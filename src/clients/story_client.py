import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class StoryPanelResult:
    index: int
    caption_vi: str
    prompt_en: str
    scene_description: str
    speaker: str = ""
    panel_type: str = "dialogue"
    speaker_position: str = "center"
    character_ids: list[str] = field(default_factory=list)


@dataclass
class StoryResult:
    story_title: str
    panels: list[StoryPanelResult] = field(default_factory=list)
    characters: dict[str, dict[str, Any]] = field(default_factory=dict)
    is_fallback: bool = False


def _parse_character_ids(raw_panel: dict[str, Any]) -> list[str]:
    """
    [story-orchestrator-character-ids] Changed: parse optional character_ids[] from story-ai panel (empty when teammate not merged yet).
    """
    raw_ids = raw_panel.get("character_ids") or []
    if not isinstance(raw_ids, list):
        return []
    return [str(char_id) for char_id in raw_ids if char_id]


def _parse_characters(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [story-orchestrator-character-ids] Changed: parse optional characters{} bible from story-ai response.
    """
    raw_characters = data.get("characters") or {}
    if not isinstance(raw_characters, dict):
        return {}
    return {
        str(char_id): dict(meta) if isinstance(meta, dict) else {}
        for char_id, meta in raw_characters.items()
    }


def _parse_story_panel(raw_panel: dict[str, Any], fallback_index: int) -> StoryPanelResult:
    """
    [story-orchestrator-character-ids] Changed: map scene_description from its own field (not panel_type); include character_ids.
    """
    panel_number = raw_panel.get("panel_number", fallback_index + 1)
    return StoryPanelResult(
        index=max(panel_number - 1, 0),
        caption_vi=raw_panel.get("dialogue") or "",
        prompt_en=raw_panel.get("image_prompt", ""),
        scene_description=raw_panel.get("scene_description") or "",
        speaker=raw_panel.get("speaker") or "",
        panel_type=raw_panel.get("panel_type") or "dialogue",
        speaker_position=raw_panel.get("speaker_position") or "center",
        character_ids=_parse_character_ids(raw_panel),
    )


class StoryClient:
    """HTTP client gọi story-ai (FastAPI) — POST /generate-story, GET /health.
    Đồng bộ (không async) để khớp cách
    ComicJobWorkflow._run_pipeline chạy trong thread riêng, không phải asyncio.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.STORY_AI_API_URL
        self.session = httpx.Client(
            base_url=self.base_url.rstrip("/"),
            timeout=settings.story_ai_timeout_sec,
        )

    def check_health(self) -> bool:
        try:
            resp = self.session.get("/health", timeout=5)
            resp.raise_for_status()
            return bool(resp.json().get("is_alive"))
        except httpx.HTTPError as exc:
            logger.warning("story-ai health check failed: %s", exc)
            return False

    def generate_story(
        self,
        *,
        job_id: str,
        summary: str,
        style: str,
        num_panels: int,
        language: str = "vi",
    ) -> StoryResult:
        payload = {
            "job_id": job_id,
            "summary": summary,
            "num_panels": num_panels,
            "style": style or "comic book style, vibrant colors",
            "language": language,
        }
        response = self.session.post("/generate-story", json=payload)
        response.raise_for_status()
        data = response.json()

        panels: list[StoryPanelResult] = []
        for raw_panel in data.get("panels", []):
            if not isinstance(raw_panel, dict):
                continue
            panels.append(_parse_story_panel(raw_panel, len(panels)))
        panels.sort(key=lambda p: p.index)

        # Gán lại index theo vị trí thực tế sau khi sort — panel_number từ LLM có thể
        # trùng hoặc nhảy số (1, 2, 4), nếu giữ nguyên sẽ gây IndexError/ghi đè khi
        # workflow truy cập state.panels[index].
        for pos, panel in enumerate(panels):
            panel.index = pos

        if not panels:
            raise RuntimeError(f"story-ai không trả về panel nào cho job_id={job_id}")

        is_fallback = bool(data.get("is_fallback", False))
        if is_fallback and not self.settings.story_allow_fallback:
            raise RuntimeError(
                f"story-ai trả kết quả mock fallback cho job_id={job_id} "
                "(LLM lỗi hoặc thiếu API key) — dừng job để không sinh ảnh từ prompt mock. "
                "Đặt ORCHESTRATOR_STORY_ALLOW_FALLBACK=true nếu muốn chấp nhận truyện mock."
            )
        if is_fallback:
            logger.warning(
                "story-ai trả kết quả mock fallback cho job_id=%s — tiếp tục vì "
                "STORY_ALLOW_FALLBACK=true", job_id,
            )

        return StoryResult(
            story_title=data.get("story_title", ""),
            panels=panels,
            characters=_parse_characters(data),
            is_fallback=is_fallback,
        )

    def close(self) -> None:
        self.session.close()
