"""Live DNS-based email authentication checks (SPF / DKIM / DMARC / MX)."""

from app.services.deliverability.checker import DeliverabilityChecker

__all__ = ["DeliverabilityChecker"]
