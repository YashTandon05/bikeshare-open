# Rubric checklist

Progress tracker for the [Methodology 07 (open) assignment](https://dsc-capstone.org/2026-27/assignments/methodology/07-open/).
Update after every checkpoint (see `CLAUDE.md`). Last updated: 2026-11-24, branch `final-evaluation-report` (from `8450800`): SDK audit recorded, REPORT.md draft.

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
| 4 | Results with baselines | 20 | Modeling closed: ridge + `cnt_std_7` selected on validation; daily-change hgb kept as the Exercise 4 comparison. No report yet; final test interpretation pending |
| 5 | Structural enforcement | 10 | Hook fired automatically on faults 1-3; did not fire on fault 4 (Bash), as the `Edit\|Write` matcher predicts. Fault-4 catch (checksum in `load_raw()`) implemented and shown in an isolated copy |
| 6 | Agent configuration | 10 | `/seed-fault` written, all three arguments run. SDK audit of our repo run and committed (`reports/audit.jsonl`). Teammate `/leakage-auditor` audit (`docs/AUDIT.md`) pending |
| 7 | Decisions and attribution | 10 | Ongoing decision log; no Attribution section |

## 1. Reproducible repository (15)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | `make all` runs data, features, then train | `Makefile` target `all: data features train` |
| [ ] | [ ] | `reports/metrics.json` comes from `make all` on the **final** code | At the Exercise 4 checkpoint, default `make train` on the current code reproduced the committed file byte for byte (sha256 `4df4eb95...`). The code is not final yet, so rerun `make all` at the end |
| [x] | [ ] | Seeds fixed | `src/train.py:52` `HistGradientBoostingRegressor(random_state=0)`; ridge is deterministic |
| [x] | [ ] | Dependencies pinned, including any added ones | `requirements.txt` (nothing added so far) |
| [x] | [ ] | `.gitignore` no longer ignores `reports/` but still ignores `data/processed/`, `.venv/`, caches | `.gitignore`, changed in `d85aa8a` |
| [x] | [ ] | `data/processed/`, `.venv/`, `__pycache__/`, `.pytest_cache/` not committed | `git ls-files` shows none at `935ecdf` |
| [x] | [ ] | `data/raw/bike_daily.csv` unchanged (sha256 starts `a6bed1577f6e4de5`) | Full hash `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc` confirmed after the fault-4 restore (`b080d81`), and again before and after the isolated checksum demonstration (`docs/SEEDED_FAULTS.md` "Fault 4 defense" > "Canonical file"). `load_raw()` now enforces it as `RAW_SHA256`. Verified waits for a fresh-clone check at submission |
| [ ] | [ ] | Fresh clone, `pip install -r requirements.txt`, `make all`, then diff with committed metrics and the `REPORT.md` table | Pending. The SDK auditor's pipeline rerun reproduced `metrics.json` byte for byte, but in the working copy, not a fresh clone |

## 2. `CLAUDE.md` (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Forbidden columns | `CLAUDE.md` "Non-negotiable rules" |
| [x] | [ ] | Split rule | `CLAUDE.md` "Never split this data randomly" |
| [x] | [ ] | Both baselines (mean and persistence) | `CLAUDE.md` "Report the mean baseline **and** the persistence baseline" |
| [x] | [ ] | The command that reproduces the headline number, named as such | `CLAUDE.md` Commands: "`make all` ... reproduces the headline metrics in `reports/metrics.json`" |
| [ ] | [ ] | Rule for our feature, if needed | Not decided |
| [x] | [ ] | Name of our custom skill | `CLAUDE.md` Commands: `/seed-fault <forbidden-column\|rolling-leakage\|weather-guard>` |
| [x] | [ ] | Under 60 lines | 48 lines at this checkpoint (added the checksum-mismatch gotcha) |
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
| [x] | [ ] | `make test` passes | `22 passed in 1.71s` at the Exercise 4 checkpoint (adds `test_change_reconstruction_never_sees_todays_target`); `21 passed` at the checksum-defense checkpoint |
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
| [ ] | [ ] | `REPORT.md` **Results**: one 8-row table (4 models × before/after) with validation and test R² and MAE, matching `reports/metrics.json` exactly | Draft on `final-evaluation-report`: the 8 rows have validation values from both metrics files; test columns marked PENDING |
| [ ] | [ ] | `REPORT.md` **Headline finding**: one paragraph with numbers, plus one sentence on the feature and the keep decision | Draft marks it PENDING (needs the final test look) |
| [ ] | [ ] | No sign the test set was used while iterating (`DECISIONS.md`, commits) | Recorded in `docs/DECISIONS.md` (evaluation history): the default pipeline computes test metrics, and two early lines quote test figures recorded before feature work, but no feature or transformation decision used them. Review again before submission, after the single final test look |

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
| [ ] | [ ] | `docs/AUDIT.md`: teammate's repo URL, verbatim `/leakage-auditor` output, one-paragraph verdict kept separate from the auditor's findings | Pending: peer branch audit not started |
| [x] | [ ] | `reports/audit.jsonl` from `python agent/audit.py . --out reports/audit.jsonl` | Committed exactly as generated (sha256 `7154daa1...`), from `env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl` on `8450800`, 2026-11-24 13:43:54 -0800 (`docs/DECISIONS.md`, SDK audit run). Has every schema field; `findings` has 2 entries |
| [x] | [ ] | If the auditor flags our repo: fix it, or argue back in `REPORT.md` | Leakage `none`. Both findings answered in the `REPORT.md` draft (Attribution > "SDK audit of our repo"): observed weather accepted as a substantive limit and stated; README test count fixed (cosmetic) |

## 7. Decisions and attribution (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | `DECISIONS.md` keeps the 5 starter lines; new lines dated, newest last | `git diff 0654988 -- docs/DECISIONS.md` only adds lines |
| [x] | [ ] | One line per decision so far: agent backend, model correction, feature, keep, column classification, tracker | `docs/DECISIONS.md` |
| [ ] | [ ] | `REPORT.md` **Attribution**: first line names the model and size and whether we switched (Sonnet 5.5 planned, Opus 5.5 used, see `b033c19`) | No `REPORT.md` |
| [ ] | [ ] | Attribution list: files and functions the agent generated | No `REPORT.md` |
| [ ] | [ ] | Attribution list: our decisions, each traced to a `DECISIONS.md` line | No `REPORT.md` |
| [ ] | [ ] | Every decision has a commit and every commit has a decision | Check at the end |

## Remaining exercises

- [x] Ex 1: add one feature with `/new-feature`: `cnt_std_7`, kept (`e21af14`, `b03f86b`, `935ecdf`)
- [x] Ex 2: four seeded faults. Done: forbidden-column `4f3703c`, rolling-leakage `6f69ea5`, weather-guard `a0d7ab1` (each 2 repair tool calls / 1 repair cycle, which are lower bounds, not conversational turns); fault 4, the manual Bash raw-data copy, recorded with what would catch it
- [ ] Ex 3: audit a teammate; run `agent/audit.py` on our repo
- [ ] Ex 4: target transformation so hgb can compete. **Validation part done:** `python -m src.train --validation-target-experiment` -> `reports/target_transform_validation.json`. hgb predicting the daily change: valid R^2 0.5642 / MAE 885.8, vs ordinary hgb 0.0977 / 1381.6, persistence 0.4507 / 900.6, ridge 0.7224 / 700.4. **Interpretation recorded** (`docs/DECISIONS.md`, "refines the Exercise 4 result line"): improves hgb but does not establish the cause of its original weakness; small MAE gain over persistence with no uncertainty estimate; assumes yesterday's count and same-day observed weather are known. **Pending:** the single end-of-project test look (reported as such) and the REPORT.md section. Committed `metrics.json` stays untransformed
- [ ] Ex 5: one paragraph with numbers on whether ridge is worth deploying over persistence
- [ ] Ex 6 (optional): second model size or hosted model, as a subsection under Attribution

## Required `REPORT.md` structure (2-4 pages)

- [ ] **Results**: draft, validation filled, test PENDING
- [ ] **Headline finding**: PENDING in draft
- [ ] **Exercise 4: target transformation**: drafted from `reports/target_transform_validation.json`; test result PENDING
- [ ] **Exercise 5: ridge vs persistence**: PENDING in draft
- [ ] **Attribution**: drafted (model line, agent-generated list, decisions list, SDK audit assessment). TODO: DECISIONS lines for "what to predict" and "is it believable"

## Commit history (squashing all of it scores 0 on item 7)

| Done | Required commit, in order | Commit |
|---|---|---|
| [x] | 1. Unmodified starter, the first commit | `0654988` |
| [x] | 2. Failing test for the feature | `e21af14` |
| [x] | 3. Feature that makes the test pass | `b03f86b` (kept and refactored in `935ecdf`) |
| [x] | 4. Each seeded fault and its fix (or one commit per fault, with the fix in the message) | 4 of 4 distinct faults committed: forbidden-column `4f3703c`, rolling-leakage `6f69ea5`, weather-guard `a0d7ab1`, Bash raw-data copy `b080d81`. Later rechecks (the post-hardening `rolling-leakage` recheck is recorded under its own heading) do not change the count of 4 |
| [ ] | 5. Audit run | Not started |
| [ ] | 6. Report | Not started |

Setup commits `d85aa8a` and `b033c19` come between 1 and 2; each has a `DECISIONS.md` line.

## Submission

- [ ] Repository URL submitted through the course form (`https://github.com/YashTandon05/bikeshare-open`)
- No deadline is given on the assignment page.
