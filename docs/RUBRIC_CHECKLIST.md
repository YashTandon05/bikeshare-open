# Rubric checklist

Progress tracker for the [Methodology 07 (open) assignment](https://dsc-capstone.org/2026-27/assignments/methodology/07-open/).
Update after every checkpoint (see `CLAUDE.md`). Last updated: 2026-11-24, after fault 1 (`4f3703c`) and the skill-heading fix.

Each criterion has two boxes:

- **Impl**: the work exists in the repo. Cite the file, commit, or output.
- **Verified**: checked under grading conditions on the final code (fresh
  clone, `make all`, `make test`, compared with `REPORT.md`). Anything that
  can still change before submission stays unticked here.

| # | Category | Points | Status |
|---|---|---|---|
| 1 | Reproducible repository | 15 | Partly done |
| 2 | `CLAUDE.md` | 10 | Partly done |
| 3 | Verification suite | 25 | Feature, contract and weather-guard tests done; fault 1 of 4 recorded |
| 4 | Results with baselines | 20 | Validation measured; no report |
| 5 | Structural enforcement | 10 | Starter hook fired automatically on fault 1; faults 2-4 pending |
| 6 | Agent configuration | 10 | `/seed-fault` written and used once (fault 1); audits not started |
| 7 | Decisions and attribution | 10 | Ongoing decision log; no Attribution section |

## 1. Reproducible repository (15)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | `make all` runs data, features, then train | `Makefile` target `all: data features train` |
| [ ] | [ ] | `reports/metrics.json` comes from `make all` on the **final** code | Current file comes from `make train` at `b03f86b`. `935ecdf` changed `src/` (a refactor that keeps behavior) and was not retrained. Rerun at the end. |
| [x] | [ ] | Seeds fixed | `src/train.py:52` `HistGradientBoostingRegressor(random_state=0)`; ridge is deterministic |
| [x] | [ ] | Dependencies pinned, including any added ones | `requirements.txt` (nothing added so far) |
| [x] | [ ] | `.gitignore` no longer ignores `reports/` but still ignores `data/processed/`, `.venv/`, caches | `.gitignore`, changed in `d85aa8a` |
| [x] | [ ] | `data/processed/`, `.venv/`, `__pycache__/`, `.pytest_cache/` not committed | `git ls-files` shows none at `935ecdf` |
| [x] | [ ] | `data/raw/bike_daily.csv` unchanged (sha256 starts `a6bed1577f6e4de5`) | `sha256sum` gave `a6bed1577f6e4de5...` at `935ecdf` and again at the fault-workflow checkpoint. A final check after fault 4 is still needed |
| [ ] | [ ] | Fresh clone, `pip install -r requirements.txt`, `make all`, then diff with committed metrics and the `REPORT.md` table | Not done |

## 2. `CLAUDE.md` (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Forbidden columns | `CLAUDE.md` "Non-negotiable rules" |
| [x] | [ ] | Split rule | `CLAUDE.md` "Never split this data randomly" |
| [x] | [ ] | Both baselines (mean and persistence) | `CLAUDE.md` "Report the mean baseline **and** the persistence baseline" |
| [x] | [ ] | The command that reproduces the headline number, named as such | `CLAUDE.md` Commands: "`make all` ... reproduces the headline metrics in `reports/metrics.json`" |
| [ ] | [ ] | Rule for our feature, if needed | Not decided |
| [x] | [ ] | Name of our custom skill | `CLAUDE.md` Commands: `/seed-fault <forbidden-column\|rolling-leakage\|weather-guard>` |
| [x] | [ ] | Under 60 lines | 46 lines at this checkpoint |
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
| [x] | [ ] | `make test` passes | `19 passed in 1.29s` at the fault-workflow checkpoint (`18 passed` at `935ecdf`) |
| [x] | [ ] | Fault 1 (forbidden column in `feature_columns`): real red output pasted | `4f3703c`, `docs/SEEDED_FAULTS.md` "Fault: forbidden-column" > "Red test output": `FAILED tests/test_leakage.py::test_no_forbidden_features`, `1 failed, 18 passed`, `exit=2` |
| [ ] | [ ] | Fault 2 (`.shift(1)` removed from `cnt_roll_7`): real red output pasted | Not started |
| [ ] | [ ] | Fault 3 (`raise` removed from the weather encoder): real red output pasted | Not started. Groundwork: `tests/test_leakage.py::test_unknown_weather_label_is_rejected` makes this fault visible, since the raw data has only known labels and nothing else would fail |
| [ ] | [ ] | Fault 4 (`cp` into `data/raw/` from Bash): what happened, recorded | Not started |
| [ ] | [ ] | Pasted output matches what the final tests print | Check after all faults |

## 4. Results with baselines (20)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Metrics from before the feature kept | `reports/metrics_before_feature.json` (`d85aa8a`, never changed) |
| [x] | [ ] | Feature's validation effect measured without using test scores | Ridge R² 0.6475 to 0.7224, hgb 0.2185 to 0.0977 (`b03f86b`, `docs/DECISIONS.md`) |
| [x] | [ ] | Validation delta explained, including the negative one | `docs/DECISIONS.md` keep entry (`935ecdf`); hgb's drop reported, cause not yet found |
| [ ] | [ ] | `REPORT.md` **Results**: one 8-row table (4 models × before/after) with validation and test R² and MAE, matching `reports/metrics.json` exactly | No `REPORT.md` |
| [ ] | [ ] | `REPORT.md` **Headline finding**: one paragraph with numbers, plus one sentence on the feature and the keep decision | No `REPORT.md` |
| [ ] | [ ] | No sign the test set was used while iterating (`DECISIONS.md`, commits) | Review before submission |

## 5. Structural enforcement (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Starter hook and permissions still work | `.claude/settings.json` unchanged except `model`; the hook fired on a `src/features.py` edit while building `935ecdf` (a `NameError` from an edit made in two steps) |
| [ ] | [ ] | Hook stderr pasted for faults 1-3 | 1 of 3 done. Fault 1 (`4f3703c`): automatic feedback appeared, recorded in `docs/SEEDED_FAULTS.md` "Fault: forbidden-column" > "Automatic hook feedback (PostToolUse)". Manual diagnostic `exit=2` also recorded. Faults 2-3 pending. Tick only when the *automatic* PostToolUse feedback appeared; the manual diagnostic (also recorded, with its measured exit code) does not count |
| [ ] | [ ] | Fault 4: paragraph naming what would catch it (`Stop` hook, `PreToolUse` on Bash, filesystem permission, or a hash check in `make data`) | Not started |
| [ ] | [ ] | Optional (up to 3 pts): implement the fault-4 catch | Not started |

## 6. Agent configuration (10)

| Impl | Verified | Criterion | Evidence |
|---|---|---|---|
| [x] | [ ] | Our own skill in `.claude/skills/<name>/SKILL.md`, for a workflow we repeated, taking `$ARGUMENTS` | `.claude/skills/seed-fault/SKILL.md` (uses `$ARGUMENTS`, `disable-model-invocation: true`). Created in `6fb1c66`, corrected in `040ee64`. **First real use:** `/seed-fault forbidden-column` produced the "Fault: forbidden-column" record in `docs/SEEDED_FAULTS.md` (`4f3703c`). The table heading that `$ARGUMENTS` was substituting into was fixed afterwards (text only). Verified stays unticked until the final skill text has run faults 2-3. (`.claude/skills/run-pipeline/` is still an empty, untracked directory) |
| [x] | [ ] | Starter `new-feature` skill kept | `.claude/skills/new-feature/SKILL.md` |
| [ ] | [ ] | `docs/AUDIT.md`: teammate's repo URL, verbatim `/leakage-auditor` output, one-paragraph verdict kept separate from the auditor's findings | Not started |
| [ ] | [ ] | `reports/audit.jsonl` from `python agent/audit.py . --out reports/audit.jsonl` | Not started |
| [ ] | [ ] | If the auditor flags our repo: fix it, or argue back in `REPORT.md` | Pending the audit |

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
- [ ] Ex 2: four seeded faults (1 of 4 done: forbidden-column in `4f3703c`, 2 repair tool calls / 1 cycle; rolling-leakage, weather-guard and the manual raw-data fault pending), with repair effort for 1-3 (reported as repair tool calls and repair cycles, not conversational turns; see the `/seed-fault` counting convention). Faults 1-3 go through `/seed-fault`; fault 4 (raw-data `cp`) is done by hand, outside the skill
- [ ] Ex 3: audit a teammate; run `agent/audit.py` on our repo
- [ ] Ex 4: target transformation so hgb can compete. Validation only; touch test once at the end and say so; the committed `metrics.json` stays untransformed
- [ ] Ex 5: one paragraph with numbers on whether ridge is worth deploying over persistence
- [ ] Ex 6 (optional): second model size or hosted model, as a subsection under Attribution

## Required `REPORT.md` structure (2-4 pages)

- [ ] **Results**: 8-row table, validation and test R² and MAE, before and after the feature
- [ ] **Headline finding**: one paragraph with numbers, plus the feature sentence
- [ ] **Exercise 4: target transformation**
- [ ] **Exercise 5: ridge vs persistence**
- [ ] **Attribution**: model line, agent-generated list, our-decisions list

## Commit history (squashing all of it scores 0 on item 7)

| Done | Required commit, in order | Commit |
|---|---|---|
| [x] | 1. Unmodified starter, the first commit | `0654988` |
| [x] | 2. Failing test for the feature | `e21af14` |
| [x] | 3. Feature that makes the test pass | `b03f86b` (kept and refactored in `935ecdf`) |
| [ ] | 4. Each seeded fault and its fix (or one commit per fault, with the fix in the message) | 1 of 4 committed: forbidden-column `4f3703c`. Stays pending until **all four** prescribed experiments are recorded and committed |
| [ ] | 5. Audit run | Not started |
| [ ] | 6. Report | Not started |

Setup commits `d85aa8a` and `b033c19` come between 1 and 2; each has a `DECISIONS.md` line.

## Submission

- [ ] Repository URL submitted through the course form (`https://github.com/YashTandon05/bikeshare-open`)
- No deadline is given on the assignment page.
