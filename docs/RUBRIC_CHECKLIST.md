# Rubric checklist

Progress tracker for the [Methodology 07 (open) assignment](https://dsc-capstone.org/2026-27/assignments/methodology/07-open/).
Update after every checkpoint (see `CLAUDE.md`). Last updated: 2026-11-24, `final-evaluation-report` merged into `master` (`edd74cf`); fresh-clone reproduction passed (`docs/FINAL_CHECKS.md`).

Each criterion has two boxes:

- **Impl**: the work exists in the repo. Cite the file, commit, or output.
- **Verified**: checked under grading conditions on the final code (fresh
  clone, `make all`, `make test`, compared with `REPORT.md`). Anything that
  can still change before submission stays unticked here.

| # | Category | Points | Status |
|---|---|---|---|
| 1 | Reproducible repository | 15 | Partly done |
| 2 | `CLAUDE.md` | 10 | Partly done |
| 3 | Verification suite | 25 | Feature, contract, weather-guard, checksum and hardened rolling-mean tests; all 4 faults recorded (fault 4 left the pre-defense suite green) |
| 4 | Results with baselines | 20 | Final evaluation run once (`9315d78`); `REPORT.md` final: all 8 rows, headline, Exercises 4-5. Reciprocal review found no issue that changes a number (`docs/AUDIT.md`, `1cc391c`) |
| 5 | Structural enforcement | 10 | Hook fired automatically on faults 1-3; did not fire on fault 4 (Bash), as the `Edit\|Write` matcher predicts. Fault-4 catch (checksum in `load_raw()`) implemented and shown in an isolated copy |
| 6 | Agent configuration | 10 | `/seed-fault` written, all three arguments run. SDK audit of our repo run and committed (`reports/audit.jsonl`). `agent/audit.py` isolates `Exception` only; cancellation still propagates (`tests/test_audit.py`, 5 tests). Peer review of Issac Roy's `sdk-audit` closed in `docs/AUDIT.md` (CHANGES REQUESTED on `a38f682`, APPROVED WITH DOCUMENTED LIMITATIONS on `c059b5a`) and merged into `master` (`cf5cb31`). Reciprocal review of Yash's `final-evaluation-report` recorded (`docs/AUDIT.md`, `1cc391c`, no changes requested) |
| 7 | Decisions and attribution | 10 | Decision log current; `REPORT.md` Attribution final: both contributors, both peer reviews, and their tools/models (Opus 5.5 via Claude Code/SDK; Grok 4.7 via OpenCode and a Grok 4.7 subagent; ChatGPT). Commit/decision cross-check pending |

## 1. Reproducible repository (15)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [x] | `make all` runs data, features, then train | `Makefile` target `all: data features train`. **Verified:** exit 0, ingest -> features -> train (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | `reports/metrics.json` comes from `make all` on the **final** code | `make all` at `9315d78` (final evaluation) reproduced the committed file byte for byte, sha256 `4df4eb95...` (`docs/DECISIONS.md`, final evaluation run). Verified waits for the fresh-clone run. **Verified:** regenerated file byte-identical, sha256 `4df4eb95...` (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | Seeds fixed | `src/train.py:65` `HistGradientBoostingRegressor(random_state=0, max_iter=300)`; ridge is deterministic. **Verified:** byte-identical rerun (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | Dependencies pinned, including any added ones | `requirements.txt` (nothing added so far). **Verified:** all six pinned with `==`; fresh `pip install -r requirements.txt` exit 0 (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | `.gitignore` no longer ignores `reports/` but still ignores `data/processed/`, `.venv/`, caches | `.gitignore`, changed in `d85aa8a`. **Verified:** `git check-ignore -v` (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | `data/processed/`, `.venv/`, `__pycache__/`, `.pytest_cache/` not committed | `git ls-files` shows none at `935ecdf`. **Verified:** none tracked after `make all` (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | `data/raw/bike_daily.csv` unchanged (sha256 starts `a6bed1577f6e4de5`) | Full hash `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc` confirmed after the fault-4 restore (`b080d81`), and again before and after the isolated checksum demonstration (`docs/SEEDED_FAULTS.md` "Fault 4 defense" > "Canonical file"). `load_raw()` now enforces it as `RAW_SHA256`. Verified waits for a fresh-clone check at submission. **Verified:** sha256 `a6bed157...` = `RAW_SHA256`, also under `core.autocrlf=true` (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [x] | Fresh clone, `pip install -r requirements.txt`, `make all`, then diff with committed metrics and the `REPORT.md` table | Done. The SDK auditor's pipeline rerun reproduced `metrics.json` byte for byte, but in the working copy, not a fresh clone. **Verified:** 27 passed; `metrics.json` byte-identical; 8/8 report rows match (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |

## 2. `CLAUDE.md` (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Forbidden columns | `CLAUDE.md` "Non-negotiable rules" |
| [x] | [ ] | Split rule | `CLAUDE.md` "Never split this data randomly" |
| [x] | [ ] | Both baselines (mean and persistence) | `CLAUDE.md` "Report the mean baseline **and** the persistence baseline" |
| [x] | [x] | The command that reproduces the headline number, named as such | `CLAUDE.md` Commands: "`make all` ... reproduces the headline metrics in `reports/metrics.json`". **Verified:** `make all` reproduced `metrics.json` byte for byte (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [ ] | [ ] | Rule for our feature, if needed | Not decided |
| [x] | [ ] | Name of our custom skill | `CLAUDE.md` Commands: `/seed-fault <forbidden-column\|rolling-leakage\|weather-guard>` |
| [x] | [x] | Under 60 lines | 48 lines at this checkpoint (added the checksum-mismatch gotcha). **Verified:** 48 lines (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [ ] | [ ] | Every line changes agent behavior (the grader deletes lines one at a time) | Not reviewed |
| [x] | n/a | Changes recorded in `DECISIONS.md` | Tracker line, see `docs/DECISIONS.md` |

## 3. Verification suite (25)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Starter tests kept: leakage tied to `FORBIDDEN`, temporal split, row-loss bound | `tests/test_leakage.py::test_no_forbidden_features`, `tests/test_split.py`, `tests/test_contract.py::test_only_expected_rows_are_dropped` |
| [x] | [x] | Feature test written **before** the feature, with the failing run recorded | `tests/test_leakage.py::test_rolling_std_excludes_today`; failing commit `e21af14` comes before the implementation in `b03f86b`; output in `docs/SEEDED_FAULTS.md` "Feature test before implementation" (`1 failed, 14 passed`) |
| [x] | [ ] | Feature test checks a value on a named date against a hand-computed value from strictly earlier dates | 2011-02-01, expected 499.70 from the counts for Jan 25-31 |
| [x] | [ ] | Unclassified-column test in `tests/test_contract.py` | `test_raw_columns_are_all_classified`, with the hand-typed `CLASSIFIED_RAW_COLS` in `src/config.py` (`935ecdf`) |
| [x] | [ ] | Unknown-column rejection shown | `docs/SEEDED_FAULTS.md` "Unclassified raw column rejected": `AssertionError: unclassified raw columns: ['surge_index']` |
| [x] | [x] | `make test` passes | `22 passed in 1.71s` at the Exercise 4 checkpoint (adds `test_change_reconstruction_never_sees_todays_target`); `21 passed` at the checksum-defense checkpoint. **Verified:** `27 passed` (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [ ] | Raw-data checksum tests (temporary files; canonical CSV untouched) | `tests/test_contract.py::test_load_raw_accepts_trusted_bytes` PASSED, `::test_load_raw_rejects_fault4_alteration` PASSED (`docs/SEEDED_FAULTS.md` "Fault 4 defense" > "Unit tests") |
| [x] | [ ] | `test_rolling_mean_excludes_today` cannot pass vacuously | The conditional skip is now an assertion that the reference window is complete (`tests/test_leakage.py`). PASSED in the same run. Post-hardening recheck done: `docs/SEEDED_FAULTS.md` "Fault: rolling-leakage (post-hardening recheck)". The window assertion passed, then the comparison failed (`4389.0` vs `4414.857142857143`), giving `1 failed, 20 passed`, `exit=2`. Automatic hook feedback appeared; manual diagnostic `exit=2`; 2 repair tool calls / 1 cycle. The original `6f69ea5` record is unchanged |
| [x] | [ ] | Fault 1 (forbidden column in `feature_columns`): real red output pasted | `4f3703c`, `docs/SEEDED_FAULTS.md` "Fault: forbidden-column" > "Red test output": `FAILED tests/test_leakage.py::test_no_forbidden_features`, `1 failed, 18 passed`, `exit=2` |
| [x] | [ ] | Fault 2 (`.shift(1)` removed from `cnt_roll_7`): real red output pasted | `docs/SEEDED_FAULTS.md` "Fault: rolling-leakage" > "Red test output": `FAILED tests/test_leakage.py::test_rolling_mean_excludes_today`, `1 failed, 18 passed`, `exit=2`. Rechecked against the hardened test in "Fault: rolling-leakage (post-hardening recheck)": still red |
| [x] | [ ] | Fault 3 (`raise` removed from the weather encoder): real red output pasted | `docs/SEEDED_FAULTS.md` "Fault: weather-guard" > "Red test output": `FAILED tests/test_leakage.py::test_unknown_weather_label_is_rejected` (`DID NOT RAISE ValueError`), `1 failed, 18 passed`, `exit=2`. Only that test, added in `6fb1c66`, catches this fault |
| [x] | [ ] | Fault 4 (`cp` into `data/raw/` from Bash): what happened, recorded | `docs/SEEDED_FAULTS.md` "Fault 4: Bash raw-data copy": `cp exit=0` (not denied), hash `a6bed157...` -> `cae60e1c...`, 1-byte diff, **`make test` stayed green** (`19 passed`, `exit=0`), no automatic hook feedback, restored and re-verified |
| [ ] | [ ] | Pasted output matches what the final tests print | Check after all faults |

## 4. Results with baselines (20)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Metrics from before the feature kept | `reports/metrics_before_feature.json` (`d85aa8a`, never changed) |
| [x] | [ ] | Feature's validation effect measured without using test scores | Ridge R² 0.6475 to 0.7224, hgb 0.2185 to 0.0977 (`b03f86b`, `docs/DECISIONS.md`) |
| [x] | [ ] | Validation delta explained, including the negative one | `docs/DECISIONS.md` keep entry (`935ecdf`); hgb's drop reported, cause not yet found |
| [x] | [x] | `REPORT.md` **Results**: one 8-row table (4 models × before/after) with validation and test R² and MAE, matching `reports/metrics.json` exactly | Filled from `reports/metrics_before_feature.json` and `reports/metrics.json` by script. Re-check against the fresh-clone metrics. **Verified:** 8/8 rows equal the JSON values (fresh clone of `edd74cf`, `docs/FINAL_CHECKS.md`) |
| [x] | [ ] | `REPORT.md` **Headline finding**: one paragraph with numbers, plus one sentence on the feature and the keep decision | Drafted: both baselines, ridge, hgb, `cnt_std_7` effect and keep decision, observed-weather qualification. Final |
| [x] | [ ] | No sign the test set was used while iterating (`DECISIONS.md`, commits) | Evaluation-history and final-evaluation lines in `docs/DECISIONS.md`. The final look was planned before running, its code committed first (`9315d78`), and run once; no selection followed |

## 5. Structural enforcement (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Starter hook and permissions still work | `.claude/settings.json` unchanged except `model`; the hook fired on a `src/features.py` edit while building `935ecdf` (a `NameError` from an edit made in two steps) |
| [x] | [ ] | Hook stderr pasted for faults 1-3 | 3 of 3. Automatic PostToolUse feedback appeared after each seeding `Edit` and was recorded verbatim under "Automatic hook feedback (PostToolUse)" in `docs/SEEDED_FAULTS.md`: "Fault: forbidden-column" (`4f3703c`), "Fault: rolling-leakage" (`6f69ea5`), "Fault: weather-guard". Each also has a separately labelled manual diagnostic with measured `exit=2` |
| [x] | [ ] | Fault 4: paragraph naming what would catch it (`Stop` hook, `PreToolUse` on Bash, filesystem permission, or a hash check in `make data`) | `docs/SEEDED_FAULTS.md` "Fault 4" > "What would catch it": a sha256 check in `load_raw()` against `RAW_SHA256` in `src/config.py`. It also explains why a `Stop` hook running `make test` alone would miss this fault |
| [x] | [ ] | Optional (up to 3 pts): implement the fault-4 catch | `RAW_SHA256` in `src/config.py` and a sha256 check in `src/ingest.py::load_raw()`. **Observed:** in an isolated `TemporaryDirectory` project copy, `make data` printed `OK ingest: 728 rows` (`exit=0`) with trusted bytes and `ValueError: raw data checksum mismatch ... expected sha256 a6bed157...dc, got cae60e1c...ac` (`exit=2`) with the one-byte change. **Not observed:** the same demonstration on the canonical file; its preparation command was denied (no reason given) and not retried. Detects corruption on load; does not prevent the `cp` |

## 6. Agent configuration (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Our own skill in `.claude/skills/<name>/SKILL.md`, for a workflow we repeated, taking `$ARGUMENTS` | `.claude/skills/seed-fault/SKILL.md` (uses `$ARGUMENTS`, `disable-model-invocation: true`). Created in `6fb1c66`, corrected in `040ee64`. **All three arguments run:** `forbidden-column` (`4f3703c`), `rolling-leakage` (`6f69ea5`), `weather-guard` (`a0d7ab1`). On weather-guard the `Edit` included one unchanged context line, but the net diff was exactly the required 2 deletions and 0 additions. **Real uses:** `/seed-fault rolling-leakage` and `/seed-fault weather-guard` ran on the current text and produced "Fault: rolling-leakage" (`6f69ea5`) and "Fault: weather-guard". Earlier, `/seed-fault forbidden-column` produced the "Fault: forbidden-column" record in `docs/SEEDED_FAULTS.md` (`4f3703c`). The table heading that `$ARGUMENTS` was substituting into was fixed afterwards (text only). Verified stays unticked for review: on weather-guard the agent added a context line to the `Edit` strings, so the table's literal strings for that row were not used as-is (net diff still matched; see that record). (`.claude/skills/run-pipeline/` is still an empty, untracked directory) |
| [x] | [ ] | Starter `new-feature` skill kept | `.claude/skills/new-feature/SKILL.md` |
| [x] | [ ] | `docs/AUDIT.md`: teammate's repo URL, verbatim `/leakage-auditor` output, one-paragraph verdict kept separate from the auditor's findings | `docs/AUDIT.md`: shared repo URL; Issac Roy's `sdk-audit` reviewed twice (`a38f682` CHANGES REQUESTED, `c059b5a` APPROVED WITH DOCUMENTED LIMITATIONS), each with fenced verbatim `leakage-auditor` output and a separate reviewer verdict. Accepted limitations: a symlink-loop or unresolvable path aborts the batch; interrupted runs lose rows. Merged into `master` in `cf5cb31`. Reciprocal review of Yash's `final-evaluation-report` @ `1cc391c` is in `docs/AUDIT.md` (no changes requested; not the Claude subagent, because credits were exhausted) |
| [x] | [ ] | `reports/audit.jsonl` from `python agent/audit.py . --out reports/audit.jsonl` | Committed exactly as generated (sha256 `7154daa1...`); the same bytes are preserved as `reports/audit_initial_8450800.jsonl`, which `REPORT.md` cites, so a later run may replace `reports/audit.jsonl`, from `env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl` on `8450800`, 2026-11-24 13:43:54 -0800 (`docs/DECISIONS.md`, SDK audit run). Has every schema field; `findings` has 2 entries |
| [x] | [ ] | If the auditor flags our repo: fix it, or argue back in `REPORT.md` | Leakage `none`. Both findings answered in the `REPORT.md` draft (Attribution > "SDK audit of our repo"): observed weather accepted as a substantive limit and stated; README test count fixed (cosmetic) |

## 7. Decisions and attribution (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | `DECISIONS.md` keeps the 5 starter lines; new lines dated, newest last | `git diff 0654988 -- docs/DECISIONS.md` only adds lines |
| [x] | [ ] | One line per decision so far: agent backend, model correction, feature, keep, column classification, tracker | `docs/DECISIONS.md` |
| [x] | [ ] | `REPORT.md` **Attribution**: first line names the model and size and whether we switched (Sonnet 5.5 planned, Opus 5.5 used, see `b033c19`) | Final. Names Opus 5.5 for Yash's Claude Code, SDK and peer-review work, ChatGPT for planning, Grok 4.7 via OpenCode for `a38f682`, and the Grok 4.7 subagent for Issac's reciprocal review. Issac Roy's credit confirmed against the merged `docs/DECISIONS.md` entry (`a38f682`: OpenCode with Grok 4.7; tool for `c059b5a` not documented); `sdk-audit` merged in `cf5cb31` |
| [x] | [ ] | Attribution list: files and functions the agent generated | `REPORT.md` Attribution |
| [x] | [ ] | Attribution list: our decisions, each traced to a `DECISIONS.md` line | `REPORT.md` Attribution; the target and believability lines are in `docs/DECISIONS.md` |
| [ ] | [ ] | Every decision has a commit and every commit has a decision | Check at the end |

## Remaining exercises

- [x] Ex 1: add one feature with `/new-feature`: `cnt_std_7`, kept (`e21af14`, `b03f86b`, `935ecdf`)
- [x] Ex 2: four seeded faults. Done: forbidden-column `4f3703c`, rolling-leakage `6f69ea5`, weather-guard `a0d7ab1` (each 2 repair tool calls / 1 repair cycle, which are lower bounds, not conversational turns); fault 4, the manual Bash raw-data copy, recorded with what would catch it
- [x] Ex 3: audit a teammate; run `agent/audit.py` on our repo. **Our-repo SDK audit done** (`601400b`, `reports/audit.jsonl`). **Teammate audit done:** `docs/AUDIT.md` (Issac Roy's `sdk-audit`, approved with documented limitations on `c059b5a`, merged in `cf5cb31`). Issac's reciprocal review of Yash's `final-evaluation-report` is recorded in `docs/AUDIT.md` (`1cc391c`, no changes requested)
- [x] Ex 4: target transformation. Validation (`reports/target_transform_validation.json`) and a single final test look (`reports/target_transform_final_test.json`, `--final-target-test` at `9315d78`): hgb_daily_change test R² 0.4761 / MAE 990.5, vs persistence 0.5099 / 840.1 and ridge 0.6356 / 840.3. Defensibility argued in `REPORT.md`. Committed `metrics.json` untransformed
- [x] Ex 5: ridge vs persistence argued as one paragraph with numbers in `REPORT.md` (position: not to deploy over persistence for now; test average absolute error 840.3 vs 840.1, about 25.6% lower squared error). Final
- [ ] Ex 6 (optional): second model size or hosted model, as a subsection under Attribution

## Required `REPORT.md` structure (2-4 pages)

Exactly these five `##` sections. Length estimated, not rendered (no PDF engine here): 1,909 words, about 3.6 pages.

- [x] **Results**: 8 rows, valid and test filled
- [x] **Headline finding**: final
- [x] **Exercise 4: target transformation**: validation and final test, defensibility
- [x] **Exercise 5: ridge vs persistence**: final
- [x] **Attribution**: model line, contributors and tools, agent-generated list, decisions list, SDK audit assessment

## Commit history (squashing all of it scores 0 on item 7)

| Done | Required commit, in order | Commit |
|---|---|---|
| [x] | 1. Unmodified starter, the first commit | `0654988` |
| [x] | 2. Failing test for the feature | `e21af14` |
| [x] | 3. Feature that makes the test pass | `b03f86b` (kept and refactored in `935ecdf`) |
| [x] | 4. Each seeded fault and its fix (or one commit per fault, with the fix in the message) | 4 of 4 distinct faults committed: forbidden-column `4f3703c`, rolling-leakage `6f69ea5`, weather-guard `a0d7ab1`, Bash raw-data copy `b080d81`. Later rechecks (the post-hardening `rolling-leakage` recheck is recorded under its own heading) do not change the count of 4 |
| [x] | 5. Audit run | SDK audit `601400b` (initial output kept as `reports/audit_initial_8450800.jsonl`); peer audit `9df6f70`, `050eaa0`; reciprocal review `4d004fd`. All on `master` (`cf5cb31`, `edd74cf`) |
| [x] | 6. Report | Draft `6dd265e`, final evaluation and complete draft `f572f37`, finalized in `60a7dd2` after the reciprocal review; merged into `master` in `edd74cf` |

Setup commits `d85aa8a` and `b033c19` come between 1 and 2; each has a `DECISIONS.md` line.

## Submission

- [ ] Repository URL submitted through the course form (`https://github.com/YashTandon05/bikeshare-open`)
- No deadline is given on the assignment page.
