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

## sdk-audit follow-up review: repo label authority (`c059b5a`)

**Status: proposed verdict pending reviewer sign-off.** The first review and its CHANGES REQUESTED verdict above are kept as written. Not merged.

| Field | Value |
|---|---|
| Shared repository | https://github.com/YashTandon05/bikeshare-open |
| Author | Issac Roy |
| Reviewer | Yash Tandon (review run with a fresh `leakage-auditor` subagent invocation) |
| Branch | `sdk-audit` |
| Previously reviewed commit | `a38f682f8da986102c090feae748c03dbe854771` (CHANGES REQUESTED) |
| Reviewed commit | `c059b5ae8854596ce24c6e195b2eb5708467bd91` (matches the expected code commit) |
| Author's commit | "Make the audit repo label authoritative." (2026-11-24 15:01 -0800) |
| Date | 2026-11-24 |
| Files changed since `9df6f70` (review commit) | `agent/audit.py`, `tests/test_audit.py`, `docs/DECISIONS.md`, `docs/RUBRIC_CHECKLIST.md`, `docs/AUDIT.md` (appended "Author response" only) |

### Test evidence (reviewer-run on `c059b5a`, independent of the subagent)

Python 3.12.3. Every SDK test mocks `query`; no API, network, or CLI calls.

| Command | Result |
|---|---|
| `python -m pytest tests/test_audit.py -q` | `5 passed in 1.48s` (expected 5) |
| `make test` (`python -m pytest tests/ -q`) | `27 passed in 3.01s` (expected 27) |
| `git diff origin/master...c059b5a -- src data reports Makefile requirements.txt` | empty (0 lines) |
| Symlink-loop probe (B1 below): `audit_many([<self-loop symlink>, <ok dir>])` with a fake `query` that raises | `BATCH RAISED: RuntimeError Symlink loop from '/tmp/b1check.9Noe/loop'`; no rows returned (reproduced independently of the subagent) |

### Subagent output (verbatim)

The fresh `leakage-auditor` report, unedited. It is fenced with four backticks because it contains a three-backtick code block.

````text
## Follow-up review of `sdk-audit` at c059b5a (compared with a38f682)

**Verdict:** all four requested changes (R1 to R4) are done, and the tests that guard them are real. c059b5a introduces one new, narrow regression: an exception during label lookup can now abort the whole batch (B1). One test gap remains (B2). Modeling code, data and metrics are unchanged, and the five methodology checks pass.

I worked read-only. The main tree stayed clean at c059b5ae8854596ce24c6e195b2eb5708467bd91. The mutation worktree was created and removed. **The probe directory `/tmp/sdk-followup-probe` was NOT removed:** my `rm -rf` was part of a compound command that the permission system denied, and I did not retry. You need to delete it by hand. It holds `probe.py`, `mutate.sh`, `old.py` and `w/` (empty test dirs, a symlink `link-to-real`, and a self-loop symlink `loop`).

### Test runs (Python 3.12.3, `.venv`)
- `python -m pytest tests/test_audit.py -q` gave `5 passed in 1.04s`.
- `make test` (`python -m pytest tests/ -q`) gave `27 passed in 2.09s`. Both match the expected counts.

### (a) Requested changes that are resolved

**R1. The model cannot set the repo label.** `agent/audit.py:144-151`: `_with_repo` returns `{**payload, "repo": repo.resolve().name}`, so the directory name always wins. It is used on every return path: run_failed (line 185), structured output (187), JSON fallback (191), unparseable (195) and the exception record in `audit_many` (208).

I probed each path with a fake `query` whose payload or text contained `"repo":"EVIL"`. Every row came back with `repo: real-repo`. `EVIL` only appears inside `raw` for run_failed, which is just echoed text, not the label.

Mutation results, run in `/tmp/sdk-followup-mut` (I confirmed the import resolved to `/tmp/sdk-followup-mut/agent/audit.py`; the unmutated baseline gave 5 passed):

