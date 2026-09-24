"""LLMClient unit tests — AsyncOpenAI is faked, no tokens spent."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import LLMSettings, Settings
from app.services.llm_client import LLMClient


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]
        self.usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7)
        self.model = "gpt-4o-mini"


class _FakeCompletions:
    def __init__(self, contents: list[str] | None = None, errors: list[Exception] | None = None) -> None:
        self.contents = list(contents or [])
        self.errors = list(errors or [])
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        if self.errors:
            raise self.errors.pop(0)
        content = self.contents.pop(0) if self.contents else '{"subject":"Hi","body":"Hello"}'
        return _FakeCompletion(content)


def _client(completions: _FakeCompletions) -> LLMClient:
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    settings = Settings(
        llm=LLMSettings(mode="real", openai_api_key="sk-test"),
        llm_mode="real",
        openai_api_key="sk-test",
    )
    return LLMClient(settings, client=fake, backoff_seconds=0.0)


async def test_chat_returns_content_and_tokens() -> None:
    completions = _FakeCompletions(contents=['{"subject":"Hi","body":"Hello"}'])
    client = _client(completions)
    result = await client.chat("sys", "user")
    assert result["content"]
    assert result["tokens_input"] == 11
    assert result["tokens_output"] == 7
    assert result["model"] == "gpt-4o-mini"
    assert completions.calls == 1


async def test_chat_retries_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeCompletions(
        contents=['{"subject":"Hi","body":"Hello after retry"}'],
        errors=[RuntimeError("rate")],
    )
    monkeypatch.setattr(LLMClient, "_is_retryable", staticmethod(lambda _exc: True))
    client = _client(completions)
    result = await client.chat("sys", "user")
    assert "retry" in result["content"] or result["content"]
    assert completions.calls == 2


async def test_chat_json_parses_valid_json() -> None:
    completions = _FakeCompletions(contents=['{"subject":"Meet","body":"Let us talk"}'])
    client = _client(completions)
    result = await client.chat_json("sys", "user")
    assert result["parsed"]["subject"] == "Meet"
    assert result["parsed"]["body"] == "Let us talk"


async def test_chat_json_handles_markdown_wrapped_json() -> None:
    wrapped = '```json\n{"subject":"Meet","body":"Let us talk"}\n```'
    completions = _FakeCompletions(contents=[wrapped])
    client = _client(completions)
    result = await client.chat_json("sys", "user")
    assert result["parsed"]["subject"] == "Meet"


async def test_chat_json_raises_on_invalid_json() -> None:
    completions = _FakeCompletions(contents=["not-json-at-all"])
    client = _client(completions)
    with pytest.raises(ValueError, match="invalid JSON"):
        await client.chat_json("sys", "user")


def test_parse_json_strips_fences() -> None:
    client = LLMClient(Settings(llm_mode="mock"))
    parsed = client._parse_json('```\n{"subject":"A","body":"B"}\n```')
    assert parsed == {"subject": "A", "body": "B"}


def test_mock_mode_does_not_need_api_key() -> None:
    client = LLMClient(Settings(llm_mode="mock"))
    assert client._client is None
    _ = uuid4()
