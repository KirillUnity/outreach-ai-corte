"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator
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


class AgentSettings(BaseModel):
    """LangGraph outreach-agent knobs. Approval stays on in dev on purpose."""

    max_iterations: int = 10
    enable_checkpointing: bool = True
    checkpointer_table: str = "agent_checkpoints"
    auto_send_threshold: float = 0.8
    require_deliverability_check: bool = True
    require_human_approval: bool = True
    sender_domain: str = ""


class LangfuseSettings(BaseModel):
    """Self-hosted Langfuse. Empty keys disable tracing (no-op), never crash the API."""

    enabled: bool = True
    public_key: str = ""
    secret_key: str = ""
    host: str = "http://langfuse:3000"
    release: str = "outreach-ai-cortex@0.1.0"
    environment: str = "development"
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class PromptABSettings(BaseModel):
    """In-process prompt A/B. Off by default so CI stays deterministic."""

    enabled: bool = False


class Neo4jSettings(BaseModel):
    """Bolt driver settings. Heap/pagecache live in Compose, not here."""

    uri: str = "bolt://neo4j:7687"
    user: str = "neo4j"
    password: str = "change-me-please-strong-password"
    database: str = "neo4j"
    max_connection_pool_size: int = 50
    connection_timeout: int = 30
    enabled: bool = True
    auto_sync_on_write: bool = False


class EmailFinderSettings(BaseModel):
    """Pattern + Hunter lookup. Real SMTP RCPT is disabled (spam-probe risk)."""

    enabled: bool = True
    max_patterns_to_try: int = 10
    common_patterns: list[str] = Field(
        default_factory=lambda: [
            "{first}.{last}",
            "{first}{last}",
            "{f}{last}",
            "{first}_{last}",
            "{first}",
            "{last}.{first}",
            "{last}{first}",
            "{first}-{last}",
            "{f}.{last}",
            "{first}.{l}",
        ]
    )
    smtp_enabled: bool = False
    smtp_timeout: int = 10
    smtp_helo_domain: str = "outreach-ai-cortex.local"
    smtp_from_email: str = "verify@outreach-ai-cortex.local"
    hunter_enabled: bool = False
    hunter_api_key: str = ""
    hunter_base_url: str = "https://api.hunter.io/v2"
    apollo_enabled: bool = False
    apollo_api_key: str = ""
    apollo_base_url: str = "https://api.apollo.io/api/v1"
    min_confidence_to_save: float = 0.3
    min_confidence_to_use: float = 0.6

    @field_validator("common_patterns", mode="before")
    @classmethod
    def _split_patterns(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


class WarmupSettings(BaseModel):
    """In-process mailbox warmup emulator (no real SMTP)."""

    enabled: bool = True
    auto_run_enabled: bool = False
    tick_interval_seconds: int = 3600
    max_emails_per_tick: int = 10
    daily_limits: list[int] = Field(
        default_factory=lambda: (
            [5] * 7 + [10] * 7 + [20] * 7 + [40] * 7 + [60, 60]
        )
    )
    peer_open_rate: float = 0.7
    peer_reply_rate: float = 0.15
    peer_spam_rate: float = 0.002
    peer_bounce_rate: float = 0.01
    peer_important_rate: float = 0.05
    reputation_min: float = 0.0
    reputation_max: float = 100.0
    reputation_ban_threshold: float = 20.0
    reputation_warmed_threshold: float = 70.0
    rng_seed: int | None = None
    peer_network_size: int = 20

    @field_validator("daily_limits", mode="before")
    @classmethod
    def _split_limits(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        return value


class DeliverabilitySettings(BaseModel):
    """Live DNS lookups for SPF / DKIM / DMARC / MX."""

    dns_timeout: float = 5.0
    dns_lifetime: float = 10.0
    dns_nameservers: list[str] = Field(default_factory=lambda: ["1.1.1.1", "8.8.8.8"])
    dkim_selectors: list[str] = Field(
        default_factory=lambda: [
            "google",
            "default",
            "mail",
            "dkim",
            "k1",
            "s1",
            "s2",
            "selector1",
            "selector2",
            "mandrill",
        ]
    )
    cache_ttl_seconds: int = 3600

    @field_validator("dns_nameservers", "dkim_selectors", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


class LinkedInSettings(BaseModel):
    """LinkedIn enrichment: mock (default) or Phantombuster."""

    mode: Literal["mock", "real"] = "mock"
    phantombuster_api_key: str = ""
    phantombuster_phantom_id: str = ""
    people_search_phantom_id: str = ""
    base_url: str = "https://api.phantombuster.com/api/v2"
    mock_delay_seconds: float = 0.2
    poll_interval_seconds: float = 3.0
    max_poll_attempts: int = 20


class CrmSettings(BaseModel):
    """Outbound CRM upsert. Default mock — no vendor calls without URL/key."""

    enabled: bool = True
    provider: Literal["mock", "bitrix24", "retailcrm"] = "mock"
    webhook_url: str = ""
    webhook_token: str = ""
    api_key: str = ""
    base_url: str = ""
    require_token: bool = False
    timeout_seconds: float = 15.0


class ContentSettings(BaseModel):
    """Outbound publishing configuration; mock channel needs no secrets."""

    publish_webhook_url: str = ""
    timeout_seconds: float = 15.0


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

    # Observability. Empty DSN skips Sentry. Metrics are a scrape endpoint, not a local Prometheus.
    sentry_dsn: str = ""
    sentry_enabled: bool = False
    prometheus_enabled: bool = True

    # PostgreSQL (async SQLAlchemy)
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/outreach"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    parser: ParserSettings = Field(default_factory=ParserSettings)
    linkedin: LinkedInSettings = Field(default_factory=LinkedInSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    prompt_ab: PromptABSettings = Field(default_factory=PromptABSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    deliverability: DeliverabilitySettings = Field(default_factory=DeliverabilitySettings)
    warmup: WarmupSettings = Field(default_factory=WarmupSettings)
    email_finder: EmailFinderSettings = Field(default_factory=EmailFinderSettings)
    crm: CrmSettings = Field(default_factory=CrmSettings)
    content: ContentSettings = Field(default_factory=ContentSettings)
    graph_sync_token: str = ""
    hunter_api_key: str = ""
    hunter_enabled: bool = False
    apollo_api_key: str = ""
    apollo_enabled: bool = False
    smtp_verification_enabled: bool = False
    bitrix_webhook_url: str = ""
    retailcrm_api_key: str = ""
    retailcrm_base_url: str = ""
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

    @property
    def database_url_sync(self) -> str:
        """psycopg-style URL for LangGraph's Postgres checkpointer."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    def model_post_init(self, __context: object) -> None:
        """Copy flat env aliases into nested settings."""
        if self.hunter_api_key and not self.email_finder.hunter_api_key:
            self.email_finder.hunter_api_key = self.hunter_api_key
        if self.hunter_enabled:
            self.email_finder.hunter_enabled = True
        if self.apollo_api_key and not self.email_finder.apollo_api_key:
            self.email_finder.apollo_api_key = self.apollo_api_key
        if self.apollo_enabled:
            self.email_finder.apollo_enabled = True
        if self.smtp_verification_enabled:
            self.email_finder.smtp_enabled = True
        if self.bitrix_webhook_url and not self.crm.webhook_url:
            self.crm.webhook_url = self.bitrix_webhook_url
        if self.retailcrm_api_key and not self.crm.api_key:
            self.crm.api_key = self.retailcrm_api_key
        if self.retailcrm_base_url and not self.crm.base_url:
            self.crm.base_url = self.retailcrm_base_url
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
