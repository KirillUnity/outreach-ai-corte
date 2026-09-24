"""Persisted outreach-agent run (audit trail, not the LangGraph checkpoint)."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.person import Person


class AgentRun(UUIDMixin, TimestampMixin, Base):
    """One completed (or failed-after-invoke) graph execution."""

    __tablename__ = "agent_runs"

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    goal: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    final_state: Mapped[dict] = mapped_column(JSONB, nullable=False)

    person: Mapped["Person"] = relationship()
