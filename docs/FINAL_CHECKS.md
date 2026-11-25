# Final checks

Fresh-clone reproduction of pushed `master`, run 2026-11-24 by Yash Tandon (commands run through Claude Code, Claude Opus 5.5).

| Field | Value |
|---|---|
| Repository | https://github.com/YashTandon05/bikeshare-open |
| Tested commit | `edd74cff6ace0e901964e816a7822f9939b3978f` (`master`, merge of `final-evaluation-report`) |
| Clone | `git clone https://github.com/YashTandon05/bikeshare-open.git /tmp/fresh-20261124-172131/repo` (new, empty directory; `core.autocrlf` unset) |
| Interpreter | `/usr/bin/python3.12`, Python 3.12.3 |
| Platform | Linux (WSL2) |

## Environment

```
python3.12 -m venv .venv
.venv/bin/pip install -q -r requirements.txt      # exit 0
```

`python3.12` on the PATH was the project's existing `.venv` interpreter, but `-m venv` built a new, independent environment. Its `pyvenv.cfg` has `executable = /usr/bin/python3.12` and `include-system-site-packages = false`, and `sys.prefix` is the clone's `.venv`. Installed versions match the pins: numpy 2.5.3, pandas 3.0.5, pyarrow 26.0.1, scikit-learn 1.9.1, pytest 9.1.1, claude-agent-sdk 0.2.172.

## Pipeline and tests (with the clone's `.venv/bin` first on `PATH`)

| Command | Result |
|---|---|
| `make all` | exit 0. `OK ingest: 728 rows, 2011-01-03 -> 2012-12-31`; `OK features: 714 rows, 15 features -> features.parquet`; `src.train` wrote `reports/metrics.json` (`n_train` 348, `n_valid` 182, `n_test` 184) |
| `make test` (`python -m pytest tests/ -q`) | exit 0, `27 passed in 1.91s` |

## Metrics comparison

| Check | Result |
|---|---|
| `sha256sum reports/metrics.json`, before `make all` (committed) | `4df4eb95b75f186b18ebad13a81cc88ce7c3b8e5cc377c79373e2292ed460dde` |
| `sha256sum reports/metrics.json`, after `make all` (regenerated) | `4df4eb95b75f186b18ebad13a81cc88ce7c3b8e5cc377c79373e2292ed460dde` |
| `git diff --exit-code reports/metrics.json` | exit 0: byte-identical to the committed file |
| `git status --porcelain` after `make all` | empty |

The eight `REPORT.md` Results rows were parsed by a script (`python3 -I check_rows.py`, kept outside the clone) and compared with exact float equality to `reports/metrics_before_feature.json` ("before") and the regenerated `reports/metrics.json` ("after"). **8/8 match.**

| model | set | valid R² | valid MAE | test R² | test MAE | match |
|---|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 | OK |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 | OK |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 | OK |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 | OK |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 | OK |
| ridge | after | 0.7224 | 700.4 | 0.6356 | 840.3 | OK |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 | OK |
| hgb | after | 0.0977 | 1381.6 | -0.6959 | 2108.4 | OK |

## Raw data

| Check | Result |
|---|---|
| `sha256sum data/raw/bike_daily.csv` | `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc` |
| `RAW_SHA256` in `src/config.py` | `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc` (match) |
| `load_raw()` | OK, 728 rows |
| `git ls-files --eol data/raw/bike_daily.csv` | `i/lf w/lf attr/text=auto eol=lf` |

### Checkout with `core.autocrlf=true`

This is a second clone of the same pushed `master`, reusing the first clone's environment (no second install).

| Checkout | `--eol` | sha256 of `data/raw/bike_daily.csv` | `load_raw()` / tests |
|---|---|---|---|
| `git clone -c core.autocrlf=true ...` at `edd74cf` (with `.gitattributes`) | `i/lf w/lf attr/text=auto eol=lf` | `a6bed157...b0ad9dc` (trusted) | OK, 728 rows; `pytest tests/ -q`: `27 passed in 1.81s` |
| Control: `git worktree add ... 4d004fd` in that clone (before `.gitattributes`) | `i/lf w/crlf attr/` | `13e33ae5fe50b591515f796baa37b3e009af84dcde909e1dbb0fa90d9684031b` | `ValueError: raw data checksum mismatch ... expected sha256 a6bed157..., got 13e33ae5...` |

