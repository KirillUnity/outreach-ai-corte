# Prompt catalog (v1.2)

All LLM-facing strings live in `backend/app/services/prompts/email_prompts.py`. Change copy there, then note the changelog below. Embeddings have no NL prompt. LinkedIn mock and the site parser do not call an LLM.

## System prompts

### outreach_email_system (`SYSTEM_PROMPT_OUTREACH`)

- **Purpose:** Contract for a B2B cold email: tone, one CTA, no invented facts, JSON-only pairing with the user template.
- **Variables:** `{max_words}`, `{language}`
- **Expected output:** None alone. Combined with the user prompt the model must return `{"subject": "...", "body": "..."}`.
- **Good:** Short observation about the recipient’s product, one ask for 15 minutes, no buzzwords.
- **Bad:** “I hope this email finds you well”, ALL CAPS, two CTAs, facts not in RAG.
- **Changelog:** v1.0 initial. v1.1 spam-word ban + JSON example. v1.2 guardrail retry suffix (do not invent phones/companies).

## User prompts

### email_generation_user (`USER_PROMPT_TEMPLATE`)

| Variable | If omitted |
|----------|------------|
| `{first_name}` `{last_name}` | Generic “Hi there” — personalization_score drops |
| `{title}` | Weaker RAG query and opener |
| `{company_name}` | Model invents a company (hallucination rail) |
| `{rag_context}` | Empty research disclaimer — still must not invent |
| `{goal_description}` | Vague CTA |
| `{tone}` | Defaults in the HTTP schema, not here |
| `{sender_*}` | Unsigned letter |
| `{custom_instructions}` | Empty string; used for validator/guardrail retries |

**Expected output:** JSON object only, no markdown fences (parser strips fences as a fallback).

### Validation / guardrail retries

- `VALIDATION_RETRY_SUFFIX` — `{errors}` from `OutputValidator` / spam list.
- `GUARDRAIL_RETRY_SUFFIX` — `{reasons}` from blocking guardrails (PII, policy, structure CTA, 4+ unknown entities).

## Prompt patterns we use

- **JSON output** — `response_format=json_object` in real mode; mock returns JSON too.
- **Few-shot** — one inline example object in the user template (shape, not a full email).
- **Chain of thought** — not used on the hot path (extra tokens, extra $). Guardrails are deterministic instead.
- **Role prompting** — “expert B2B sales copywriter” in the system prompt.

## Anti-patterns

- “I hope this email finds you well”
- Generic “increase revenue / scale your business”
- Letters over ~120 words (system `max_words`; structure rail warns outside 50–200)
- URL shorteners, ALL CAPS, stacked CTAs

## Versioning

**Current: v1.2**

| Version | Change | What we watch |
|---------|--------|----------------|
| v1.0 | First system+user pair | Mock fixture stability |
| v1.1 | Spam list + JSON-only | `spam_score`, parse errors |
| v1.2 | Guardrail retry copy | `guardrails/failures`, reject rate |

A/B: `PROMPT_AB_ENABLED=true` picks `v1_default` vs `v1_direct_cta` (`app.services.prompt_ab`). Log `prompt_variant` on Langfuse generations. Keep A/B **off** in CI.

## Why this file exists

The team can diff prompt copy in git, map a Langfuse `release` to a row here, and avoid “the prompt is buried in a 400-line service.”