| Mutation | Result | Tests that went red |
|---|---|---|
| M1: label first, `{"repo": label, **payload}` | 3 failed | `test_structured_output_ignores_model_repo`, `test_json_fallback_ignores_model_repo`, `test_dot_path_success_uses_resolved_directory_name` |
| M2: `repo.name` instead of `repo.resolve().name` | 2 failed | `test_dot_path_success_...`, `test_dot_path_error_...` |
| M3: revert only the structured path to `{"repo": repo.name, **so}` | 2 failed | `test_structured_output_ignores_model_repo`, `test_dot_path_success_...` |
| M4: revert only the fallback path | 1 failed | `test_json_fallback_ignores_model_repo` |
| M5: structured path uses `repo.name` with the label last | 1 failed | `test_dot_path_success_...` |
| M6: whole `audit.py` reverted to a38f682 | 4 failed | everything except `test_sdk_exception_keeps_the_other_repo` |
| M7: `except Exception` changed to `except BaseException` | 5 passed | none; see B2 |
| M8: exception record uses `repo.name` | 1 failed | `test_dot_path_error_...` |
| M9: run_failed and unparseable paths use `repo.name` | 5 passed | none; see B2 |

So both parse paths have regression tests that fail if the fix is reverted.

**R2. Docs limit isolation to `Exception`.** The new line in `docs/DECISIONS.md` (line 30) names `CancelledError`, `BaseExceptionGroup`, `KeyboardInterrupt` and `SystemExit` as still propagating. The checklist row 6 now says "isolates `Exception` only... cancellation still propagates". The code comment at `audit.py:206` agrees.

I checked propagation with a 4-repo fake batch where repo r2 raises:
- `CancelledError` propagated as `CancelledError`.
- `BaseExceptionGroup([CancelledError])` propagated as `BaseExceptionGroup`.
- `KeyboardInterrupt` propagated as `KeyboardInterrupt`.
- `SystemExit(3)` propagated as `SystemExit`.

**R3. Interruption durability is documented, not fixed.** DECISIONS.md says: "Rows are still written only after the whole batch finishes, so an interrupt loses completed audits; recorded, not fixed." `main()` (lines 222-225) still writes only after `gather` returns, so the doc matches the code.

**R4. Python version.** The author now states 3.12.1 (`tags/v3.12.1:2305ca5`). I can't verify it: this machine has 3.12.3.

**Reviewer verdict in `docs/AUDIT.md` is unaltered.** I byte-compared the file at 9df6f70 with the same-length prefix at c059b5a: identical. The only change is a trailing newline plus an appended "### Author response" section. Note that AUDIT.md does not exist at a38f682; it was added by the reviewer's commit 9df6f70. So `git diff a38f682 c059b5a` also includes the reviewer's own RUBRIC_CHECKLIST edits. I reviewed the author's edits as `git diff 9df6f70 c059b5a`.

**Isolation of ordinary exceptions still works.** With repos r1 (succeeds after a delay), r2 (`ValueError`), r3 (`ExceptionGroup` of `OSError`) and r4 (succeeds), I got `[('r1', None), ('r2','exception','ValueError: bad'), ('r3','exception','ExceptionGroup: eg (1 sub-exception)'), ('r4', None)]`. Every repo was kept, in input order.

### (b) Issues introduced by c059b5a

**B1 (new, low severity). Label lookup can now raise inside the exception handler and abort the batch.** At `agent/audit.py:146`, `repo.resolve()` can raise; a38f682's `repo.name` never could. Line 208 calls it inside `except Exception`, so an error there escapes `bounded` and `gather` fails.
- Scenario: one argument is a symlink loop (`w/loop -> w/loop`), next to a healthy repo, and `query` raises.
- At c059b5a the whole batch raises `RuntimeError Symlink loop from '/tmp/sdk-followup-probe/w/loop'`, and no rows are written.
- At a38f682 (same probe, run in the worktree) both rows survive: `[{'repo': 'loop', 'error': 'exception', ...}, {'repo': 'real-repo', 'error': 'exception', ...}]`.
- The same raise also hits the success and error return paths (lines 185-195). Other filesystem errors from `resolve()` would behave the same way.
- Minimal fix:
  ```python
  def _repo_label(repo):
      try:
          return repo.resolve().name or str(repo)
      except (OSError, RuntimeError):
          return repo.name or str(repo)
  ```
  Or compute the label once in `bounded` before the `try`, with that fallback. Add one test using a self-loop symlink plus a healthy repo.

**B2 (test gap, not a wrong result today).**
- No test checks the run_failed or unparseable records for `Path(".")` (M9 stayed green).
- No test checks that cancellation or interruption propagate (M7 stayed green). `grep -nE 'Cancel|KeyboardInterrupt|SystemExit|BaseException' tests/*.py` finds nothing.

