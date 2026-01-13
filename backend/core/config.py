"""Explorer configuration."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql+asyncpg://explorer:explorer@localhost:5432/explorer"

    # Blockchain node
    node_url: str = "http://localhost:8000"

    # Indexer settings
    indexer_poll_interval: int = 2  # seconds
    resync_interval: int = 300  # 5 minutes
    resync_depth: int = 10  # check last N blocks for reorg

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 3001
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://frontend:3000", "*"]

    # Pagination
    default_page_size: int = 25
    max_page_size: int = 100

    class Config:
        env_prefix = "EXPLORER_"
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
