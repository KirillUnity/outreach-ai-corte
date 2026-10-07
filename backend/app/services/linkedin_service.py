"""LinkedIn profile enrichment: deterministic mock or Phantombuster."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any

import httpx

from app.core.config import Settings, settings as default_settings
from app.schemas.linkedin import LinkedInProfile
from app.schemas.person import normalize_linkedin_url

logger = logging.getLogger(__name__)

_IN_PATH = re.compile(r"/in/([^/?#]+)", re.IGNORECASE)

_FIRST_NAMES = ("Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Avery")
_LAST_NAMES = ("Chen", "Patel", "Nguyen", "Garcia", "Kowalski", "Andersen", "Okoro", "Berg")
_TITLES = (
    "VP of Sales",
    "Head of Growth",
    "Director of Engineering",
    "Chief Revenue Officer",
    "Product Marketing Lead",
    "Customer Success Manager",
)
_COMPANIES = ("Acme", "Globex", "Initech", "Umbrella", "Hooli", "Stark Industries")
_LOCATIONS = ("San Francisco, CA", "Austin, TX", "Berlin, DE", "London, UK", "Toronto, CA")


class LinkedInService:
    """Fetch a public-profile snapshot. Never hits LinkedIn directly."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings

    async def get_profile(self, linkedin_url: str) -> LinkedInProfile:
        """Dispatch mock vs real. Real failures fall back to mock."""
        url = normalize_linkedin_url(linkedin_url)
        username = self.extract_username(url)
        cfg = self.settings.linkedin
        if cfg.mode != "real":
            return await self._get_profile_mock(url, username)

        try:
            return await self._get_profile_real(url, username)
        except Exception:
            logger.warning(
                "Phantombuster failed for %s — falling back to mock",
                url,
                exc_info=True,
            )
            profile = await self._get_profile_mock(url, username)
            return profile

    async def _get_profile_mock(self, linkedin_url: str, username: str) -> LinkedInProfile:
        """Deterministic fake profile from sha256(username). Same URL → same person."""
        delay = self.settings.linkedin.mock_delay_seconds
        await asyncio.sleep(delay)
        digest = hashlib.sha256(username.lower().encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16)
        first = _FIRST_NAMES[idx % len(_FIRST_NAMES)]
        last = _LAST_NAMES[(idx // 8) % len(_LAST_NAMES)]
        title = _TITLES[(idx // 16) % len(_TITLES)]
        company = _COMPANIES[(idx // 32) % len(_COMPANIES)]
        location = _LOCATIONS[(idx // 64) % len(_LOCATIONS)]
        headline = f"{title} at {company}"
        return LinkedInProfile(
            linkedin_url=linkedin_url,
            username=username,
            first_name=first,
            last_name=last,
            headline=headline,
            current_title=title,
            current_company=company,
            location=location,
            about=f"{first} {last} works on B2B outreach at {company}.",
            source="mock",
        )

    async def _get_profile_real(self, linkedin_url: str, username: str) -> LinkedInProfile:
        """Launch a Phantombuster agent and poll fetch-output."""
        cfg = self.settings.linkedin
        if not cfg.phantombuster_api_key:
            raise ValueError("phantombuster_api_key is empty")
        if not cfg.phantombuster_phantom_id:
            raise ValueError("phantombuster_phantom_id is empty")

        headers = {
            "X-Phantombuster-Key-1": cfg.phantombuster_api_key,
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            launch = await client.post(
                f"{cfg.base_url.rstrip('/')}/agents/launch",
                json={
                    "id": cfg.phantombuster_phantom_id,
                    "argument": {"profileUrl": linkedin_url},
                },
            )
            launch.raise_for_status()
            launched = launch.json()
            agent_id = launched.get("containerId") or launched.get("id")
            if not agent_id:
                raise RuntimeError("Phantombuster launch returned no container id")

            last_payload: dict[str, Any] = {}
            for attempt in range(cfg.max_poll_attempts):
                await asyncio.sleep(cfg.poll_interval_seconds)
                response = await client.get(
                    f"{cfg.base_url.rstrip('/')}/agents/fetch-output",
                    params={"id": agent_id},
                )
                response.raise_for_status()
                last_payload = response.json()
                status = str(last_payload.get("status") or "").lower()
                if status in {"running", "launching", "todo", "not finished", ""}:
                    logger.info("phantombuster poll attempt=%s status=%s", attempt + 1, status)
                    continue
                if status in {"error", "failed"}:
                    raise RuntimeError(f"Phantombuster agent failed: {last_payload}")
                profile = self._map_phantom_output(linkedin_url, username, last_payload)
                if profile is None:
                    raise RuntimeError("Phantombuster returned empty output")
                return profile

        raise TimeoutError(
            f"Phantombuster poll exhausted after {cfg.max_poll_attempts} attempts"
        )

    async def search_people(
        self,
        company_domain: str,
        title_contains: str | None = None,
        limit: int = 10,
    ) -> list[LinkedInProfile]:
        """Company people-search. Never hits linkedin.com; mock is the default."""
        cap = max(1, min(int(limit or 10), 25))
        host = (company_domain or "").strip().lower()
        if not host:
            return []
        cfg = self.settings.linkedin
        if cfg.mode != "real":
            return await self._search_people_mock(host, title_contains, cap)
        try:
            return await self._search_people_real(host, title_contains, cap)
        except Exception:
            logger.warning(
                "Phantombuster people-search failed domain=%s — mock fallback",
                host,
                exc_info=True,
            )
            return await self._search_people_mock(host, title_contains, cap)

    async def _search_people_mock(
        self,
        company_domain: str,
        title_contains: str | None,
        limit: int,
    ) -> list[LinkedInProfile]:
        delay = self.settings.linkedin.mock_delay_seconds
        await asyncio.sleep(delay)
        needle = (title_contains or "").strip()
        out: list[LinkedInProfile] = []
        for index in range(limit):
            digest = hashlib.sha256(
                f"{company_domain}|{needle}|{index}".encode("utf-8")
            ).hexdigest()
            idx = int(digest[:8], 16)
            first = _FIRST_NAMES[idx % len(_FIRST_NAMES)]
            last = _LAST_NAMES[(idx // 8) % len(_LAST_NAMES)]
            title = needle or _TITLES[(idx // 16) % len(_TITLES)]
            slug = f"{company_domain.split('.')[0]}-{digest[:8]}"
            url = f"https://linkedin.com/in/{slug}"
            out.append(
                LinkedInProfile(
                    linkedin_url=url,
                    username=slug,
                    first_name=first,
                    last_name=last,
                    headline=f"{title} at {company_domain}",
                    current_title=title,
                    current_company=company_domain.split(".")[0].title(),
                    location=_LOCATIONS[(idx // 64) % len(_LOCATIONS)],
                    about=f"Mock search hit {index} for {company_domain}",
                    source="mock",
                )
            )
        return out

    async def _search_people_real(
        self,
        company_domain: str,
        title_contains: str | None,
        limit: int,
    ) -> list[LinkedInProfile]:
        cfg = self.settings.linkedin
        if not cfg.phantombuster_api_key:
            raise ValueError("phantombuster_api_key is empty")
        phantom_id = cfg.people_search_phantom_id or cfg.phantombuster_phantom_id
        if not phantom_id:
            raise ValueError("people_search_phantom_id is empty")
        headers = {
            "X-Phantombuster-Key-1": cfg.phantombuster_api_key,
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            launch = await client.post(
                f"{cfg.base_url.rstrip('/')}/agents/launch",
                json={
                    "id": phantom_id,
                    "argument": {
                        "company": company_domain,
                        "title": title_contains or "",
                        "limit": limit,
                    },
                },
            )
            launch.raise_for_status()
            launched = launch.json()
            agent_id = launched.get("containerId") or launched.get("id")
            if not agent_id:
                raise RuntimeError("Phantombuster launch returned no container id")
            last_payload: dict[str, Any] = {}
            for attempt in range(cfg.max_poll_attempts):
                await asyncio.sleep(cfg.poll_interval_seconds)
                response = await client.get(
                    f"{cfg.base_url.rstrip('/')}/agents/fetch-output",
                    params={"id": agent_id},
                )
                response.raise_for_status()
                last_payload = response.json()
                status = str(last_payload.get("status") or "").lower()
                if status in {"running", "launching", "todo", "not finished", ""}:
                    logger.info("people-search poll attempt=%s status=%s", attempt + 1, status)
                    continue
                if status in {"error", "failed"}:
                    raise RuntimeError(f"Phantombuster search failed: {last_payload}")
                mapped = self._map_phantom_search(company_domain, last_payload, limit)
                if not mapped:
                    raise RuntimeError("Phantombuster people-search returned empty output")
                return mapped
        raise TimeoutError(
            f"Phantombuster people-search poll exhausted after {cfg.max_poll_attempts} attempts"
        )

    def _map_phantom_search(
        self,
        company_domain: str,
        payload: dict[str, Any],
        limit: int,
    ) -> list[LinkedInProfile]:
        raw = payload.get("resultObject") or payload.get("output") or payload.get("data")
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return []
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
        if isinstance(raw, dict):
            raw = raw.get("people") or raw.get("results") or [raw]
        if not isinstance(raw, list):
            return []
        profiles: list[LinkedInProfile] = []
        for row in raw[:limit]:
            if not isinstance(row, dict):
                continue
            url = str(row.get("linkedinProfile") or row.get("profileUrl") or "").strip()
            if not url:
                continue
            try:
                username = self.extract_username(url)
            except ValueError:
                continue
            mapped = self._map_phantom_output(url, username, {"data": row})
            if mapped is not None:
                profiles.append(mapped)
        return profiles

    def _map_phantom_output(
        self,
        linkedin_url: str,
        username: str,
        payload: dict[str, Any],
    ) -> LinkedInProfile | None:
        raw = payload.get("resultObject") or payload.get("output") or payload.get("data")
        if raw is None:
            return None
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return None
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("phantombuster output is not JSON")
                return None
        if isinstance(raw, list):
            if not raw:
                return None
            raw = raw[0]
        if not isinstance(raw, dict):
            return None

        first = str(raw.get("firstName") or raw.get("first_name") or "").strip()
        last = str(raw.get("lastName") or raw.get("last_name") or "").strip()
        if not first and not last:
            return None
        title = raw.get("jobTitle") or raw.get("title") or raw.get("current_title")
        company = raw.get("companyName") or raw.get("company") or raw.get("current_company")
        return LinkedInProfile(
            linkedin_url=str(raw.get("linkedinProfile") or raw.get("profileUrl") or linkedin_url),
            username=username,
            first_name=first or username,
            last_name=last or "Unknown",
            headline=raw.get("headline"),
            current_title=str(title) if title else None,
            current_company=str(company) if company else None,
            location=raw.get("location"),
            about=raw.get("general") or raw.get("description") or raw.get("about"),
            source="phantombuster",
        )

    @staticmethod
    def extract_username(linkedin_url: str) -> str:
        """Pull the /in/{slug} segment from a profile URL."""
        match = _IN_PATH.search(linkedin_url)
        if not match:
            raise ValueError(f"Cannot extract LinkedIn username from '{linkedin_url}'")
        username = match.group(1).strip().strip("/")
        if not username:
            raise ValueError(f"Cannot extract LinkedIn username from '{linkedin_url}'")
        return username
