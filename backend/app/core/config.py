"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ParserSettings(BaseModel):
    """HTTP fetch and text-extraction limits for company site research."""

    timeout: int = 15
    max_retries: int = 2
    user_agent: str = (
        "Mozilla/5.0 (compatible; OutreachAICortex/1.0; "
        "+https://github.com/KirillUnity/outreach-ai-cortex)"
    )
    max_text_length: int = 50000
    follow_links: list[str] = Field(
        default_factory=lambda: ["/about", "/product", "/services", "/solutions", "/pricing"]
    )


class LinkedInSettings(BaseModel):
    """LinkedIn enrichment: mock (default) or Phantombuster."""

    mode: Literal["mock", "real"] = "mock"
    phantombuster_api_key: str = ""
    phantombuster_phantom_id: str = ""
    base_url: str = "https://api.phantombuster.com/api/v2"
    mock_delay_seconds: float = 0.2
    poll_interval_seconds: float = 3.0
    max_poll_attempts: int = 20


class Settings(BaseSettings):
    """Centralized settings for Outreach AI Cortex."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="_",
    )

    # Application
    app_name: str = "Outreach AI Cortex"
    debug: bool = False

    # PostgreSQL (async SQLAlchemy)
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/outreach"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    parser: ParserSettings = Field(default_factory=ParserSettings)
    linkedin: LinkedInSettings = Field(default_factory=LinkedInSettings)
    # Convenience alias so .env can use PHANTOMBUSTER_API_KEY without a nested prefix.
    phantombuster_api_key: str = ""

    @property
    def chroma_base_url(self) -> str:
        """Base URL for ChromaDB HTTP API."""
        return f"http://{self.chroma_host}:{self.chroma_port}"

    def model_post_init(self, __context: object) -> None:
        """Copy top-level PHANTOMBUSTER_API_KEY into nested LinkedIn settings."""
        if self.phantombuster_api_key and not self.linkedin.phantombuster_api_key:
            self.linkedin.phantombuster_api_key = self.phantombuster_api_key


settings = Settings()
