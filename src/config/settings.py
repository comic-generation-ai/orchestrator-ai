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

    # Configuration to load from .env file (biến dạng ORCHESTRATOR_* trong .env)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ORCHESTRATOR_",
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        return self.REDIS_URL


@lru_cache
def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
