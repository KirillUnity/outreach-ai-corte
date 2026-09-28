"""Thin async wrapper around OpenAI-compatible chat APIs (OpenAI or OpenRouter)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from app.core.config import Settings, settings as default_settings
from app.services.cost_tracker import CostTracker
from app.services.tracing import TracingService, get_tracing

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class LLMClient:
    """Chat completions with retry + JSON parsing. Mock mode never hits the network."""

    def __init__(
        self,
        settings: Settings | None = None,
        cost_tracker: CostTracker | None = None,
        client: Any = None,
        tracing: TracingService | None = None,
        backoff_seconds: float = 1.0,
        max_attempts: int = 4,
    ) -> None:
        self.settings = settings or default_settings
        self.cost_tracker = cost_tracker or CostTracker()
        self.tracing = tracing if tracing is not None else get_tracing()
        self.backoff_seconds = backoff_seconds
        self.max_attempts = max_attempts
        self._client = client
        if self._client is None and self.settings.llm.mode == "real":
            self._client = self._build_client()

    def _build_client(self) -> Any:
        from openai import AsyncOpenAI

        llm = self.settings.llm
        timeout = llm.request_timeout
        if llm.provider == "openrouter":
            if not llm.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY is empty — cannot call LLM in real mode")
            return AsyncOpenAI(
                api_key=llm.openrouter_api_key,
                base_url=llm.openrouter_base_url,
                timeout=timeout,
            )
        if not llm.openai_api_key:
            raise ValueError("OPENAI_API_KEY is empty — cannot call LLM in real mode")
        return AsyncOpenAI(api_key=llm.openai_api_key, timeout=timeout)

    async def chat(
        self,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Return content + token usage. Retries rate limits / timeouts with backoff."""
        llm = self.settings.llm
        chosen_model = model or llm.default_model
        temp = llm.temperature if temperature is None else temperature
        tokens = llm.max_tokens if max_tokens is None else max_tokens

        if llm.mode == "mock" and self._client is None:
            return await self._chat_traced(system, user, chosen_model, lambda: self._mock_chat(system, user, chosen_model))

        async def _call() -> dict[str, Any]:
            last_error: Exception | None = None
            for attempt in range(self.max_attempts):
                try:
                    kwargs: dict[str, Any] = {
                        "model": chosen_model,
                        "temperature": temp,
                        "max_tokens": tokens,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    }
                    if response_format is not None:
                        kwargs["response_format"] = response_format
                    completion = await self._client.chat.completions.create(**kwargs)
                    choice = completion.choices[0]
                    content = (choice.message.content or "").strip()
                    usage = completion.usage
                    tokens_input = int(getattr(usage, "prompt_tokens", 0) or 0)
                    tokens_output = int(getattr(usage, "completion_tokens", 0) or 0)
                    used_model = getattr(completion, "model", None) or chosen_model
                    self.cost_tracker.log_chat(used_model, tokens_input, tokens_output)
                    return {
                        "content": content,
                        "tokens_input": tokens_input,
                        "tokens_output": tokens_output,
                        "model": used_model,
                    }
                except Exception as exc:
                    if not self._is_retryable(exc) or attempt == self.max_attempts - 1:
                        raise
                    last_error = exc
                    delay = self.backoff_seconds * (2**attempt)
                    logger.warning(
                        "llm retry attempt=%s delay=%s error=%s",
                        attempt + 1,
                        delay,
                        exc,
                    )
                    if delay:
                        await asyncio.sleep(delay)
            raise last_error or RuntimeError("LLM chat failed")

        return await self._chat_traced(system, user, chosen_model, _call)

    async def chat_json(
        self,
        system: str,
        user: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Like chat(), but parse a JSON object from the model content."""
        raw = await self.chat(
            system,
            user,
            response_format={"type": "json_object"},
            **kwargs,
        )
        parsed = self._parse_json(raw["content"])
        return {**raw, "parsed": parsed}

    async def _chat_traced(
        self,
        system: str,
        user: str,
        model: str,
        producer: Any,
    ) -> dict[str, Any]:
        """Keep system vs user as separate fields so prompt diffs are obvious in Langfuse."""
        started = time.perf_counter()
        with self.tracing.trace_generation(
            name="llm_chat",
            model=model,
            input_payload={"system": system, "user": user},
        ) as gen:
            try:
                result = producer()
                if hasattr(result, "__await__"):
                    result = await result
                duration_ms = (time.perf_counter() - started) * 1000
                cost = 0.0
                if self.cost_tracker.records:
                    cost = self.cost_tracker.records[-1].estimated_cost_usd
                gen.update(
                    output=result.get("content"),
                    usage={
                        "input": result.get("tokens_input", 0),
                        "output": result.get("tokens_output", 0),
                        "total": int(result.get("tokens_input") or 0)
                        + int(result.get("tokens_output") or 0),
                    },
                    metadata={"cost_usd": cost, "duration_ms": round(duration_ms, 2)},
                )
                return result
            except Exception as exc:
                gen.update(level="ERROR", status_message=str(exc))
                raise

    def _parse_json(self, content: str) -> dict[str, Any]:
        """Parse model JSON; strip markdown fences on the first failure."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            cleaned = _FENCE_RE.sub("", content.strip())
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("LLM JSON must be an object")
        return data

    def _mock_chat(self, system: str, user: str, model: str) -> dict[str, Any]:
        """Deterministic JSON email so CI never spends tokens."""
        subject = "Quick idea for your team"
        body = (
            "I noticed your team is investing in better billing workflows. "
            "We help founders cut the time they spend on outreach research. "
            "Would you have 15 minutes next week to compare notes?"
        )
        payload = json.dumps({"subject": subject, "body": body})
        tokens_input = max(1, (len(system) + len(user)) // 4)
        tokens_output = max(1, len(payload) // 4)
        used_model = f"mock-{model}"
        self.cost_tracker.log_chat(used_model, tokens_input, tokens_output)
        return {
            "content": payload,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "model": used_model,
        }

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        try:
            from openai import APITimeoutError, RateLimitError
        except ImportError:
            return False
        return isinstance(exc, RateLimitError | APITimeoutError)
