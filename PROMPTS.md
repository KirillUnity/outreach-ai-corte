# Prompt catalog

All LLM-facing strings in Outreach AI Cortex. Embeddings (Day 6) have no natural-language prompt.

## Cold outreach — system

- **File:** `backend/app/services/prompts/email_prompts.py` → `SYSTEM_PROMPT_OUTREACH`
- **Purpose:** Style and safety contract for a B2B cold email.
- **Variables:** `{max_words}`, `{language}`
- **Expected output:** None by itself; pairs with the user template.

## Cold outreach — user

- **File:** `backend/app/services/prompts/email_prompts.py` → `USER_PROMPT_TEMPLATE`
- **Purpose:** Recipient, RAG company context, goal, tone, sender.
- **Variables:** `{first_name}`, `{last_name}`, `{title}`, `{company_name}`, `{rag_context}`, `{goal_description}`, `{tone}`, `{sender_name}`, `{sender_title}`, `{sender_company}`, `{custom_instructions}`
- **Expected output:** JSON object `{"subject": "...", "body": "..."}` — no markdown.

## Cold outreach — validation retry

- **File:** `backend/app/services/prompts/email_prompts.py` → `VALIDATION_RETRY_SUFFIX`
- **Purpose:** One rewrite when the first draft fails `OutputValidator` or contains spam triggers.
- **Variables:** `{errors}`
- **Expected output:** Same JSON shape as the user template.

## LinkedIn / parser

No LLM prompts. LinkedIn mock is hash-based; the site parser uses trafilatura + BeautifulSoup.
