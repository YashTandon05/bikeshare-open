# Bikeshare demand: methodology report

> **Status: complete draft for team review.** Every number is copied from a
> committed JSON file named next to it. The conclusions in *Headline
> finding* and *Exercise 5* are **proposed** and await our sign-off.
> Still pending outside this report: the peer `/leakage-auditor` audit
> (`docs/AUDIT.md`) and the fresh-clone reproduction check.

**Prediction-time assumption, applies throughout.** The weather inputs
(`temp`, `atemp`, `hum`, `windspeed`, `weather`) are the day's *observed*
values. Ridge and both hgb variants are therefore scored as if the actual
weather for the day being forecast were known when the forecast is made.
The lag features assume yesterday's final count is known before today is
forecast. The mean and persistence baselines use no weather. What we
evaluate is a **reproducible comparison with observed weather available**;
operational forecast performance, with *predicted* weather, is untested and
probably worse.

## Results

Target: daily total rides `cnt` (the assignment's target). Temporal split:
train 2011 (348 rows), validation 2012-01-01 to 2012-06-30 (182 rows), test
H2 2012 (184 rows). "Before" is the starter feature set (14 features,
`reports/metrics_before_feature.json`, frozen before feature work). "After"
adds `cnt_std_7`, the population standard deviation of `cnt` over the seven
calendar days before each date (15 features, `reports/metrics.json`,
produced by `make all`).

| model | feature set | valid R² | valid MAE | test R² | test MAE |
|---|---|---|---|---|---|
| baseline_mean | before (14) | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after (15, + cnt_std_7) | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before (14) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after (15, + cnt_std_7) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before (14) | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after (15, + cnt_std_7) | 0.7224 | 700.4 | 0.6356 | 840.3 |
| hgb | before (14) | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after (15, + cnt_std_7) | 0.0977 | 1381.6 | -0.6959 | 2108.4 |

MAE is in rides per day. The baselines do not use `cnt_std_7`, so their
rows are identical before and after.

**Evaluation history.** We kept `cnt_std_7` on validation alone (ridge
+0.0749 R², hgb -0.1208). The default pipeline computes test metrics on
every run, but no feature, transformation or model choice used them. The
final look was planned and recorded before it ran: `make all` and
`python -m src.train --final-target-test`, run once each on 2026-11-24 at
commit `9315d78`, after the evaluation code was committed. `make all`
reproduced `reports/metrics.json` byte for byte.

## Headline finding

A tree model trained on 2011 fails on 2012, while a linear model succeeds
but only just beats "yesterday again". Ridership grew so much that
predicting the 2011 mean scores test R² **-2.1441** (MAE 2847.7). Ordinary
hgb scores test R² **-0.6959** (MAE 2108.4); that fits trees being unable
to extrapolate past 2011 levels, but we did not test that cause. It is far below the persistence baseline
(**0.5099**, MAE **840.1**), which simply predicts yesterday's count.
Ridge reaches test R² **0.6356**, but its MAE (**840.3**) equals
persistence's: it cuts large misses, not the typical one. Adding
`cnt_std_7` helped ridge on both splits (test R² +0.0523, MAE -106.8) and
hurt hgb on both (test R² -0.1984, MAE +135.8). We kept it, based on
validation, for ridge. All model scores assume same-day **observed weather**,
so they are upper bounds on a real day-ahead forecast.

## Exercise 4: target transformation

**Hypothesis (recorded before running).** hgb might handle the 2011-to-2012
growth better if it predicted the change from yesterday rather than the
level: fit on `cnt - cnt_lag_1`, then forecast `cnt_lag_1 + predicted_change`.

**Method.** Same 15 features, same parameters, cloned estimators, fitted on
the 2011 rows only. Today's true count is used only for scoring; a unit
test (`test_change_reconstruction_never_sees_todays_target`) shows the
reconstruction uses only the feature frame. We ran it on validation
(`--validation-target-experiment`) and then once on test
(`--final-target-test`, no refit on validation). The committed
`reports/metrics.json` stays untransformed.

| method | valid R² | valid MAE | test R² | test MAE |
|---|---|---|---|---|
| baseline_mean | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | 0.7224 | 700.4 | 0.6356 | 840.3 |
| hgb | 0.0977 | 1381.6 | -0.6959 | 2108.4 |
| hgb_daily_change | 0.5642 | 885.8 | 0.4761 | 990.5 |

Sources: `reports/target_transform_validation.json`,
`reports/target_transform_final_test.json`.

**What it shows.**

- Predicting the change transforms hgb: R² +0.4665 on validation and
  +1.1720 on test; MAE -495.8 and -1117.9.
- On validation it edged past persistence (R² +0.1135, MAE -14.8). **On
  test it did not:** 0.4761 vs 0.5099 R², 990.5 vs 840.1 MAE. The small
  validation advantage, which we flagged as within noise and had no
  uncertainty estimate, did not hold up.
- It stays behind ridge on both splits.
- It **does not establish why** ordinary hgb fails. Extrapolation fits the
  pattern but was not tested directly.

**Defensible, or a way to win?** It is defensible as a method. It assumes
only what persistence and the lag features already assume: yesterday's
observed count is available before today is forecast. It inherits the
observed-weather assumption. It was a structural choice (differencing),
fixed before the run and not tuned. It applies only one day ahead; further
out, yesterday's count would itself be a prediction. But it does not let
gradient boosting compete. It rescues hgb from failure, yet on test it
loses to the simplest baseline, so we would not adopt it.

## Exercise 5: ridge vs persistence

**Proposed position: on this evidence, ridge is not worth deploying over
persistence as a day-ahead forecaster.**

- On test, the two make the same typical error: MAE **840.3 vs 840.1**
  rides/day.
- Ridge's R² advantage (**0.6356 vs 0.5099**) means about 26% less squared
  error (SSE ratio ≈ (1-0.6356)/(1-0.5099) ≈ 0.74, RMSE about 14% lower,
  from rounded R²). So ridge's value is in fewer large misses, not
  better everyday accuracy.
- The edge shrank from validation to test: validation MAE 700.4 vs 900.6,
  SSE ratio ≈ 0.51.
- It was measured with same-day **observed** weather. A deployed ridge
  would get weather *forecasts*, which would erode the remaining margin by
  an amount we have not measured.
- Persistence needs no weather feed, no features, no fitted model and no
  retraining as ridership grows. It cannot leak, and it degrades
  predictably.
- We estimated no uncertainty: one split, 184 test days, including
  Hurricane Sandy (2012-10-29, 22 rides), which hits every lag-based model.

The case *for* ridge is conditional. If large misses are much costlier than
typical ones, and ridge still beats persistence when fed forecast weather,
it could be worth the extra machinery. Neither condition has been shown,
so persistence should be the default and ridge a candidate pending that
test.

## Attribution

**Model:** Claude Opus 5.5 (`claude-opus-5-5`, hosted; Anthropic does not
publish its size). We switched models: the setup plan named Claude Sonnet
5.5, but setup and all later work ran on Opus 5.5, instead of the
starter's local `bikeshare-coder`. See `b033c19` and the agent-backend
lines in `docs/DECISIONS.md`.

**Contributors and tools.**

- **Yash Tandon:** every methodological decision below, reviewed every
  commit, ran the SDK audit, approved or denied agent actions.
- **Claude Opus 5.5 via Claude Code**, interactively: wrote code, tests and
  documentation drafts under that direction. It used the starter's
  PostToolUse leakage hook, the starter `/new-feature` skill, and our
  `/seed-fault` skill.
- **Claude Opus 5.5 via the Agent SDK** (`agent/audit.py`,
  `AUDIT_MODEL=opus`): audited this repo.
- The starter's `/leakage-auditor` subagent has not been run yet: the peer
  audit is pending.

**Agent-generated files and functions** (reviewed before each commit):

- `src/features.py`: the `cnt_std_7` line, and `WEEK_DAYS` replacing the literal 7
- `src/config.py`: `WEEK_DAYS`, the raw-column classification sets,
  `RAW_SHA256`, and the two target-experiment output paths
- `src/ingest.py`: `file_sha256()` and the checksum check in `load_raw()`
- `src/train.py`: `reconstruct_from_change()`, `_target_comparison()`,
  `validation_target_experiment()`, `final_target_test()`,
  `markdown_table()`, and the two flags
- `tests/`: `test_rolling_std_excludes_today`,
  `test_unknown_weather_label_is_rejected`, the hardened
  `test_rolling_mean_excludes_today`, the column-classification guard and
  its tests, the two checksum tests, and the reconstruction test
- `.claude/skills/seed-fault/SKILL.md`, `docs/SEEDED_FAULTS.md`,
  `docs/RUBRIC_CHECKLIST.md`, the wording of our `docs/DECISIONS.md` lines,
  `README.md` updates, and this report's text

**Our decisions** (each traces to a dated line in `docs/DECISIONS.md`):

- What to predict: the assignment's daily `cnt` (target line)
- What counts as leakage: exclude `casual`/`registered`, `cnt_2d_bfr`, and
  the time indexes (starter lines), and give every raw column one role
  (column-classification line)
- How to split: 2011 / H1 2012 / H2 2012 by date (starter line)
- Which baselines: mean and persistence with every score (starter line)
- Keep `cnt_std_7` on ridge's validation gain, reporting hgb's drop (KEEP line)
- Select ridge and close modeling (modeling-closed line)
- Run the daily-change target as the single Exercise 4 experiment (plan line)
- Plan the final evaluation before running it (final-evaluation plan line)
- Detect raw-data overwrites with a checksum (fault-4 and checksum lines)
- Use hosted Opus 5.5 instead of the local model (agent-backend lines)
- Whether the answer is believable: as a reproducible comparison with
  observed weather, yes; as an operational forecast, untested
  (believability line)

### SDK audit of our repo: findings and our assessment

Auditor output, verbatim in `reports/audit.jsonl`, from
`env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl` on
`8450800`, 2026-11-24. Verdict: leakage `none`, `temporal_ok`,
`baseline_reported`, `reproducible`, confidence `high`. Two findings:

1. *Auditor:* same-day observed weather predicts same-day `cnt`. Not
   leakage (`check_identity` clean), but it assumes perfect weather
   knowledge, so the scores are upper bounds. **Our assessment:
   substantive, accepted.** It limits what the numbers mean for a deployed
   forecaster. It is stated at the top of this report and weighs in
   Exercise 5. No number changes.
2. *Auditor:* README said `make test` runs 14 tests; the suite runs 22.
   **Our assessment: cosmetic doc drift, fixed.** README now says `make
   test` runs the verification suite, and was updated to the hosted setup.
