"""A failed SDK run must not drop the other repos in the batch."""
import asyncio
import json
from pathlib import Path

import agent.audit as audit
from agent.audit import ResultMessage

_FIELDS = {
    "leakage": "none",
    "temporal_ok": True,
    "baseline_reported": True,
    "reproducible": True,
    "findings": [],
    "confidence": "high",
}


def _message(*, structured=None, result=None) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id="test",
        result=result,
        structured_output=structured,
    )


def _yielding(message):
    async def fake_query(*, prompt, options=None, transport=None):
        yield message

    return fake_query


def _raising():
    async def fake_query(*, prompt, options=None, transport=None):
        raise RuntimeError("sdk connection reset")
        yield None  # keeps this an async generator so async for raises RuntimeError

    return fake_query


async def _fake_query(*, prompt, options=None, transport=None):
    if "broken-repo" in prompt:
        raise RuntimeError("sdk connection reset")
    yield _message(structured=dict(_FIELDS))


def test_sdk_exception_keeps_the_other_repo(tmp_path, monkeypatch):
    broken = tmp_path / "broken-repo"
    ok = tmp_path / "ok-repo"
    broken.mkdir()
    ok.mkdir()
    monkeypatch.setattr(audit, "query", _fake_query)

    rows = asyncio.run(audit.audit_many([broken, ok], concurrency=2))

    assert [row["repo"] for row in rows] == ["broken-repo", "ok-repo"]
    assert rows[0]["error"] == "exception"
    assert "RuntimeError: sdk connection reset" in rows[0]["raw"]
    assert rows[1]["leakage"] == "none"
    assert "error" not in rows[1]
    assert json.loads(json.dumps(rows)) == rows


def test_structured_output_ignores_model_repo(tmp_path, monkeypatch):
    repo = tmp_path / "real-repo"
    repo.mkdir()
    payload = {**_FIELDS, "repo": "not-this-repo"}
    monkeypatch.setattr(audit, "query", _yielding(_message(structured=payload)))

    rows = asyncio.run(audit.audit_many([repo], concurrency=1))

    assert rows[0]["repo"] == "real-repo"
    assert rows[0]["leakage"] == "none"


def test_json_fallback_ignores_model_repo(tmp_path, monkeypatch):
    repo = tmp_path / "real-repo"
    repo.mkdir()
    payload = {**_FIELDS, "repo": "not-this-repo"}
    message = _message(result=json.dumps(payload))
    monkeypatch.setattr(audit, "query", _yielding(message))

    rows = asyncio.run(audit.audit_many([repo], concurrency=1))

    assert rows[0]["repo"] == "real-repo"
    assert rows[0]["leakage"] == "none"
    assert "error" not in rows[0]


def test_dot_path_success_uses_resolved_directory_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {**_FIELDS, "repo": "not-this-repo"}
    monkeypatch.setattr(audit, "query", _yielding(_message(structured=payload)))

    rows = asyncio.run(audit.audit_many([Path(".")], concurrency=1))

    assert rows[0]["repo"] == tmp_path.name
    assert rows[0]["repo"] not in {"", "not-this-repo"}


def test_dot_path_error_uses_resolved_directory_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audit, "query", _raising())

    rows = asyncio.run(audit.audit_many([Path(".")], concurrency=1))

    assert rows[0]["repo"] == tmp_path.name
    assert rows[0]["repo"] != ""
    assert rows[0]["error"] == "exception"
