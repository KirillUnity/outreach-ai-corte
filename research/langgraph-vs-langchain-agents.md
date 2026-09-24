# LangGraph vs LangChain AgentExecutor

## Why a graph, not AgentExecutor

`AgentExecutor` lets the model pick tools in a loop. That is useful for open-ended research. Cold outreach is **not** open-ended: we always load the person, maybe research the site, retrieve, generate, validate, check DNS snapshots, then decide. A `StateGraph` with named edges encodes that policy in code. The LLM writes the email; it does not choose whether to skip deliverability.

Deterministic routing is what we test in `test_agent_edges.py` without spending tokens.

## What we kept from LangChain

Chunking and (optional) OpenAI embeddings stay on LangChain splitters / `langchain-openai`. Chat itself is `AsyncOpenAI` so retries and JSON parsing stay explicit.

## Checkpointing

`thread_id` keys a checkpoint so a crash mid-graph can resume. We **do not** reuse `person_id` as `thread_id`: a second outreach would resume stale `validation_errors` / iteration. Each `run()` uses `{person_id}:{uuid4()}`.

In-process we compile with `MemorySaver` so pytest needs no extra Postgres tables. `langgraph-checkpoint-postgres` is on the dependency list for a later lifespan-owned `AsyncPostgresSaver` (needs `setup()` and a psycopg pool). `agent_runs.final_state` is the product audit trail either way.

## What we exercised

- Happy path with fakes: `decision=send` when approval and deliverability gates are off.
- Missing person: graph ends at `fail`, no draft.
- `decide`: reject on validator errors, hold on DKIM/SPF, hold on `require_human_approval`.
- Validate loop: one regenerate (`iteration < 2`), then continue. `validation_errors` **overwrites** (not `add`) so a clean rewrite can proceed.

## Hardware

No local models. The graph only calls cloud chat when `LLM_MODE=real`.
