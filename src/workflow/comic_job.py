"""Saga workflow: mock story → sinh ảnh từng panel qua image-ai."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from src.generated import orchestrator_pb2
from src.clients.image_client import ImageAiClient
from src.clients.story_client import StoryClient
from src.state.redis_store import ComicJobStore

logger = logging.getLogger(__name__)

PANEL_STATUS_PENDING = "PENDING"
PANEL_STATUS_PROCESSING = "PROCESSING"
PANEL_STATUS_SUCCESS = "SUCCESS"
PANEL_STATUS_FAILED = "FAILED"


@dataclass
class PanelScriptData:
    index: int
    caption_vi: str
    prompt_en: str
    scene_description: str
    speaker: str = ""
    panel_type: str = "dialogue"
    speaker_position: str = "center"


@dataclass
class ComicJobState:
    job_id: str
    user_id: str
    summary: str
    style: str
    request_id: str
    num_panels: int
    status: int = orchestrator_pb2.COMIC_JOB_PENDING
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
            status=int(data.get("status", orchestrator_pb2.COMIC_JOB_PENDING)),
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
            status=orchestrator_pb2.COMIC_JOB_PENDING,
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
        self._persist(state)

        for task_id in state.image_task_ids:
            if task_id:
                self._image_client.cancel_task(task_id)
        return state

    def _persist(self, state: ComicJobState) -> None:
        self._store.save(state.job_id, state.to_dict())

    def _run_pipeline(self, job_id: str) -> None:
        state = self.get(job_id)
        if not state:
            return

        try:
            self._update(state, status=orchestrator_pb2.COMIC_JOB_STORY_GENERATING, step="Generating story")

            if state.cancel_requested:
                return

            story_result = self._story_client.generate_story(
                job_id=state.job_id,
                summary=state.summary,
                style=state.style,
                num_panels=state.num_panels,
            )
            scripts = [
                PanelScriptData(
                    index=p.index,
                    caption_vi=p.caption_vi,
                    prompt_en=p.prompt_en,
                    scene_description=p.scene_description,
                    speaker=p.speaker,
                    panel_type=p.panel_type,
                    speaker_position=p.speaker_position,
                )
                for p in story_result.panels
            ]
          
            state.num_panels = len(scripts)
            state.progress_total = len(scripts)
            state.panels = [_empty_panel_dict(script) for script in scripts]
            state.image_task_ids = [None] * len(scripts)
            self._update(state, status=orchestrator_pb2.COMIC_JOB_STORY_READY, step="Story ready")

            if state.cancel_requested:
                return

            reference_url = ""
            for script in scripts:
                if state.cancel_requested:
                    return

                panel_index = script.index
                state.panels[panel_index]["status"] = PANEL_STATUS_PROCESSING
                self._update(
                    state,
                    status=orchestrator_pb2.COMIC_JOB_IMAGE_GENERATING,
                    step=f"Generating panel {panel_index + 1}/{state.num_panels}",
                )

                try:
                    result = self._image_client.generate_panel(
                        prompt=script.prompt_en,
                        caption_vi=script.caption_vi,
                        reference_image_url=reference_url,
                        style=state.style,
                    )
                except Exception as exc:
                    logger.exception("Panel %s failed for job %s", panel_index, job_id)
                    state.panels[panel_index]["status"] = PANEL_STATUS_FAILED
                    state.panels[panel_index]["error_message"] = str(exc)
                    raise

                state.panels[panel_index]["image_url"] = result.image_url
                state.panels[panel_index]["seed"] = result.seed
                state.panels[panel_index]["status"] = PANEL_STATUS_SUCCESS
                state.image_task_ids[panel_index] = result.task_id
                state.progress_current = panel_index + 1

                if panel_index == 0:
                    reference_url = result.image_url

                self._update(
                    state,
                    status=orchestrator_pb2.COMIC_JOB_IMAGE_GENERATING,
                    step=f"Completed panel {panel_index + 1}/{state.num_panels}",
                )

            self._update(
                state,
                status=orchestrator_pb2.COMIC_JOB_SUCCESS,
                step="All panels completed",
            )
            logger.info("Job %s completed successfully", job_id)

        except Exception as exc:
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