The control reproduces the hash Issac Roy observed on Windows (`docs/AUDIT.md`, reciprocal review). With the `* text=auto eol=lf` rule, the same `core.autocrlf=true` checkout keeps the trusted bytes.

## Repository checks

| Check | Result |
|---|---|
| `wc -l < CLAUDE.md` | 48 (under 60) |
| Required files (`git ls-files --error-unmatch`) | all tracked: `CLAUDE.md`, `REPORT.md`, `Makefile`, `requirements.txt`, `.gitignore`, `.gitattributes`, `docs/{DECISIONS,AUDIT,SEEDED_FAULTS,RUBRIC_CHECKLIST}.md`, `reports/{metrics,metrics_before_feature,target_transform_validation,target_transform_final_test}.json`, `reports/audit.jsonl`, `reports/audit_initial_8450800.jsonl`, `.claude/skills/{seed-fault,new-feature}/SKILL.md`, `.claude/agents/leakage-auditor.md`, `agent/audit.py`, `tests/test_leakage.py`, `tests/test_audit.py`, `data/raw/bike_daily.csv` |
| Commit history (`git rev-list --count HEAD`) | 33 commits; root `0654988` (unmodified starter) |
| Required commits in history (`git merge-base --is-ancestor`) | starter `0654988`; failing test `e21af14`; feature `b03f86b` / `935ecdf`; faults `4f3703c`, `6f69ea5`, `a0d7ab1`, `b080d81`; SDK audit `601400b`; peer audit `9df6f70`, `050eaa0`; reciprocal review `4d004fd`; report `6dd265e`, `f572f37`, `60a7dd2`; final evaluation `9315d78`; merges `cf5cb31`, `edd74cf`. All present |
| Generated files tracked? `git ls-files` filtered for `.venv`, `__pycache__`, `.pytest_cache`, `data/processed`, `*.pyc`, `*.parquet` | none tracked |
| `git check-ignore -v` | `data/processed/` (`.gitignore:4`), `.venv/` (`:1`), `__pycache__/` (`:2`), `.pytest_cache/` (`:3`); `git status --porcelain --ignored` shows them only as ignored (`!!`) |

## Not covered here

- `REPORT.md` length is estimated, not rendered (no PDF engine on this machine): 1,909 words in five `##` sections, about 3.6 pages. **Superseded** by the rendered check in "Closeout documentation checks" below.
- The leftover clones in `/tmp/fresh-20261124-172131/` were not deleted.

## Closeout documentation checks

Run 2026-11-24 on `master` in the working copy by Yash Tandon (commands run through Claude Code, Claude Opus 5.5). Documentation-only: no experiment, SDK audit, or peer review was run in this step.

### Final SDK audit

| Field | Value |
|---|---|
| Command (fish history, 18:00:17 -0800) | `source .venv/bin/activate.fish; env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl` |
| Audited commit | `28572c4` (`master` HEAD; `reports/audit.jsonl` was the only uncommitted change afterwards) |
| Output | `reports/audit.jsonl`, written 18:00:57, sha256 `7197d5a670c07db5c9d350a17bbe1bdd36f53a7f8e7e243a1168091b49f08387`, committed as generated in `db238a6` (`git show db238a6:reports/audit.jsonl \| sha256sum` matches) |
| Result | 0 flagged, 0 errors; `"leakage": "none"`, `temporal_ok` / `baseline_reported` / `reproducible` true, `"confidence": "high"`, `"findings": []` |
| Initial audit archive | `reports/audit_initial_8450800.jsonl`, sha256 `7154daa1...3f152`, byte-identical to the pre-closeout `reports/audit.jsonl` (`diff` exit 0); its two findings are unchanged |

### Seeded-fault output

Every historical record was checked against the test source and suite size at its recorded commit (`git show <commit>:tests/test_leakage.py`, `git grep '^def test_' <commit> -- tests`). All records are kept unchanged, including counts and timings.

