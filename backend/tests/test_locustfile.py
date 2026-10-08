"""Smoke checks for the read-only Locust file (no live server required)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_LOCUSTFILE = _ROOT / "loadtest" / "locustfile.py"


def test_locustfile_only_documents_readonly_gets() -> None:
    """The swarm file must stay GET-only against health and metrics."""
    source = _LOCUSTFILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    urls: list[str] = []
    methods: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        methods.add(func.attr)
        if func.attr in {"get", "post", "put", "patch", "delete"} and node.args:
            arg0 = node.args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                urls.append(arg0.value)
    assert methods.isdisjoint({"post", "put", "patch", "delete"})
    assert "/api/v1/health" in urls
    assert "/metrics" in urls
    assert all("/agent/outreach" not in u for u in urls)


def test_readonly_user_task_names() -> None:
    """If locust is installed, the HttpUser exposes health and metrics tasks."""
    pytest.importorskip("locust")
    import sys

    loadtest_dir = str(_ROOT / "loadtest")
    if loadtest_dir not in sys.path:
        sys.path.insert(0, loadtest_dir)
    import locustfile  # type: ignore[import-not-found]

    raw = locustfile.ReadOnlyUser.tasks
    fns = raw.keys() if isinstance(raw, dict) else raw
    names = {fn.__name__ for fn in fns}
    assert names == {"health", "metrics"}
