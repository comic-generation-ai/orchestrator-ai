import os
from dataclasses import dataclass
from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    ENV: str = Field(default="development", description="Environment mode (development/production)")
    
    # gRPC & HTTP Server Settings
    GRPC_HOST: str = Field(default="0.0.0.0", description="Host address")
    GRPC_PORT: int = Field(default=50052, description="gRPC listen port")
    REDIS_URL: str = Field(default="redis://localhost:6379/1", description="Redis server URL")

    # Image AI Settings
    IMAGE_AI_GRPC_TARGET: str = Field(default="localhost:50051", description="Image AI gRPC target")
    IMAGE_AI_WIDTH: int = Field(default=512, description="Image width")
    IMAGE_AI_HEIGHT: int = Field(default=512, description="Image height")
    IMAGE_AI_STEPS: int = Field(default=4, description="Image steps")
    IMAGE_POLL_INTERVAL_SEC: float = Field(default=2, description="Image poll interval in seconds")
    IMAGE_POLL_MAX_ATTEMPTS: int = Field(default=360, description="Image poll max attempts")
    REDIS_JOB_TTL_SEC: int = Field(default=86400, description="Redis job TTL in seconds")
    REDIS_DB: int = Field(default=1, description="Redis database")

    # Story AI Settings (REST/FastAPI — story-ai không triển khai gRPC được)
    # Cảnh báo: story-ai mặc định chạy port 50052 (Config.PORT trong story-ai/src/config.py)
    # — TRÙNG với ORCHESTRATOR_GRPC_PORT mặc định (50052). Nếu chạy 2 service cùng máy,
    # đổi 1 trong 2 port qua .env để tránh đụng.
    STORY_AI_API_URL: str = Field(default="http://localhost:50052", description="Story AI base URL")
    # 240s: story-ai retry tối đa 3 lần (LLM ~10-60s/lần + wait rate-limit tối đa 20s/lần)
    # — 90s cũ khiến orchestrator ReadTimeout trong khi story-ai vẫn đang xử lý.
    STORY_AI_TIMEOUT_SEC: float = Field(default=270.0, description="Story AI request timeout (giây)")
    # False (mặc định): job FAILED ngay khi story-ai trả kết quả mock fallback
    # (LLM lỗi / thiếu API key) — tránh đốt GPU sinh ảnh từ prompt mock vô nghĩa.
    # True: chấp nhận truyện mock (dùng khi dev không có API key).
    STORY_ALLOW_FALLBACK: bool = Field(default=False, description="Chấp nhận kết quả mock fallback từ story-ai")

    # Configuration to load from .env file (biến dạng ORCHESTRATOR_* trong .env)
    # Neo theo vị trí settings.py (không dùng cwd) — cùng lý do đã gặp bug ở image-ai:
    # đường dẫn tương đối khiến Settings âm thầm bỏ qua .env nếu chạy khác cwd dự kiến.
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        env_prefix="ORCHESTRATOR_",
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        return self.REDIS_URL

    @property
    def grpc_host(self) -> str:
        return self.GRPC_HOST

    @property
    def grpc_port(self) -> int:
        return self.GRPC_PORT

    @property
    def redis_job_ttl_sec(self) -> int:
        return self.REDIS_JOB_TTL_SEC

    @property
    def image_ai_grpc_target(self) -> str:
        return self.IMAGE_AI_GRPC_TARGET

    @property
    def image_width(self) -> int:
        return self.IMAGE_AI_WIDTH

    @property
    def image_height(self) -> int:
        return self.IMAGE_AI_HEIGHT

    @property
    def image_steps(self) -> int:
        return self.IMAGE_AI_STEPS

    @property
    def image_poll_interval_sec(self) -> float:
        return self.IMAGE_POLL_INTERVAL_SEC

    @property
    def image_poll_max_attempts(self) -> int:
        return self.IMAGE_POLL_MAX_ATTEMPTS

    @property
    def image_poll_timeout_sec(self) -> float:
        return self.IMAGE_POLL_INTERVAL_SEC * self.IMAGE_POLL_MAX_ATTEMPTS

    @property
    def story_ai_timeout_sec(self) -> float:
        return self.STORY_AI_TIMEOUT_SEC

    @property
    def story_allow_fallback(self) -> bool:
        return self.STORY_ALLOW_FALLBACK


@lru_cache
def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
