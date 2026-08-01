"""Saga workflow: mock story → sinh ảnh từng panel qua image-ai."""

from __future__ import annotations

import math
import re
import difflib
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from src.generated import orchestrator_pb2
from src.clients.image_client import ImageAiClient
from src.clients.story_client import StoryClient, StoryGenerationCancelledError
from src.state.redis_store import ComicJobStore

logger = logging.getLogger(__name__)

PANEL_STATUS_PENDING = "PENDING"
PANEL_STATUS_PROCESSING = "PROCESSING"
PANEL_STATUS_SUCCESS = "SUCCESS"
PANEL_STATUS_FAILED = "FAILED"

# Tag nhận diện nhân vật (vd "a small black crow with a shiny beak") luôn được
# story-ai lặp lại NGUYÊN VĂN giữa các panel (xem CHARACTER CONSISTENCY trong
# prompt_template.py) — nên 1 đoạn trùng khớp đủ dài giữa 2 prompt là dấu hiệu
# đáng tin cậy rằng 2 panel có chung nhân vật.
_SHARED_CHARACTER_TAG_MIN_LENGTH = 20

def _extract_character_segments(prompt: str) -> list[dict]:
    if not prompt:
        return []
    raw_segments = [s.strip() for s in prompt.split(";") if s.strip()]
    if not raw_segments:
        return []
    spatial_indicators = ["on the left", "on the right", "in the center", "at the background"]

    has_spatial = any(
        any( ind in seg.lower() for ind in spatial_indicators)
        for seg in raw_segments
    )

    character_segments = []
    if has_spatial:
        for seg in raw_segments:
            if any(ind in seg.lower() for ind in spatial_indicators):
                seg_clean = seg
                for ind in spatial_indicators:
                    seg_clean = re.sub(re.escape(ind) + r"\s*,\s*", "", seg_clean, flags=re.IGNORECASE)
                    seg_clean = re.sub(re.escape(ind) + r"\s*", "", seg_clean, flags=re.IGNORECASE)
                character_segments.append(seg_clean.strip())
    else: 
        character_segments.append(raw_segments[0])
    return character_segments


def _shares_character_tag(prompt_a: str, prompt_b: str) -> bool:
    """
    Xác định xem hai prompt có chung nhân vật hay không bằng cách so khớp chéo
    các phân đoạn nhân vật sạch. Loại bỏ hoàn toàn nhiễu do trùng bối cảnh.
    """
    segs_a = _extract_character_segments(prompt_a)
    segs_b = _extract_character_segments(prompt_b)
    
    if not segs_a or not segs_b:
        return False
    
    for seg_a in segs_a:
        for seg_b in segs_b:
            match = difflib.SequenceMatcher(None, seg_a.lower(), seg_b.lower()).find_longest_match(
                0, len(seg_a), 0, len(seg_b)
            )
            if match.size >= _SHARED_CHARACTER_TAG_MIN_LENGTH:
                return True
    return False


def _char_id_for_speaker(
    speaker: str,
    characters: dict[str, dict[str, Any]],
    panel_character_ids: list[str],
) -> str | None:
    """
    [story-orchestrator-character-ids] Changed: map speaker name to char_id when present in panel character_ids.
    """
    if not speaker or not panel_character_ids:
        return None
    speaker_norm = speaker.strip().lower()
    for char_id in panel_character_ids:
        meta = characters.get(char_id) or {}
        name = str(meta.get("name") or "").strip().lower()
        if name and name == speaker_norm:
            return char_id
    return None


def _resolve_panel_reference_url(
    script: "PanelScriptData",
    *,
    characters: dict[str, dict[str, Any]],
    char_reference_map: dict[str, str],
    panel_history: list[tuple[str, str]],
) -> str:
    """
    [story-orchestrator-character-ids] Changed: prefer char_reference_map by character_ids; fallback to fuzzy tag match.
    """
    if script.character_ids:
        speaker_char_id = _char_id_for_speaker(
            script.speaker, characters, script.character_ids
        )
        if speaker_char_id and speaker_char_id in char_reference_map:
            return char_reference_map[speaker_char_id]
        for char_id in script.character_ids:
            if char_id in char_reference_map:
                return char_reference_map[char_id]
        return ""

    for past_prompt, past_image_url in panel_history:
        if _shares_character_tag(past_prompt, script.prompt_en):
            return past_image_url
    return ""


