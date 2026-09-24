"""Export the outreach graph as Mermaid (and PNG if mermaid.ink is reachable)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.core.config import AgentSettings, Settings
from app.services.agent.graph import build_outreach_graph


def main() -> None:
    settings = Settings(agent=AgentSettings(enable_checkpointing=False))
    graph = build_outreach_graph(
        person_service=MagicMock(),
        company_service=MagicMock(),
        rag_service=MagicMock(),
        email_generator=MagicMock(),
        validator=MagicMock(),
        deliverability_checker=MagicMock(),
        draft_service=MagicMock(),
        settings=settings,
    )
    drawable = graph.get_graph()
    docs = Path(__file__).resolve().parents[1] / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    mermaid_path = docs / "agent_graph.mmd"
    mermaid_path.write_text(drawable.draw_mermaid(), encoding="utf-8")
    print(f"wrote {mermaid_path}")
    png_path = docs / "agent_graph.png"
    try:
        drawable.draw_mermaid_png(output_file_path=str(png_path))
        print(f"wrote {png_path}")
    except Exception as exc:
        print(f"PNG skipped ({exc}). Use the .mmd file or a mermaid renderer.")


if __name__ == "__main__":
    main()
