# Langfuse screenshots

Drop PNG captures from http://localhost:3001 here after a real run. The UI is the source of truth; this folder is only for interview/demo evidence.

## Suggested captures

| File | What to show |
|------|----------------|
| `01-project-keys.png` | Project **outreach-ai-cortex**, Public Key visible, Secret Key masked |
| `02-trace-generate-email.png` | Trace after `POST /api/v1/persons/{id}/generate-email`: input `system` + `user`, output JSON, tokens, latency |
| `03-trace-agent-graph.png` | Nested spans for `load_person` → … → `decide` (metadata: decision, reason, validation_errors) |
| `04-dashboard.png` | Dashboard: call count, p95 latency, estimated cost |
| `05-scores.png` | `length_score` / `spam_score` / `personalization_score` / `cta_score` on a draft |

## How to produce them

1. `docker compose up -d langfuse-db langfuse` then the rest of the stack.
2. Register the first user, create the project, paste keys into `.env`, recreate `api`.
3. Generate one mock email, then one `POST /api/v1/agent/outreach`.
4. Traces → open the newest row → screenshot. Dashboard → screenshot.

Do not commit Secret Keys or `.env`.