def _register_char_references(
    char_reference_map: dict[str, str],
    character_ids: list[str],
    image_url: str,
) -> None:
    """
    [story-orchestrator-character-ids] Changed: store first panel image URL per char_id for IP-Adapter reference.
    """
    for char_id in character_ids:
        if char_id not in char_reference_map:
            char_reference_map[char_id] = image_url


@dataclass
class PanelScriptData:
    index: int
    caption_vi: str
    prompt_en: str
    scene_description: str
    speaker: str = ""
    panel_type: str = "dialogue"
    speaker_position: str = "center"
    character_ids: list[str] = field(default_factory=list)


@dataclass
class ComicJobState:
    job_id: str
    user_id: str
    summary: str
    style: str
    request_id: str
    num_panels: int
    status: int = orchestrator_pb2.COMIC_JOB_QUEUED
    progress_current: int = 0
    progress_total: int = 4
    current_step: str = "Queued"
    error_message: str = ""
    page_image_url: str = ""
    panels: list[dict[str, Any]] = field(default_factory=list)
    image_task_ids: list[Optional[str]] = field(default_factory=list)
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "summary": self.summary,
            "style": self.style,
            "request_id": self.request_id,
            "num_panels": self.num_panels,
            "status": self.status,
            "progress_current": self.progress_current,
            "progress_total": self.progress_total,
            "current_step": self.current_step,
            "error_message": self.error_message,
            "page_image_url": self.page_image_url,
            "panels": self.panels,
            "image_task_ids": self.image_task_ids,
            "cancel_requested": self.cancel_requested,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComicJobState:
        return cls(
            job_id=data["job_id"],
            user_id=data.get("user_id", ""),
            summary=data.get("summary", ""),
            style=data.get("style", ""),
            request_id=data.get("request_id", ""),
            num_panels=int(data.get("num_panels", 4)),
            status=int(data.get("status", orchestrator_pb2.COMIC_JOB_QUEUED)),
            progress_current=int(data.get("progress_current", 0)),
            progress_total=int(data.get("progress_total", 4)),
            current_step=data.get("current_step", ""),
            error_message=data.get("error_message", ""),
            page_image_url=data.get("page_image_url", ""),
            panels=list(data.get("panels", [])),
            image_task_ids=list(data.get("image_task_ids", [])),
            cancel_requested=bool(data.get("cancel_requested", False)),
        )

    def to_status_response(self) -> orchestrator_pb2.GetComicJobStatusResponse:
        response = orchestrator_pb2.GetComicJobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            progress_current=self.progress_current,
            progress_total=self.progress_total,
            page_image_url=self.page_image_url,
            error_message=self.error_message,
            current_step=self.current_step,
        )
        for panel in self.panels:
            response.panels.append(
                orchestrator_pb2.PanelResult(
                    index=panel.get("index", 0),
                    caption_vi=panel.get("caption_vi", ""),
                    image_url=panel.get("image_url", ""),
                    prompt_en=panel.get("prompt_en", ""),
                    seed=int(panel.get("seed", 0)),
                    status=panel.get("status", PANEL_STATUS_PENDING),
                    error_message=panel.get("error_message", ""),
                    speaker=panel.get("speaker", ""),
                    panel_type=panel.get("panel_type", ""),
                    speaker_position=panel.get("speaker_position", "center"),
                )
            )
        return response


def _empty_panel_dict(script: PanelScriptData) -> dict[str, Any]:
    return {
        "index": script.index,
        "caption_vi": script.caption_vi,
        "prompt_en": script.prompt_en,
        "image_url": "",
        "seed": 0,
        "status": PANEL_STATUS_PENDING,
        "error_message": "",
        "speaker": script.speaker,
        "panel_type": script.panel_type,
        "speaker_position": script.speaker_position,
    }


