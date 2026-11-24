# Bikeshare demand: methodology report

> **DRAFT. Not for submission.** This draft holds validation results only.
> Still **pending**: the final test-set interpretation, the test columns of
> the results table, the headline finding, and the Exercise 5 deployment
> argument. Every number here is copied from a committed file named next to
> it. No test-set figure has been read for this draft.

**Prediction-time assumption, applies throughout.** The weather inputs
(`temp`, `atemp`, `hum`, `windspeed`, `weather`) are the day's *observed*
values. Ridge and both hgb variants are therefore scored as if the actual
weather for the day being forecast were known when the forecast is made. A
real day-ahead forecast would use predicted weather and would probably score
worse, so every model score below is an upper bound on deployable
performance. The lag features also assume yesterday's final count is known
before today is forecast. The mean and persistence baselines use no weather.

## Results

Daily counts, temporal split: train 2011 (348 rows), validation
2012-01-01 to 2012-06-30 (182 rows), test H2 2012. "Before" is the starter
feature set (14 features, `reports/metrics_before_feature.json`). "After"
adds `cnt_std_7`, the population standard deviation of `cnt` over the seven
calendar days before each date (15 features, `reports/metrics.json`).

| model | feature set | valid R² | valid MAE | test R² | test MAE |
|---|---|---|---|---|---|
| baseline_mean | before (14 features) | -0.9318 | 2002.2 | PENDING | PENDING |
| baseline_mean | after (15 features, + cnt_std_7) | -0.9318 | 2002.2 | PENDING | PENDING |
| baseline_persistence | before (14 features) | 0.4507 | 900.6 | PENDING | PENDING |
| baseline_persistence | after (15 features, + cnt_std_7) | 0.4507 | 900.6 | PENDING | PENDING |
| ridge | before (14 features) | 0.6475 | 832.9 | PENDING | PENDING |
| ridge | after (15 features, + cnt_std_7) | 0.7224 | 700.4 | PENDING | PENDING |
| hgb | before (14 features) | 0.2185 | 1296.6 | PENDING | PENDING |
| hgb | after (15 features, + cnt_std_7) | 0.0977 | 1381.6 | PENDING | PENDING |

**PENDING: complete table.** The test columns will be filled from
`reports/metrics.json` in one explicit final look, after a fresh-clone
`make all` confirms the committed metrics.

Validation effect of `cnt_std_7`: ridge +0.0749 R² (MAE -132.5 rides/day),
hgb -0.1208 R² (MAE +85.0). We kept the feature because of ridge, the
stronger model and the only one that beats persistence on validation. The
hgb deterioration is reported, not hidden; we did not establish its cause
(`docs/DECISIONS.md`, KEEP line).

## Headline finding

**PENDING.** The headline needs the final test interpretation, which has
not been done. What the validation set shows so far is not the headline:
ridge with `cnt_std_7` is the selected model (valid R² 0.7224, MAE 700.4),
ahead of persistence (0.4507, 900.6). Ordinary hgb falls below persistence
(0.0977, 1381.6).

## Exercise 4: target transformation

**Hypothesis (recorded before the run).** hgb might handle the 2011-to-2012
growth better if it predicted the change from yesterday rather than the
level: fit on `cnt - cnt_lag_1`, then forecast `cnt_lag_1 + predicted_change`.

**Method.** `python -m src.train --validation-target-experiment`, run once.
It uses the same 15 features, temporal split and model parameters, with cloned
estimators. Test rows are dropped before anything is fitted or scored, and
today's true count is used only for scoring. A unit test
(`test_change_reconstruction_never_sees_todays_target`) shows the
reconstruction uses only the feature frame. Output:
`reports/target_transform_validation.json`.

| method | valid R² | valid MAE (rides) |
|---|---|---|
| baseline_mean | -0.9318 | 2002.2 |
| baseline_persistence | 0.4507 | 900.6 |
| ridge | 0.7224 | 700.4 |
| hgb | 0.0977 | 1381.6 |
| hgb_daily_change | 0.5642 | 885.8 |

Validation only: 182 rows, 2012-01-01 to 2012-06-30, 348 training rows.

**Interpretation.**

- Predicting the change makes hgb much better: R² +0.4665, MAE -495.8
  rides/day. This **does not establish why** ordinary hgb was weak. "Trees
  cannot extrapolate the 2012 level" fits the result but was not tested.
- It beats persistence clearly on R² (+0.1135), but on MAE only by 14.8
  rides/day (1.6%). **We did not estimate uncertainty** (no bootstrap or
  interval), so we do not claim it beats persistence on typical error.
- It stays well behind ridge: R² -0.1582, MAE +185.4.

