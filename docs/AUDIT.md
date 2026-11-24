# Audits

## sdk-audit: SDK exception isolation in `agent/audit.py`

**Status: CHANGES REQUESTED** (first peer review; not merged)

| Field | Value |
|---|---|
| Shared repository | https://github.com/YashTandon05/bikeshare-open |
| Author | Issac Roy |
| Reviewer | Yash Tandon (review run with the `leakage-auditor` subagent) |
| Branch | `sdk-audit` |
| Base | `origin/master` @ `8450800aa9f046738d88f4b21d202517550a8d15` (also the merge-base) |
| Reviewed commit | `a38f682f8da986102c090feae748c03dbe854771` (matches expected head `a38f682`) |
| Date | 2026-11-24 |
| Files changed | `agent/audit.py`, `tests/test_audit.py` (new), `docs/DECISIONS.md`, `docs/RUBRIC_CHECKLIST.md` |

### Test evidence (reviewer-run on `a38f682`, independent of the subagent)

Python 3.12.3, pytest 9.1.1, claude-agent-sdk 0.2.172.

| Command | Result |
|---|---|
| `git diff --stat origin/master...a38f682 -- src data reports Makefile requirements.txt` | empty (no modeling, raw-data, or metrics change) |
| `python -m pytest tests/test_audit.py -q` | `1 passed in 1.42s` |
| `python -m pytest -q` | `23 passed in 2.44s` |
| `make test` | `23 passed in 2.11s` |

The docs diff changes status text only; no recorded metric value changed. I checked the subagent's cited lines against the code: `agent/audit.py:194` catches only `Exception`, and `agent/audit.py:177` and `:181` place `repo.name` before the `**` unpack. Mutation and edge-case results below are the subagent's, run in a temporary worktree that it removed.

### Subagent output (verbatim)

The `leakage-auditor` report, unedited. It is fenced so its headings stay inside the record.

````text
## Review of `sdk-audit` @ a38f682 vs origin/master 8450800 (author: Issac Roy)

**Summary:** This diff doesn't touch the modeling code, the data or the metrics, so the five methodology checks (leakage, temporal ordering, calendar gaps, silent row loss, baselines) all pass trivially. Claims A, B and C hold for ordinary `Exception`s. The one real gap is in A: a `BaseException` from any one repo still loses every repo's result.

### Commands run and results
- `git diff --stat origin/master...a38f682` → 4 files: agent/audit.py (+22/-8), docs/DECISIONS.md (+1), docs/RUBRIC_CHECKLIST.md (4 lines changed), tests/test_audit.py (+48 new). 75 insertions, 12 deletions.
- `git diff --stat origin/master...a38f682 -- src data reports Makefile requirements.txt` → **empty**.
- `python -m pytest tests/test_audit.py -q` → **1 passed**. Full `python -m pytest -q` → **23 passed**. Versions here: Python 3.12.3, pytest 9.1.1, claude-agent-sdk 0.2.172.
- `git show origin/master:agent/audit.py | grep -c "def audit_many"` → **0**.
- **Mutation 1:** in `git worktree add /tmp/sdk-audit-mut a38f682`, I removed the try/except in `bounded` so it just did `return await audit_repo(repo)`. Result: `FAILED tests/test_audit.py::test_sdk_exception_keeps_the_other_repo - RuntimeError`, **1 failed**. I confirmed the import resolved to `/tmp/sdk-audit-mut/agent/audit.py`.
- **Mutation 2:** I put master's `agent/audit.py` into the same worktree. Result: `AttributeError: module 'agent.audit' has no attribute 'audit_many'`, **1 failed**.
- I removed the worktree with `git -C ... worktree remove --force /tmp/sdk-audit-mut`. `worktree list` now shows only the main tree, and `git status --short` is empty, so the main tree was never modified. The probe script at `/tmp/sdk-probe/probe.py` is still there: my `rm -rf` was denied by permissions.
- **Edge-case probe** (`python -I /tmp/sdk-probe/probe.py <repo>`). It blocks `socket.connect` and `subprocess.Popen`, imports `agent.audit`, then runs `audit_many` on 3 repos (`bad`, `ok1`, `ok2`) with a fake `query`:
  - import → OK, with no socket or subprocess use
  - `mid` (yields a message, then raises `RuntimeError`) → `[('bad','exception'),('ok1',None),('ok2',None)]`
  - `egroup` (`ExceptionGroup`) → caught, all 3 rows kept
  - `slow_ok` (bad repo finishes last, concurrency 3) → order still `bad, ok1, ok2`
  - `cancel` (`asyncio.CancelledError`) → **raised; all rows lost**
  - `bgroup` (`BaseExceptionGroup[CancelledError]`) → **raised; all rows lost**
  - `kbint` (`KeyboardInterrupt`) → **raised; all rows lost**

### Methodology checks 1-5
Nothing in src/, data/ or reports/ changed, so all five pass. Neither docs file changes any recorded metric. The only new numbers are tool versions, and the Ex 4 metrics line is untouched.

### Claim verdicts
- **A: holds for `Exception`, not for `BaseException`.** An error raised partway through `async for ... in query(...)` is caught, because it happens inside `audit_repo`, which runs inside the try. `gather` keeps the input order. `main` writes every row after `audit_many` returns.
  - The error-count line is correct: `"error" in r` counts the new `exception` rows plus the existing `run_failed` and `unparseable` rows. The format string labels this "errors", which is accurate.
  - One caveat: `REPORT_SCHEMA` does not set `additionalProperties: false`, so a model could in principle add an `"error"` key and get counted. This is minor and I did not observe it.
