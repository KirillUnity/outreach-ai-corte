"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized settings for Outreach AI Cortex."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Outreach AI Cortex"
    debug: bool = False

    # PostgreSQL (async SQLAlchemy)
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/outreach"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    @property
    def chroma_base_url(self) -> str:
        """Base URL for ChromaDB HTTP API."""
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()
