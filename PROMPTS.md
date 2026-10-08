# Prompt catalog (v1.3)

All LLM-facing strings live in `backend/app/services/prompts/email_prompts.py`. Change copy there, then note the changelog below. Embeddings have no NL prompt. LinkedIn mock and the site parser do not call an LLM.

## System prompts

### outreach_email_system (`SYSTEM_PROMPT_OUTREACH`)

- **Purpose:** Contract for a B2B cold email: tone, one CTA, no invented facts, JSON-only pairing with the user template.
- **Variables:** `{max_words}`, `{language}`
- **Expected output:** None alone. Combined with the user prompt the model must return `{"subject": "...", "body": "..."}`.
- **Good:** Short observation about the recipient’s product, one ask for 15 minutes, no buzzwords.
- **Bad:** “I hope this email finds you well”, ALL CAPS, two CTAs, facts not in RAG.
- **Changelog:** v1.0 initial. v1.1 spam-word ban + JSON example. v1.2 guardrail retry suffix (do not invent phones/companies). v1.3 warm-intro user template.

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
| `{email_hint}` | Built in `EmailGenerator`, not by the HTTP client. If the graph already found an address, the line is `Recipient email: {address}`. Otherwise `Recipient email: not found — email will need manual lookup`. A stored `Person.email` fills that gap. The model must not invent a different address. |

**Expected output:** JSON object only, no markdown fences (parser strips fences as a fallback).

### email_generation_user_warm_intro (`USER_PROMPT_WITH_WARM_INTRO`)

Same variables as `USER_PROMPT_TEMPLATE`, plus `{mutual_connection_name}`.

- **Purpose:** Only used when `graph_context.warm_intro_available` is true **and** we have a real name (not “a mutual connection”). Forces the opener to mention that person and forbids invented intro details.
- **Good:** “Ada mentioned you are hiring a RevOps lead…”
- **Bad:** Inventing that Ada works at Stripe or that you had lunch last week.
- **Changelog:** v1.3 added for Day 14 graph personalization. `{email_hint}` is on this template too.

## Article prompts (`article-v1`)

Source: `backend/app/services/prompts/article_prompts.py`. Constant `ARTICLE_PROMPT_VERSION = "article-v1"`. Separate from the email catalog.

### article_system (`SYSTEM_PROMPT_ARTICLE`)

- **Purpose:** Factual B2B SEO draft. Facts only from RAG. If context is missing, the model must say company-specific claims need editorial review.
- **Variables:** `{max_words}`, `{language}`
- **Expected output:** One JSON object: `title`, `slug`, `body_markdown`. Slug is lowercase ASCII kebab-case.
- **Good:** One H1, clear H2s, no invented customers or metrics.
- **Bad:** Awards, quotes, or URLs that are not in the context. URL shorteners.

### article_user (`USER_PROMPT_ARTICLE`)

| Variable | If omitted |
|----------|------------|
| `{company_name}` | The article cannot stay grounded |
| `{keyword}` | No SEO target |
| `{language}` `{max_words}` | Generator always passes them (default language `ru`, 800 words on the HTTP schema) |
| `{rag_context}` | Model must refuse invented company facts |

**Changelog:** article-v1 initial. Optimize (`POST /articles/{id}/optimize`) does not call this prompt; it fills meta fields in code.

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

**Current: v1.3**

| Version | Change | What we watch |
|---------|--------|----------------|
| v1.0 | First system+user pair | Mock fixture stability |
| v1.1 | Spam list + JSON-only | `spam_score`, parse errors |
| v1.2 | Guardrail retry copy | `guardrails/failures`, reject rate |
| v1.3 | Warm-intro user prompt | `generation_context.graph_context`, reply rate |

## Prompt A/B

`PromptABTester` in `backend/app/services/prompt_ab.py` is real. It is off unless `PROMPT_AB_ENABLED=true` (`PromptABSettings.enabled`, default false) so CI stays deterministic. There is no separate experiment service and no stored assignment table.

| Variant | Suffix appended to the user prompt |
|---------|--------------------------------------|
| `v1_default` | empty |
| `v1_direct_cta` | Prefer a single concrete CTA with a 15-minute window. Do not stack questions. |

`pick_variant` chooses with equal weights. `log_result` keeps in-process trials, success rate, and average score. Log `prompt_variant` on Langfuse generations when tracing is on. Keep A/B **off** in CI.

## Why this file exists

The team can diff prompt copy in git, map a Langfuse `release` to a row here, and avoid “the prompt is buried in a 400-line service.”