- **B: holds.** `agent/audit.py:34` does `from claude_agent_sdk import query`, and `audit_repo` (line 169) looks up the module-global `query` when it is called. So `monkeypatch.setattr(audit, "query", ...)` is the binding that actually gets used. The fake's signature matches the SDK's `query(*, prompt, options, transport)`.
  - Importing the module does no network or subprocess work: it only builds an in-process MCP server.
  - The test fails on master, but there that only proves `audit_many` doesn't exist. Mutation 1 is the real evidence: it shows the test does exercise the isolation logic.
  - Gap: the test does not cover `main()` (file writing or the count line), and it does not cover a raise after messages have already been yielded. My probe covered the second case.
- **C: holds.** Modeling code, raw data and metrics are unchanged. I could not verify the DECISIONS.md claim "Ran with Python 3.12.1": this machine has 3.12.3. The pytest and SDK versions match.

### (1) Issues newly introduced by this diff
1. **docs/DECISIONS.md:29 and docs/RUBRIC_CHECKLIST.md (row 6 and the audit.jsonl row) overstate how far the isolation goes.** At `agent/audit.py:194`, `except Exception` does not catch `asyncio.CancelledError` or `BaseExceptionGroup` containing one; both are `BaseException`s. The SDK runs on anyio task groups, and if something inside it cancels one repo's run, the error comes out of `gather` (line 200). Then `audit_many` raises, `main` never reaches `ns.out.open`, and every other repo's result is lost. I reproduced this above (`cancel` and `bgroup` → all rows lost).
   - **Minimal fix:** at line 200, call `asyncio.gather(..., return_exceptions=True)` and turn any `BaseException` result into `{"repo": r.name, "error": "exception", "raw": ...}`. Re-raise only `KeyboardInterrupt`/`SystemExit`. Alternatively, keep the code and narrow the doc wording to "any `Exception` subclass".
   - This does not change any modeling number. It does make the stated conclusion ("One raised SDK run no longer aborts the batch") untrue for that class of failure.

### (2) Pre-existing limitations (not caused by this diff)
1. **agent/audit.py:177:** `{"repo": repo.name, **final.structured_output}`. `REPORT_SCHEMA` makes `"repo"` a required field, so the model's own `"repo"` string overrides the directory name. Scenario: across a 40-repo batch, a model that writes "bikeshare" or a URL produces rows that can't be joined back to their directories. The test passes only because `_ok_result()` leaves out `repo`.
   - **Fix:** `{**final.structured_output, "repo": repo.name}`. The same applies at line 181.
2. **agent/audit.py:210-213:** results are written only after all repos finish. A `KeyboardInterrupt`, or the issue (1) case, loses every completed audit.
   - **Fix:** write each row as its task completes (e.g. with `asyncio.as_completed` plus the repo name), or write in a `finally` block.
3. **agent/audit.py:181:** if the fallback `json.loads` returns a non-dict, such as a list, `**` raises `TypeError`. Before this change that killed the whole batch. Now `audit_many` turns it into an `"exception"` row, so it is mitigated rather than introduced.

### Relevant paths
- /home/ytandon/dsc180-methodology/bikeshare-open/agent/audit.py (lines 169, 177, 187-200, 210-220)
- /home/ytandon/dsc180-methodology/bikeshare-open/tests/test_audit.py
- /home/ytandon/dsc180-methodology/bikeshare-open/docs/DECISIONS.md (line 29)
- /home/ytandon/dsc180-methodology/bikeshare-open/docs/RUBRIC_CHECKLIST.md
- /tmp/sdk-probe/probe.py (left over; deletion was denied)
````

### Reviewer verdict: CHANGES REQUESTED

Yash Tandon, 2026-11-24, on `a38f682`. The branch shows that one ordinary SDK exception is isolated. When `audit_repo` raises an `Exception`, including partway through iteration, that repo gets an `{"repo", "error": "exception", "raw"}` row and the other repos are kept in input order. The mocked test runs without API calls and goes red when the try/except is removed. Modeling code, raw data, and official metrics are unchanged. Cancellation (`asyncio.CancelledError`, including inside a `BaseExceptionGroup`) and process interruption (`KeyboardInterrupt`, `SystemExit`) are outside that guarantee. They should keep propagating normally and should not be caught. The code is acceptable on that point, but `docs/DECISIONS.md` and `docs/RUBRIC_CHECKLIST.md` must say explicitly that isolation covers `Exception` subclasses only, not "one raised SDK run" in general. Before approval, the model must stop controlling a result's repository identity: `repo.name` has to override any model-supplied `"repo"` at `agent/audit.py:177` and `:181`. Add regression tests showing that a model-supplied `"repo"` is replaced by the directory name on both the structured-output path and the JSON-fallback path. Interruption durability is a pre-existing limitation: rows are written only after the whole batch finishes, so an interrupt loses completed audits. Record that as a documented limitation; it does not block this change. This review machine has Python 3.12.3, which neither confirms nor disproves the recorded 3.12.1, so the author should confirm the version actually used. Requested changes are pending, and the branch stays unmerged.

### Author response

The reviewer's verdict above is unchanged. The follow-up keeps `except Exception`, so cancellation and process interruption still stop the batch. `repo` is now the resolved directory name, applied after the model payload, on both parse paths. `Path(".")` uses that name in success and error records. The original test run was Python 3.12.1 (`tags/v3.12.1:2305ca5`). Awaiting re-review. The branch stays unmerged.