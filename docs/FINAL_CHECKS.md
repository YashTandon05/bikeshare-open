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

- `REPORT.md` length is estimated, not rendered (no PDF engine on this machine): 1,909 words in five `##` sections, about 3.6 pages.
- The leftover clones in `/tmp/fresh-20261124-172131/` were not deleted.