So R2 holds in the code but nothing enforces it: someone widening the catch to `BaseException` would pass CI.
- Fix: add a parametrized test where `query` raises `asyncio.CancelledError` / `KeyboardInterrupt` and `pytest.raises` expects it out of `audit_many`.
- Fix: add a `Path(".")` case with `is_error=True` and one with non-JSON text.

**B3 (behaviour change, worth noting in the docs).** Because of `resolve()`, a symlinked argument is now labelled with its target's name, not the link's. `w/link-to-real` was labelled `real-repo` (at a38f682 it would have been `link-to-real`). Trailing slashes are harmless: `Path("x/")` drops them, and `./` gave `real-repo`.

### (c) Limitations that predate this change (same behaviour at a38f682)

1. **A JSON fallback that parses to a non-dict is misclassified.** At `audit.py:191`, `{**payload, ...}` raises `TypeError` on a list, str, int, `null` or bool. I probed `[1,2]`, `"EVIL"`, `42`, `null`, `true` and `[["repo","EVIL"]]`.
   - Through `audit_many` the row becomes `{'error': 'exception', 'raw': "TypeError: 'list' object is not a mapping", 'repo': 'real-repo'}`. It is labelled `exception` instead of `unparseable`, and the model's text is lost from `raw`.
   - `audit_repo` called directly raises.
   - A list `structured_output` behaves the same way.
   - a38f682 gave the identical row, so this is not new. The label is still not controlled by the model.
   - Fix: `if not isinstance(parsed, dict): return _with_repo(repo, {"error": "unparseable", "raw": raw})`.
2. **Repos with the same folder name get the same label.** `a/repo` and `b/repo` both come out as `['repo', 'repo']`, so rows can't be told apart; the same happened with `repo.name`. Fix: also store `str(repo.resolve())` in a separate field, such as `path`.
3. **`Path("/")` gets an empty label** (`""`), both before and after this change. `Path("..")` gives the parent's name (`w`), which is fine. A path that doesn't exist gives its own last component.
4. **Interrupted runs lose finished work** (R3, documented): rows are written only after the whole batch ends. Separately, after a `KeyboardInterrupt` or `SystemExit`, asyncio prints "Task exception was never retrieved". That is only noise.

### Methodology checks and modeling isolation
- `git diff --stat origin/master...c059b5a -- src data reports Makefile requirements.txt` printed nothing (origin/master = 8450800). `git diff --stat a38f682 c059b5a` on the same paths was also empty.
- The docs edits change no recorded numbers. The new DECISIONS line contains no metrics. In RUBRIC_CHECKLIST only status text changed in the header, row 6, the AUDIT.md row and the Ex 3 line; the Ex 4 numbers (0.5642/885.8, 0.0977/1381.6, 0.4507/900.6, 0.7224/700.4) are untouched.
- All five standard checks (target leakage, temporal ordering, calendar gaps, silent row loss, unreported baseline) pass, because nothing modeling-related changed.

### Not verified
- The author's Python 3.12.1 claim (this machine has 3.12.3).
- Real SDK or CLI behaviour: everything was run with a fake `query`, and no API, network or CLI calls were made. I did not check whether the real SDK can return a non-dict `structured_output`, or what happens when `cwd` is a symlink loop.
- Behaviour on Python 3.13+, where `resolve()` raises a different error for symlink loops.

### Commands run
- `git diff a38f682 c059b5a`, `git diff 9df6f70 c059b5a -- docs/AUDIT.md`, and `cmp` of the 9df6f70 AUDIT.md against the c059b5a prefix.
- `git worktree add /tmp/sdk-followup-mut c059b5a`, then sed mutations M1 to M9 with `python -m pytest tests/test_audit.py -q -p no:cacheprovider` in that worktree, then `git worktree remove --force /tmp/sdk-followup-mut` (WT_REMOVED; `git worktree list` now shows only the main tree).
- Probes run as `python -I /tmp/sdk-followup-probe/probe.py <repo>` from `/tmp`.

