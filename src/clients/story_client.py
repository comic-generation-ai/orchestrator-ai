import logging
from dataclasses import dataclass, field

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


@dataclass
class StoryResult:
    story_title: str
    panels: list[StoryPanelResult] = field(default_factory=list)
    is_fallback: bool = False


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
            panel_number = raw_panel.get("panel_number", len(panels) + 1)
            panels.append(
                StoryPanelResult(
                    index=max(panel_number - 1, 0),
                    caption_vi=raw_panel.get("dialogue") or "",
                    prompt_en=raw_panel.get("image_prompt", ""),
                    scene_description=raw_panel.get("panel_type", ""),
                    speaker=raw_panel.get("speaker") or "",
                    panel_type=raw_panel.get("panel_type") or "dialogue",
                    speaker_position=raw_panel.get("speaker_position") or "center",
                )
            )
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
            is_fallback=is_fallback,
        )

    def close(self) -> None:
        self.session.close()