**Defensible, or a way to win?** It is defensible for **one-day-ahead**
forecasts where yesterday's observed final count is available before today
is predicted, which is the assumption persistence and the lag features
already make. It also inherits the observed-weather assumption above. It
was a structural choice (differencing), fixed before the run, run once,
and not tuned. It would not carry over to forecasts several days ahead
without recursive forecasting, where yesterday's count is itself a
prediction. It does not "win": ridge remains selected, and the committed
`reports/metrics.json` stays untransformed.

**PENDING: test-set result.** If it is reported, it will come from a single
look at the end, stated as such.

## Exercise 5: ridge vs persistence

**PENDING: deployment argument.** It will be argued with numbers once the
final test interpretation is done. The validation inputs available now:
ridge R² 0.7224, MAE 700.4 vs persistence 0.4507, 900.6, both scored under
the observed-weather assumption. Persistence needs no weather data, which
the argument has to weigh.

## Attribution

**Model:** Claude Opus 5.5, hosted, through Claude Code (model id
`claude-opus-5-5`; Anthropic does not publish its size). Did we switch?
Yes: the setup plan named Claude Sonnet 5.5, but the setup checkpoint and all
later work ran on Opus 5.5 instead of the local `bikeshare-coder` default
(`docs/DECISIONS.md`, agent-backend line and its correction; `b033c19`). The
SDK audit also ran on Opus (`AUDIT_MODEL=opus`).

**Agent-generated files and functions** (written by Claude under our
direction; we reviewed each before committing):

- `src/features.py`: the `cnt_std_7` line, and `WEEK_DAYS` replacing the literal 7
- `src/config.py`: `WEEK_DAYS`, the raw-column classification sets
  (`REDUNDANT_CALENDAR_COLS`, `DATE_COL`, `PREDICTOR_INPUT_COLS`,
  `CLASSIFIED_RAW_COLS`), `RAW_SHA256`, `TARGET_TRANSFORM_VALIDATION`
- `src/ingest.py`: `file_sha256()` and the checksum check in `load_raw()`
- `src/train.py`: `reconstruct_from_change()`,
  `validation_target_experiment()`, `markdown_table()`, and the
  `--validation-target-experiment` flag
- `tests/test_leakage.py`: `test_rolling_std_excludes_today`,
  `test_unknown_weather_label_is_rejected`, and the hardening of
  `test_rolling_mean_excludes_today`
- `tests/test_contract.py`: `assert_all_columns_classified` and its three
  tests, the two `load_raw` checksum tests, and
  `test_change_reconstruction_never_sees_todays_target`
- `.claude/skills/seed-fault/SKILL.md`
- `docs/SEEDED_FAULTS.md`, `docs/RUBRIC_CHECKLIST.md`, the wording of our
  `docs/DECISIONS.md` lines, the README test-count fix, and this draft

**Our decisions** (each traces to a line in `docs/DECISIONS.md`):

- What counts as leakage: exclude `casual`/`registered`, `cnt_2d_bfr`, and
  the time indexes (starter lines), and give every raw column one role
  (column-classification line)
- How to split: 2011 / H1 2012 / H2 2012 by date (starter line)
- Which baselines: mean and persistence with every score (starter line)
- Keep `cnt_std_7`, on ridge's validation gain, while reporting hgb's drop (KEEP line)
- Select ridge and close the modeling phase (modeling-closed line)
- Run the daily-change target as the single Exercise 4 experiment
  (Exercise 4 plan line)
- Defend against raw-data overwrites with a checksum, not a broader
  permission change (fault-4 and checksum-defense lines)
- Use the hosted Opus 5.5 instead of the local model (agent-backend lines)
- TODO before submission: "what to predict" (one-day-ahead daily `cnt`) and
  "whether the answer is believable" have no `DECISIONS.md` line yet

### SDK audit of our repo: findings and our assessment

Auditor output, verbatim in `reports/audit.jsonl`: run with
`env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl` on
commit `8450800`, 2026-11-24. Verdict: leakage `none`, `temporal_ok`
true, `baseline_reported` true, `reproducible` true, confidence `high`.
Two findings:

1. *Auditor:* same-day observed weather is used to predict same-day `cnt`.
   Not leakage (`check_identity` clean on all 15 features), but it assumes
   perfect weather knowledge, so the scores are an upper bound.
   **Our assessment: substantive, accepted.** This is a real limit on what
   the numbers mean for a deployed forecaster, not a bug to fix in code. We
   keep the observed-weather setup the assignment defines and state the
   assumption at the top of this report, in Exercise 4, and in Exercise 5.
   It does not change any reported number.
2. *Auditor:* README said `make test` runs 14 tests; the suite runs 22.
   **Our assessment: cosmetic doc drift, fixed.** The README now just says
   `make test` runs the verification suite, with no hardcoded count to go
   stale. No number or method is affected.
