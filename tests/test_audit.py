"""A failed SDK run must not drop the other repos in the batch."""
import asyncio
import json

import agent.audit as audit
from agent.audit import ResultMessage


def _ok_result() -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id="test",
        structured_output={
            "leakage": "none",
            "temporal_ok": True,
            "baseline_reported": True,
            "reproducible": True,
            "findings": [],
            "confidence": "high",
        },
    )


async def _fake_query(*, prompt, options=None, transport=None):
    if "broken-repo" in prompt:
        raise RuntimeError("sdk connection reset")
    yield _ok_result()


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
