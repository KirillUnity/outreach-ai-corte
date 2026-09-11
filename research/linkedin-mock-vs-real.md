# LinkedIn: mock vs real

Outreach needs a person snapshot (name, title, company) before drafting email. Hitting LinkedIn from our servers is a product and legal dead end. This note records why the service has two modes.

## What we ship

| Mode | When | Network |
|------|------|---------|
| **mock** (default) | Local Docker, CI, demos | None. `sha256(username)` picks a stable fake profile. |
| **real** | Staging/prod with a vendor key | Phantombuster agent launch + poll. Failures fall back to mock. |

Cache in Postgres (`persons.linkedin_url` unique) is the first line of defense in both modes: a second research call does not spend a credit.

## Alternatives considered

**Own Selenium / Playwright scraper.** Fast to prototype, immediately against LinkedIn ToS, brittle against anti-bot, easy SSRF/account-ban surface, and a compliance incident waiting to happen. Rejected.

**SalesQL / Apollo / similar B2B APIs.** Cleaner contracts, paid data. Worth a later adapter behind the same `LinkedInService.get_profile` interface. Not day-5 scope (extra vendor, extra PII DPA).

**Phantombuster.** SaaS “phantom” already specialized in LinkedIn Profile Scraper. We launch an agent and poll; we do not drive a browser. Credits and ToS sit with the vendor. Still not “free scraping”, but it is a bounded, key-gated integration with a mock fallback.

## Trade-offs

- **Mock + hash, not `random`:** tests and demos are idempotent. Random names would make cache tests flake and hide bugs in “same URL twice”.
- **Fallback to mock on real failure:** outreach CRUD stays usable if Phantombuster is down. Logs a warning so ops can see credit/API issues.
- **No headless Chrome in our 512 MB API container:** hardware constraint from project rules; a local scraper would not fit anyway.

## Risks we still accept

Phantombuster (and any enrichment vendor) may still violate LinkedIn’s rules depending on how the phantom is configured. Production should: store only fields we need, honor deletion requests, rate-limit research, and keep `LINKEDIN_MODE=mock` until legal has signed off.
