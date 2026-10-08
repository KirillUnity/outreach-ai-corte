# Interview answers

Kirill Sokolov, before a call. Application letters stay in `docs/otklik-*.md`. Study order: [ROADMAP.md](ROADMAP.md). If that roadmap still says the GitLab file is only a prompt, ignore that line: `.gitlab-ci.yml` is in the repository. This file does not replace a résumé.

## 1. Candidate card

- **Kirill Sokolov**, Novorossiysk, remote.
- GitHub: [KirillUnity/outreach-ai-corte](https://github.com/KirillUnity/outreach-ai-corte).
- Commercial Python is **RIAC** (reporting, SQL, REST) plus this Cortex project. That is not four years of Python microservices.
- About **10 years** of commercial work on Android and Kotlin. **ComePay** is fintech. **Prognoz** is Ktor (Kotlin servers and domain/data layers), not a Python platform.
- Sole proprietor terms, summarized: full project load, 5 days × 8 hours, start soon, contract via an individual entrepreneur in Russia, **2 000 ₽/hour** (about 176 hours/month at that load). The customer’s window is the priority calendar. Wording for a recruiter: [docs/otklik-screening-ip.md](../otklik-screening-ip.md). Do not paste that letter into chat.

## 2. FAQ

| Question | Answer |
|----------|--------|
| Why FastAPI rather than Django? | Cortex is a JSON API plus an agent, not a server-rendered admin site. Pydantic v2 is both the HTTP schema and the settings model, and OpenAPI is generated from the routes, which is what I open in a demo. Routes, SQLAlchemy, and httpx are async on one event loop, which matters when a request waits on a site fetch or a cloud LLM. Routers stay thin; services hold the rules. I have not run Django in production. Django is a fair choice when you want templates and an admin. I would not claim that I had. |
| Why async SQLAlchemy 2? | New code uses `select()` and `AsyncSession` with asyncpg. The handler can await a query and an outbound HTTP call without a thread per request. I do not use the legacy Query API. A session is request-scoped. Migrations are Alembic, reviewed before `upgrade head`. The same style is what I would bring to a service that talks to Postgres and one or two vendor APIs. |
| How do you test without spending LLM money? | `LLM_MODE=mock` and `RAG_MODE=mock`. Mock chat returns deterministic JSON. Mock embeddings are hash vectors, not a local neural net. Hunter, Apollo, and Bitrix are covered with `httpx.MockTransport` (401, 429, success) so pytest never calls those hosts. The health endpoint inspects LLM config and does not send a prompt. CI sets the same mock flags. I turn `LLM_MODE=real` on only when I mean to spend. |
| Which LangGraph nodes exist? | In `backend/app/services/agent/graph.py`, in order: `load_person`, `research_company`, `retrieve_rag`, `enrich_with_graph`, `find_email`, `generate_email`, `validate_email`, `check_deliverability`, `decide`, then `save_draft` or `save_and_send`. `find_email` is a real node, not a slide. `decide` returns hold while human approval is required. `save_and_send` marks a Postgres row sent. It does not open SMTP. |
| Why Neo4j? | Warm-intro paths and “who at this company is uncontacted” are graph lookups. Postgres stays the system of record; Neo4j is a query index, synced in batch, not on every write. Heap and page cache are capped because the host has 8 GB. On a 1 GB VPS the `extra` Compose profile leaves Neo4j off. I have not run a multi-node graph cluster. |
| Docker Compose or Kubernetes? | For this product, Compose. One VPS, one operator, `mem_limit` and healthchecks on every service, Postgres unpublished. I have not deployed Kubernetes, Helm, Minikube, or k3s, and I do not recommend them here. A control plane would spend the RAM the API needs. If a company already runs Kubernetes I can learn their manifests. I will not say I have operated one. |
| GitLab CI? | `.gitlab-ci.yml` is in the repo. Stages are `test` and `build`. The backend job uses Python 3.12, a Postgres 16 service, Poetry, Alembic, and pytest, with LLM, RAG, and LinkedIn in mock and Neo4j and Langfuse off. The frontend job runs `npm ci`, build, and tests. GitHub Actions does the same kind of check. I have not administered a company’s GitLab or its runners. An older letter said CI was not set up yet; the YAML exists now. That is still not “I ran production GitLab.” |
| Redis or Kafka? | Neither is in this project, and I have not run them in production. Cortex state is Postgres: drafts, `agent_runs`, sequences, warmup events, CRM sync rows. The agent checkpointer defaults to in-process memory. Scheduled work is an HTTP tick, including n8n JSON you import elsewhere. I would not rename that “a broker.” If a team needs Kafka, that is a new sprint with a local Compose service and a fake producer in tests. |
| Phantombuster, Apollo, n8n — real or mock? | Phantombuster: a real HTTP client when `LINKEDIN_MODE=real` and a key and phantom id are set; otherwise a deterministic mock, and real mode falls back to mock on HTTP errors. This repo does not scrape LinkedIn. Apollo: `ApolloClient` returns an empty list unless `APOLLO_ENABLED` and a key are set. n8n is three JSON workflows (`warmup_tick`, `outreach_run`, `article_publish`), not a Compose service. CRM defaults to `MockCrmClient`; Bitrix24 and retailCRM POST only when their URL or key is set. |
| A sales bot drifts (length, CTA, offer). What do you change? | I keep one bad transcript and name the failure. Length: the structure guardrail warns outside about 50–200 words, and the system prompt has `max_words`. CTA: missing a next step is an error; the copy allows one ask, and variant `v1_direct_cta` adds “one 15-minute CTA, do not stack questions.” Offer: the prompt may use only the research context; the hallucination rail flags unknown entities; a retry suffix lists what failed. I edit `email_prompts.py`, replay a pytest fixture in mock mode, and compare the draft. I do not “fix” drift by raising temperature. The same loop is how I would tune a sales chatbot. I have not worked on the Chatix product itself. |
| Sequences and spam? | Sequences are an Instantly-shaped state machine: steps JSON, enroll a person once, tick advances `current_step`. `SequenceService.emails_sent` stays 0. There is no SMTP send and no mailbox blast. Warmup volume is simulated. I would not call this an Instantly integration or a sending platform. |

## 3. Board questions

Say these in a few sentences. Sources: `research/email-finding-strategies.md`, `research/email-deliverability-2024.md`, `research/b2b-email-deliverability.md`, and the code those notes point at.

### Email finder

1. **Why is live SMTP `RCPT TO` off?**  
   `HELO` / `MAIL FROM` / `RCPT TO` against someone else’s MX looks like list probing. Providers burn the source IP. Catch-all domains answer 250 for every local-part, so the probe is both noisy and useless. Cortex keeps `SMTP_VERIFICATION_ENABLED=false`. The verifier records a mock status.

2. **When does a guess become primary?**  
   Patterns are saved from confidence 0.3 (`min_confidence_to_save`). Primary is only at or above 0.6 (`min_confidence_to_use`), or when a person calls set-primary. `{first}.{last}` is 0.85, `{first}{last}` is 0.75, `{f}{last}` is 0.70, `{first}` is 0.5, other patterns fall back to 0.4.

3. **What happens on a catch-all?**  
   Mock SMTP status `catchall` caps confidence at 0.3, so it cannot auto-promote to primary. Status `invalid` zeros confidence. Status `valid` adds 0.1, capped at 1.0. I still would not send blindly; the agent hold is the human check.

4. **What do Hunter and Apollo add when keys exist?**  
   Hunter’s score is divided by 100 and capped at 0.9. Apollo’s confidence is capped at 0.85. A LinkedIn-sourced address is stored at 0.9. With flags off or keys empty, both clients return nothing and patterns still run. I say that out loud on a demo.

5. **Why keep two or three candidates?**  
   One pattern is a guess. The notes say to keep a small set (profile, Hunter if enabled, top pattern) and log `source` so later you can see which provider actually hit. Deleting a bad row is a separate endpoint. I do not treat the top pattern as a verified mailbox.

### Agent

6. **Why does the default run hold?**  
   `AGENT_REQUIRE_HUMAN_APPROVAL=true`. `decide` returns `hold` / `awaiting approval` after validation and the deliverability snapshot. The draft is still stored via `save_draft`. Send is a later explicit decision. `save_and_send` only flip a sent flag in Postgres.

7. **What is the node order, including find_email?**  
   `load_person`, `research_company`, `retrieve_rag`, `enrich_with_graph`, `find_email`, `generate_email`, `validate_email`, `check_deliverability`, `decide`, then save. If load returns errors, the graph stops. After validate, a dirty draft may generate once more (`iteration` under 2), then it still moves on to deliverability.

8. **How do guardrails fail?**  
   They return a result: passed, reason, severity. They do not raise. Error and critical severities block. Warnings are recorded. The pipeline runs the rails together. A retry suffix is appended for a second generation. PII, spam phrases, missing CTA, and unknown entities are separate rails.

9. **Why is `thread_id` `{person_id}:{uuid}`?**  
   The checkpointer would otherwise resume an old thread for that person. A new id means a new run. The default checkpointer is in-process memory so pytest does not need another table. Postgres checkpointing is a setting, not something I describe as a second database product.

10. **What do you watch after a run?**  
    `agent_runs` stores decision, token counts, cost, and duration. Langfuse, when keys exist, has the trace. `CostTracker` prices `gpt-4o-mini` and `gpt-4o` from a static table and warns if one run crosses about one dollar. Metrics can count runs by decision bucket. I do not put `person_id` on a Prometheus label.

### Deliverability

11. **What does Cortex actually check?**  
    `GET /api/v1/deliverability/check/{domain}` looks up SPF, DKIM, DMARC, and MX over DNS and can store `domain_health`. The agent node reads that snapshot. It does not re-query DNS on every graph step, and it does not sign DKIM for you.

12. **SPF in one breath?**  
    One `v=spf1` TXT. A second SPF TXT is an error. Stay near the 10-lookup limit. End at `-all` only after you know every sender. The checker reports the record; it does not edit DNS.

13. **How do you roll out DMARC?**  
    Start at `p=none` with `rua` and watch reports. Then `quarantine`, then `reject`. Alignment means the From domain matches SPF and/or DKIM. I would not flip a customer domain to `reject` on day one.

14. **Why is open rate a weak KPI?**  
    Apple Mail Privacy Protection prefetches pixels, so “opened” is not “a person read it.” I would talk about bounce, complaints, and replies. The warmup emulator’s open rate is simulated and I label it that way.

15. **Warmup versus a sending product?**  
    Instantly-style tools send and warm real mailboxes. Cortex warmup is a peer-network simulator in Postgres: volume by day, reputation, no SMTP. The sequence model borrows the shape of a campaign (steps, enroll, tick) and sends nothing. Cold mail belongs on a subdomain, separate from transactional mail, if someone later sends for real. I have not operated that sender.

## 4. Red flags — do not say these

- “I deployed Kubernetes” / “we run Helm in production” / “I can admin the cluster.” Compose only, until that changes in a real job.
- “Production Kafka” or “we already use Redis as the bus.” Not in Cortex, not in my production history.
- “Four years as a Python senior in a bank” or “four years of microservices.” Commercial Python is RIAC plus Cortex. ComePay and Prognoz are not Python-senior years.
- “Instantly is integrated” or “the agent sends the email.” The sequence does not send. The send node marks a row.
- “Hunter found this address” when the demo key is empty.
- “I ran production GitLab.” The YAML is in the repo. I have not operated their GitLab.
- “I worked on Chatix.” I have not. I can show the email guardrails as the same kind of prompt repair.

## 5. Short answers to the meta questions

**Admitting a gap.** Name it in one sentence, point at the nearest real piece, then offer one sprint. Example: “I have not run Kafka. Cortex uses Postgres and HTTP ticks. In one sprint I would add a Compose broker, a producer behind a flag, a pytest fake, a memory limit, and a demo of one warmup tick going through it. I would not call that production.”

**Estimating a task that calls an external API.** Split it: read the contract, httpx client with timeout, map 401 and 429, tests on `MockTransport`, then the service method, then the route. That is about one to three days for a client the size of Hunter, plus a day if their sandbox is flaky, plus their price per call times volume. I do not start with a scraper, and I do not hide the key in the image.

**Mock versus real on a demo.** Say “mock” before the click. Show `LLM_MODE` and `HUNTER_ENABLED`. If they want Hunter, show the client and the unit test, not a fake success. If the UI and the env disagree, trust the code path that checks the key.

**Combining jobs.** From the screening note only: the customer’s 8 hours, 5 days a week, is the priority calendar. Other work is outside that window. I have not held two full-time jobs at once. Cortex was built beside the main job without dropping deadlines. On this contract the customer is the first calendar. I do not invent extra free hours on the call.

**Cost of 1 000 emails (estimate, not a bill).** Mock mode is $0. The table in `cost_tracker.py` prices `gpt-4o-mini` at $0.15 / 1M input tokens and $0.60 / 1M output, and `gpt-4o` at $2.50 and $10. Assumption: about 800 input tokens and 200 output tokens per letter, one call, no embedding reindex. Mini is about $0.00024 per letter, about **$0.24 per 1 000**. One guardrail retry doubles that, about **$0.48**. The same shape on `gpt-4o` is about **$4 per 1 000**, or about $8 with one retry. Unknown model names use the mini rates. Embeddings are not in that table.
