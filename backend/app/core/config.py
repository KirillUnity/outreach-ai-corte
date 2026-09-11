"""Application configuration loaded from environment variables."""

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

    @property
    def chroma_base_url(self) -> str:
        """Base URL for ChromaDB HTTP API."""
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()
