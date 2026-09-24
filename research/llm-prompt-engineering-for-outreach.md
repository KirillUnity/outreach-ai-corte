# LLM prompt engineering for cold outreach

## Why this system prompt

The system prompt is a **style contract**, not a bio of the sender. It bans the phrases that make cold email look like a template (`I hope this email finds you well`), caps the CTA at one, and forbids invented facts. Those rules belong in `system` so they stay stable across recipients. Recipient, company RAG, and sender identity belong in `user`.

`default_model=gpt-4o-mini` is the dev/default path: cheap enough to iterate on prompts. `premium_model=gpt-4o` is reserved for production once the template is stable. Temperature 0.7 is a compromise — 0.2 repeats the same sentence, 1.0 drifts into hype.

## Why JSON, not free text

The API must persist `subject` and `body` as two columns. A single blob forces fragile splitting (`Subject:` on line 1). `response_format=json_object` plus `json.loads` (with a markdown-fence strip) is cheaper than a second “extract fields” call.

Alternatives we considered:

| Format | Pros | Cons |
|--------|------|------|
| JSON object | Two fields, easy to validate | Models still wrap ```json``` sometimes |
| XML `<subject>` | Easy to regex | Noisy, models invent attributes |
| Markdown headings | Readable in logs | Heading drift (`## Subj` vs `**Subject**`) |

JSON won. If parse fails we raise `ValueError` and the router returns 502 — we do **not** guess a subject from the first line.

## First generations (mock + intended real shape)

Mock mode (`LLM_MODE=mock`) never calls OpenAI. It returns a fixed professional meeting ask so pytest and Docker health stay free:

```json
{
  "subject": "Quick idea for your team",
  "body": "I noticed your team is investing in better billing workflows. We help founders cut the time they spend on outreach research. Would you have 15 minutes next week to compare notes?"
}
```

When RAG has chunks, a real `gpt-4o-mini` draft should mention **a fact from those chunks** (product name, pricing page, audience). If the body could have been written without the company site, retrieval did not land. Check `generation_context.rag_context_used` on the saved row.

## Validation and retry

We do not silently delete spam words (`guarantee`, `free`). Deleting “free” from “free up your ops time” changes meaning. One rewrite with the validator errors appended is cheaper than shipping a damaged sentence. If the retry still fails we **save the draft anyway** and record `validation_errors` — a 500 is worse than a draft the user can edit.

## Hardware

No local models. Iris Xe / 8 GB RAM is not an inference box. Embeddings and chat stay on OpenAI or OpenRouter.