| Record (commit) | Failing test at that commit | Pasted line | Line at commit | Pasted totals | Tests at commit | Same assertion in final tests? |
|---|---|---|---|---|---|---|
| Feature test before implementation (`e21af14`) | `test_rolling_std_excludes_today` | 74 | 74 | 1 failed, 14 passed | 15 | yes (now line 75) |
| forbidden-column (`4f3703c`) | `test_no_forbidden_features` | 31 | 31 | 1 failed, 18 passed | 19 | yes (line 31) |
| rolling-leakage (`6f69ea5`) | `test_rolling_mean_excludes_today`, pre-hardening `if all(...)` form | 57 | 57 | 1 failed, 18 passed | 19 | no: hardened in `7d64596`; same values 4389.0 vs 4414.857142857143 |
| weather-guard (`a0d7ab1`) | `test_unknown_weather_label_is_rejected` | 82 | 82 | 1 failed, 18 passed | 19 | yes (now line 83) |
| rolling-leakage recheck (`eae3d3e`, from `7d64596`) | hardened `test_rolling_mean_excludes_today` | 58 | 58 | 1 failed, 20 passed | 21 | yes (line 58) |
| Fault 4, Bash `cp` (`b080d81`) | none: suite stayed green | n/a | n/a | 19 passed | 19 | n/a; now caught by the two checksum tests |

Each commit adds its own `docs/SEEDED_FAULTS.md` section. Line numbers below the rolling-mean test moved down by one when `7d64596` added the window-completeness assertion. The final suite has 27 tests, so a rerun today would print different totals; the records show what ran at the time.

### Decision-commit cross-check

`git blame docs/DECISIONS.md` against `git log`: every decision line has a commit. Commits without their own line, and the Exercise 4 plan committed with its result (`05ea1ed`), are listed in `docs/DECISIONS.md` ("decision-commit cross-check") and were not back-filled.

### `CLAUDE.md`

`wc -l < CLAUDE.md`: 48. Added the `cnt_std_7` rule (seven prior calendar days, `ddof=0`); replaced the growth/extrapolation gotcha with "untested explanation; the headline follows the measured baseline comparisons"; folded the single-stage `make` lines into `make all`.

### `REPORT.md` rendered length

Headless Chrome could not start (WSL interop: `UtilAcceptVsock ... accept4 failed 110`), and the local groff has no `ms` macros or PDF device. Rendered instead with pandoc 3.1.3 (`-t typst`) and typst 0.15.2 (PyPI wheel in a throwaway venv under `/tmp`, not a project dependency). Settings: US Letter, 0.75 in margins, 11 pt body and tables, justified, Libertinus Serif. Pages were counted with a typst `counter(page).final()` query, and the PDFs were inspected visually.

| Version | Words | Default leading (0.65em) | Word-like leading (0.9em) |
|---|---|---|---|
| Before closeout (`28572c4`) | 2,007 | 4 pages, last page nearly full | **5 pages**, matching ChatGPT's 5-page sample at 11 pt / 0.75 in |
| Final | 1,888 | 4 pages, last page about half full | 4 pages, last page about three-quarters full |

Trimmed: repeated observed-weather qualifications (stated once at the top and argued in Exercise 5), the wrapped "after (15, + cnt_std_7)" table labels (the definition stays in the text), and the attribution lists. Kept: exactly five `##` sections, all 8 Results rows and the Exercise 4 table, every number (a script comparing the decimal numbers in `REPORT.md` before and after found none added or dropped), attribution, and the verbatim auditor text with our assessments. Added: the final-audit assessment. In the much wider DejaVu Serif, the final text still runs to 5 pages at default leading, so readers should use a standard serif or sans font.

### Unchanged by the closeout

| Check | Result |
|---|---|
| `git diff --stat 28572c4 -- src tests data agent Makefile requirements.txt .claude reports/metrics.json reports/metrics_before_feature.json reports/target_transform_validation.json reports/target_transform_final_test.json reports/audit_initial_8450800.jsonl` | empty |
| `sha256sum data/raw/bike_daily.csv` | `a6bed157...b0ad9dc` = `RAW_SHA256` |
| `sha256sum reports/metrics.json` | `4df4eb95...460dde` (unchanged) |
| `python -m pytest tests/ -q` | `27 passed in 2.37s` |

Changed files in the closeout: `reports/audit.jsonl` (`db238a6`), then `CLAUDE.md`, `REPORT.md`, `docs/DECISIONS.md`, `docs/RUBRIC_CHECKLIST.md`, and this file.