### Relevant paths
- `/home/ytandon/dsc180-methodology/bikeshare-open/agent/audit.py` (lines 144-151, 183-195, 203-210)
- `/home/ytandon/dsc180-methodology/bikeshare-open/tests/test_audit.py`
- `/home/ytandon/dsc180-methodology/bikeshare-open/docs/DECISIONS.md` (line 30)
- `/home/ytandon/dsc180-methodology/bikeshare-open/docs/AUDIT.md`
- `/home/ytandon/dsc180-methodology/bikeshare-open/docs/RUBRIC_CHECKLIST.md`
- `/tmp/sdk-followup-probe` (left over, needs manual removal)
````

### Proposed reviewer verdict: CHANGES REQUESTED (one narrow item)

*Proposed for Yash Tandon's sign-off, on `c059b5a`; not final until confirmed.* All four changes requested on `a38f682` are resolved. **Repository identity is resolved:** `_with_repo` writes the resolved directory name after the model payload on every return path (structured output, JSON fallback, `run_failed`, `unparseable`, and the exception record). Dedicated tests cover both the structured-output and JSON-fallback paths, and they go red when the fix is reverted (subagent mutations M1, M3, M4, M6). `Path(".")` gets the working-directory name on success and on the exception path, and both are tested (M2, M8). **Exception scope is resolved:** ordinary exceptions are still isolated, with every repo kept in input order. `CancelledError`, `BaseExceptionGroup[CancelledError]`, `KeyboardInterrupt`, and `SystemExit` still propagate, and `docs/DECISIONS.md` and the tracker now state that scope explicitly. **Interruption durability** is recorded as a limitation, as requested. **Python version:** the author confirms 3.12.1 (`tags/v3.12.1:2305ca5`). This review machine's 3.12.3 cannot contradict that, so the author's statement is accepted. Modeling code, raw data, and official metrics are unchanged; `tests/test_audit.py` gives 5 passed and `make test` gives 27 passed, with no API calls. However, the fix introduces one regression (B1, reproduced independently by the reviewer). `repo.resolve()` can raise, for example on a symlink loop, and it is now called inside the `except Exception` handler. One bad path then aborts the whole batch with no rows, which `a38f682` handled. This is the very guarantee this branch exists to provide, so approval requires `_repo_label` to fall back to `repo.name` (or `str(repo)`) when `resolve()` raises, plus a regression test pairing a symlink loop with a healthy repo. Strongly recommended but not blocking: a test that asserts cancellation and `KeyboardInterrupt` propagate from `audit_many` (B2; widening to `BaseException` currently passes CI), and a `Path(".")` test for the `run_failed` and `unparseable` records. Noted and not blocking: symlinked arguments are now labelled with their target's name (B3, worth one line in the docs). The non-dict JSON fallback, duplicate folder names, and the empty label for `/` predate this branch. The branch stays unmerged.

### Final reviewer verdict: APPROVED WITH DOCUMENTED LIMITATIONS

Yash Tandon, 2026-11-24, on `c059b5ae8854596ce24c6e195b2eb5708467bd91`. This replaces the proposed verdict above, which stays as a record. Approval covers the assignment's use only: `agent/audit.py` run on valid, resolvable repository directories, as in the planned `env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl`. The changes requested on `a38f682` are resolved. The resolved directory name now overrides any model-supplied `"repo"` on the structured-output and JSON-fallback paths, `Path(".")` gets a non-empty label, and ordinary `Exception`s are still isolated, with the other repos kept in input order. `tests/test_audit.py` gave 5 passed and `make test` gave 27 passed on `c059b5a`, with a mocked `query` and no API calls. Cancellation and process interruption (`CancelledError`, `BaseExceptionGroup[CancelledError]`, `KeyboardInterrupt`, `SystemExit`) still propagate, as intended; no test enforces this yet. The symlink-loop failure (B1) is real and **not fixed**: if `repo.resolve()` raises, the whole batch aborts with no rows. It is accepted as an invalid-input limitation, because our planned invocation never passes an unresolvable path. Interrupted runs still lose completed rows, because results are written only after the batch finishes; this stays a documented limitation. Not every finding was fixed, and not every input is supported. Still open and deferred as optional SDK hardening: B2 (no tests for propagation or the `Path(".")` error records), B3 (a symlinked argument is labelled with its target's name), the non-dict JSON fallback, duplicate folder names, and the empty label for `/`. The author's Python 3.12.1 is accepted on the author's statement; this machine has 3.12.3. Cleared to merge into `master`.
