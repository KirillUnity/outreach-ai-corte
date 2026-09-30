#!/usr/bin/env python3
"""
Deliverability CLI — SPF / DKIM / DMARC / MX for a domain.

Uses the API services (same scoring as GET /deliverability/check/{domain}).

Usage (from repo root, PYTHONPATH=backend):
    python tools/deliverability_cli.py gmail.com
    python tools/deliverability_cli.py stripe.com --json

Inside Compose:
    docker compose exec api poetry run python /app/tools/deliverability_cli.py gmail.com
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


async def _run(domain: str) -> dict:
    from app.core.config import settings
    from app.services.deliverability.checker import DeliverabilityChecker, clear_deliverability_cache

    clear_deliverability_cache()
    checker = DeliverabilityChecker(settings)
    return await checker.check_domain(domain, use_cache=False)


def print_report(result: dict) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print(json.dumps(result, default=str, indent=2))
        return

    console = Console()
    table = Table(title=f"Deliverability Report: {result['domain']}")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    spf = result["spf"]
    table.add_row(
        "SPF",
        "✅ Valid" if spf["valid"] else "❌ Missing",
        f"policy={spf.get('policy', 'N/A')}",
    )
    dkim = result["dkim"]
    table.add_row(
        "DKIM",
        "✅ Valid" if dkim["valid"] else "❌ Missing",
        f"selector={dkim.get('selector', 'N/A')}",
    )
    dmarc = result["dmarc"]
    table.add_row(
        "DMARC",
        "✅ Valid" if dmarc["valid"] else "❌ Missing",
        f"policy={dmarc.get('policy', 'N/A')}",
    )
    mx = result["mx"]
    table.add_row(
        "MX",
        "✅ Valid" if mx["valid"] else "❌ Missing",
        f"provider={mx.get('provider', 'N/A')}",
    )

    console.print(table)
    console.print(f"\n[bold]Score:[/bold] {result['overall_score']}/100")
    console.print(f"[bold]Risk:[/bold] {result['risk_level']}")
    if result.get("recommendations"):
        console.print("\n[bold yellow]Recommendations:[/bold yellow]")
        for item in result["recommendations"]:
            console.print(f"  • {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check SPF/DKIM/DMARC/MX for a domain")
    parser.add_argument("domain")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(_run(args.domain))
    if args.json:
        print(json.dumps(result, default=str, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