class ComicJobWorkflow:
    """Điều phối job sinh truyện tranh (mock story + image-ai)."""

    def __init__(self, store: ComicJobStore, image_client: ImageAiClient, story_client: StoryClient):
        self._store = store
        self._image_client = image_client
        self._story_client = story_client
        self._lock = threading.Lock()
        self._running_threads: dict[str, threading.Thread] = {}

    def start(
        self,
        *,
        job_id: str,
        user_id: str,
        summary: str,
        style: str,
        num_panels: int,
        request_id: str,
    ) -> ComicJobState:
        if self._store.load(job_id):
            raise ValueError(f"job_id {job_id} đã tồn tại")

        num_panels = num_panels or 4
        state = ComicJobState(
            job_id=job_id,
            user_id=user_id,
            summary=summary,
            style=style,
            request_id=request_id,
            num_panels=num_panels,
            progress_total=num_panels,
            status=orchestrator_pb2.COMIC_JOB_QUEUED,
            current_step="Job queued",
        )
        self._persist(state)

        thread = threading.Thread(
            target=self._run_pipeline,
            args=(job_id,),
            name=f"comic-job-{job_id}",
            daemon=True,
        )
        with self._lock:
            self._running_threads[job_id] = thread
        thread.start()
        return state

    def get(self, job_id: str) -> Optional[ComicJobState]:
        data = self._store.load(job_id)
        if not data:
            return None
        return ComicJobState.from_dict(data)

    def cancel(self, job_id: str) -> Optional[ComicJobState]:
        state = self.get(job_id)
        if not state:
            return None

        state.cancel_requested = True
        state.status = orchestrator_pb2.COMIC_JOB_CANCELLED
        state.current_step = "Cancelled by user"
        state.error_message = ""
        self._persist(state)

        # [fix-cancel] Changed: notify story-ai + revoke in-flight image Celery tasks.
        self._story_client.cancel_story(job_id)
        for task_id in state.image_task_ids:
            if task_id:
                self._image_client.cancel_task(task_id)
        return state

    def _persist(self, state: ComicJobState) -> None:
        self._store.save(state.job_id, state.to_dict())

    def _is_cancelled(self, job_id: str) -> bool:
        data = self._store.load(job_id)
        return bool(data and data.get("cancel_requested"))

    def _finalize_cancelled(
        self,
        job_id: str,
        state: Optional[ComicJobState] = None,
    ) -> None:
        """
        [fix-cancel] Changed: pipeline exit must keep CANCELLED — never overwrite with FAILED.
        """
        state = self.get(job_id) or state
        if not state:
            return
        state.cancel_requested = True
        state.status = orchestrator_pb2.COMIC_JOB_CANCELLED
        state.current_step = "Cancelled by user"
        state.error_message = ""
        self._persist(state)

    def _exit_if_cancelled(self, job_id: str, state: ComicJobState) -> bool:
        """Return True when job was cancelled and pipeline should stop."""
        if not self._is_cancelled(job_id):
            return False
        self._finalize_cancelled(job_id, state)
        return True

    def _run_pipeline(self, job_id: str) -> None:
        state = self.get(job_id)
        if not state:
            return

        try:
            self._update(state, status=orchestrator_pb2.COMIC_JOB_RUNNING, step="Generating story")

            # BUG FIX: đọc lại Redis thay vì tin object cũ trên RAM.
            if self._exit_if_cancelled(job_id, state):
                return

            try:
                story_result = self._story_client.generate_story(
                    job_id=state.job_id,
                    summary=state.summary,
                    style=state.style,
                    num_panels=state.num_panels,
                )
            except StoryGenerationCancelledError:
                self._finalize_cancelled(job_id, state)
                return
            scripts = [
                PanelScriptData(
                    index=p.index,
                    caption_vi=p.caption_vi,
                    prompt_en=p.prompt_en,
                    scene_description=p.scene_description,
                    speaker=p.speaker,
                    panel_type=p.panel_type,
                    speaker_position=p.speaker_position,
                    character_ids=list(p.character_ids),
                )
                for p in story_result.panels
            ]
            characters = story_result.characters
          
            state.num_panels = len(scripts)
            state.progress_total = len(scripts)
            state.panels = [_empty_panel_dict(script) for script in scripts]
            state.image_task_ids = [None] * len(scripts)
            self._update(state, status=orchestrator_pb2.COMIC_JOB_RUNNING, step="Story ready")

            # BUG FIX: đọc lại Redis thay vì tin object cũ trên RAM.
            if self._exit_if_cancelled(job_id, state):
                return

            # Lịch sử TẤT CẢ panel đã sinh (không chỉ panel liền trước) — dùng để
            # neo tham chiếu vào lần XUẤT HIỆN SỚM NHẤT của 1 nhân vật thay vì luôn
            # lấy panel vừa sinh xong. Trước đây tham chiếu là "rolling" (luôn =
            # panel liền trước), nên nhân vật trôi dần diện mạo qua từng panel vì
            # ảnh tham chiếu bản thân nó cũng là ảnh AI (không phải ảnh gốc) — sai
            # lệch cộng dồn panel này qua panel khác. Neo vào panel sớm nhất có
            # cùng nhân vật giữ 1 "ảnh gốc" cố định làm chuẩn xuyên suốt truyện,
            # đúng như mô tả CHARACTER CONSISTENCY cố định trong prompt_template.py.
            # [story-orchestrator-character-ids] char_id → first panel MinIO URL for IP-Adapter reference.
            char_reference_map: dict[str, str] = {}
            panel_history: list[tuple[str, str]] = []  # [(prompt_en, image_url), ...]
            for script in scripts:
                # BUG FIX: đọc cờ huỷ từ Redis thay vì object cũ trên RAM.
                if self._exit_if_cancelled(job_id, state):
                    return

                panel_index = script.index
                state.panels[panel_index]["status"] = PANEL_STATUS_PROCESSING
                self._update(
                    state,
                    status=orchestrator_pb2.COMIC_JOB_RUNNING,
                    step=f"Generating panel {panel_index + 1}/{state.num_panels}",
                )

                panel_reference_url = _resolve_panel_reference_url(
                    script,
                    characters=characters,
                    char_reference_map=char_reference_map,
                    panel_history=panel_history,
                )
                try:
                    task_id = self._image_client.submit_panel(
                        prompt=script.prompt_en,
                        caption_vi=script.caption_vi,
                        reference_image_url=panel_reference_url,
                        style=state.style,
                    )
                    # Lưu task_id vào state và persist TRƯỚC KHI POLL —
                    # cancel() chạy trên luồng gRPC khác sẽ thấy task_id này.
                    state.image_task_ids[panel_index] = task_id
                    self._persist(state)

                    result = self._image_client.poll_task(
                        task_id,
                        should_cancel=lambda: self._is_cancelled(job_id),
                    )
                except Exception as exc:
                    if self._exit_if_cancelled(job_id, state):
                        return
                    logger.exception("Panel %s failed for job %s", panel_index, job_id)
                    state.panels[panel_index]["status"] = PANEL_STATUS_FAILED
                    state.panels[panel_index]["error_message"] = str(exc)
                    raise

                state.panels[panel_index]["image_url"] = result.image_url
                state.panels[panel_index]["seed"] = result.seed
                state.panels[panel_index]["status"] = PANEL_STATUS_SUCCESS
                state.progress_current = panel_index + 1

                # Thêm panel vừa sinh vào lịch sử để các panel SAU có thể neo về nó
                # (nếu chúng là panel sớm nhất chứa nhân vật đó) — không xoá/ghi đè
                # panel cũ, nên nhân vật xuất hiện lần đầu ở panel nào sẽ mãi là
                # "ảnh gốc" cho nhân vật đó, không bị cuốn theo panel gần nhất.
                _register_char_references(
                    char_reference_map,
                    script.character_ids,
                    result.image_url,
                )
                panel_history.append((script.prompt_en, result.image_url))

                self._update(
                    state,
                    status=orchestrator_pb2.COMIC_JOB_RUNNING,
                    step=f"Completed panel {panel_index + 1}/{state.num_panels}",
                )

            if self._exit_if_cancelled(job_id, state):
                return

            self._update(
                state,
                status=orchestrator_pb2.COMIC_JOB_COMPLETED,
                step="All panels completed",
            )
            logger.info("Job %s completed successfully", job_id)

        except Exception as exc:
            if self._exit_if_cancelled(job_id, state):
                logger.info("Job %s cancelled during pipeline", job_id)
                return
            logger.exception("Job %s failed", job_id)
            state = self.get(job_id) or state
            state.status = orchestrator_pb2.COMIC_JOB_FAILED
            state.error_message = str(exc)
            state.current_step = "Failed"
            self._persist(state)
        finally:
            with self._lock:
                self._running_threads.pop(job_id, None)

    def _update(
        self,
        state: ComicJobState,
        *,
        status: Optional[int] = None,
        step: Optional[str] = None,
    ) -> None:
        if status is not None:
            state.status = status
        if step is not None:
            state.current_step = step
        self._persist(state)
