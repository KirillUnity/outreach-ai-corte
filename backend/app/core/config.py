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


class RAGSettings(BaseModel):
    """Chunking + cloud embeddings + Chroma collection layout.

    Embeddings are cloud-only (OpenAI / OpenRouter). `mode=mock` is a
    hash-vector stand-in for CI — not a local neural model.
    """

    mode: Literal["mock", "real"] = "mock"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    collection_prefix: str = "company_"
    openai_api_key: str = ""
    openai_base_url: str = ""
    max_source_chars: int = 1_000_000
    min_chunk_chars: int = 50


class LLMSettings(BaseModel):
    """Cloud chat settings. `mode=mock` is for CI — not a local model."""

    mode: Literal["mock", "real"] = "mock"
    provider: Literal["openai", "openrouter"] = "openai"
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "gpt-4o-mini"
    premium_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 800
    request_timeout: int = 60


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
    rag: RAGSettings = Field(default_factory=RAGSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    # Convenience aliases so .env can use flat names from the Day 6/7 specs.
    phantombuster_api_key: str = ""
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    rag_mode: Literal["mock", "real"] = "mock"
    llm_mode: Literal["mock", "real"] = "mock"
    llm_provider: Literal["openai", "openrouter"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    default_model: str = "gpt-4o-mini"
    premium_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 800

    @property
    def chroma_base_url(self) -> str:
        """Base URL for ChromaDB HTTP API."""
        return f"http://{self.chroma_host}:{self.chroma_port}"

    def model_post_init(self, __context: object) -> None:
        """Copy flat env aliases into nested settings."""
        if self.phantombuster_api_key and not self.linkedin.phantombuster_api_key:
            self.linkedin.phantombuster_api_key = self.phantombuster_api_key
        self.rag.mode = self.rag_mode
        self.rag.chroma_host = self.chroma_host
        self.rag.chroma_port = self.chroma_port
        self.rag.embedding_model = self.embedding_model
        self.rag.chunk_size = self.chunk_size
        self.rag.chunk_overlap = self.chunk_overlap
        self.rag.top_k = self.top_k
        if self.openai_api_key and not self.rag.openai_api_key:
            self.rag.openai_api_key = self.openai_api_key
        self.llm.mode = self.llm_mode
        self.llm.provider = self.llm_provider
        self.llm.default_model = self.default_model
        self.llm.premium_model = self.premium_model
        self.llm.temperature = self.llm_temperature
        self.llm.max_tokens = self.llm_max_tokens
        if self.openai_api_key and not self.llm.openai_api_key:
            self.llm.openai_api_key = self.openai_api_key
        if self.openrouter_api_key and not self.llm.openrouter_api_key:
            self.llm.openrouter_api_key = self.openrouter_api_key


settings = Settings()
