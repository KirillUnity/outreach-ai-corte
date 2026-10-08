# Video script (5 minutes)

English voiceover. Read it aloud. Do not promise a vendor call you did not make. Screen recording stays on your machine (`*.mp4` / `*.mov` are gitignored).

Target pace: about 130 words per minute. The block at 2:10 includes a **20-second** beat on prompt tone for a sales-chatbot screening.

## 0:00 — Cold outreach

Cold outreach fails when the first email is generic, the address is a guess, and nobody checks whether the domain can receive mail. I built a small system that researches a company, finds a person, drafts one email, and holds it until a human says send.

## 0:30 — Stack

The stack is FastAPI, PostgreSQL, retrieval over Chroma, and a LangGraph agent. Models are cloud APIs only. Nothing runs as a local language model. The code is on GitHub: https://github.com/KirillUnity/outreach-ai-corte

## 1:00 — Company and person research

Here is company research for stripe.com. The API fetches the public site, stores the text, and indexes chunks. Then person research. In the default mode this is a deterministic mock profile, not a LinkedIn scrape. The same URL always returns the same name and title.

## 1:40 — Email finder

Email find builds candidates from name patterns, such as first dot last at the company domain. Confidence decides what can become primary. I am not calling Hunter or Apollo in this demo. Those clients stay off without an API key. There is no live SMTP probe.

## 2:10 — Agent hold, guardrails, and tone (includes ~20 seconds)

The agent loads the person, researches if needed, retrieves context, reads the graph, finds an email, generates, validates, checks deliverability, and then decides. With human approval on, the decision is hold, not send.

If I were tuning a sales chatbot and the bot drifted, I would fix the prompt the same way I fix these emails. Too long: the structure check wants roughly fifty to two hundred words. No next step: one call to action, not three. Offer off-message: the system prompt allows only facts from the research context, and a retry suffix tells the model what failed. I edit the template, rerun a fixture, and compare the draft. I do not just raise the temperature.

## 2:40 — Warmup emulator

Warmup is an emulator. The mailbox card and the timeline show simulated opens and replies. No mail leaves the machine. It is a picture of reputation over days, not a real inbox warmer.

## 3:10 — SEO article

The same research can draft an SEO article for a content-marketing workflow. Generate stores a draft for review. Optimize fills the meta title, description, and safe internal links. Publishing defaults to a mock URL until a webhook is configured.

## 3:40 — n8n and CRM

n8n is JSON you import yourself: a warmup tick, an outreach run, and article publish. It is not a container in Compose. CRM sync defaults to a mock client. Bitrix or retailCRM run only when a webhook URL or a key is set, and those secrets stay in the environment file.

## 4:10 — Limits

Limits, said plainly. Hunter, Apollo, and Phantombuster are mocks until keys exist. The design target is eight gigabytes of RAM and no local language model. Production on one VPS is Docker Compose. I am not recommending Kubernetes for this project.

## 4:40 — Close

If you want to go deeper, ask where a router stops and a service starts, why Postgres is not published to the internet, or how the agent decides to hold. I can show the OpenAPI docs or the architecture note. I am happy to take questions.
