# Bikeshare demand: methodology report

> **Status: complete draft for team review.** Every number is copied from a
> committed JSON file named next to it. The conclusions in *Headline
> finding* and *Exercise 5* are **proposed** and await our sign-off.
> Still pending outside this report: the peer `/leakage-auditor` audit
> (`docs/AUDIT.md`), the fresh-clone reproduction check, and merging the
> `sdk-audit` branch (see Attribution).

**Prediction-time assumption, applies throughout.** The weather inputs
(`temp`, `atemp`, `hum`, `windspeed`, `weather`) are the day's *observed*
values, so the ridge and hgb results are **conditional on observed
weather** for the day being forecast. How they would perform with
*forecast* weather, as an operational forecaster would have, is
**untested**. The lag features assume yesterday's final count is known
before today is forecast. The two baselines (training mean, persistence)
use no weather. "Average absolute error" below is the mean absolute error
(MAE), in rides per day.

## Results

Target: daily total rides `cnt` (the assignment's target). Temporal split:
train 2011 (348 rows), validation 2012-01-01 to 2012-06-30 (182 rows), test
H2 2012 (184 rows). "Before" is the starter feature set (14 features,
`reports/metrics_before_feature.json`, frozen before feature work). "After"
adds `cnt_std_7`, the population standard deviation of `cnt` over the seven
calendar days before each date (15 features, `reports/metrics.json`,
produced by `make all`).

| model | feature set | valid R² | valid avg. absolute error | test R² | test avg. absolute error |
|---|---|---|---|---|---|
| baseline_mean | before (14) | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after (15, + cnt_std_7) | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before (14) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after (15, + cnt_std_7) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before (14) | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after (15, + cnt_std_7) | 0.7224 | 700.4 | 0.6356 | 840.3 |
| hgb | before (14) | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after (15, + cnt_std_7) | 0.0977 | 1381.6 | -0.6959 | 2108.4 |

The baselines do not use `cnt_std_7`, so their rows are identical before
and after.

**Evaluation history.** We kept `cnt_std_7` on validation alone (ridge
+0.0749 R², hgb -0.1208). The default pipeline computes test metrics on
every run, but no feature, transformation or model choice used them. The
final look was planned and recorded before it ran: `make all` and
`python -m src.train --final-target-test`, run once each on 2026-11-24 at
commit `9315d78`, after the evaluation code was committed. `make all`
reproduced `reports/metrics.json` byte for byte.

## Headline finding

A tree model trained on 2011 fails on 2012, while a linear model succeeds
but barely beats "yesterday again". Ridership grew so much that the
training-mean baseline (the 2011 average) scores test R² **-2.1441**, with
an average absolute error of **2847.7**. Ordinary hgb scores test R²
**-0.6959** (average absolute error **2108.4**). A negative R² means it does
worse than the test period's own mean, a number no forecaster has in
advance. That is not the same as losing to our training-mean baseline:
hgb still **beats** that baseline, but **substantially underperforms
persistence** (test R² **0.5099**, average absolute error **840.1**), which
predicts yesterday's count. Its failure fits trees being unable to
extrapolate past 2011 levels, but we did not test that cause. Ridge reaches
test R² **0.6356**, with an average absolute error (**840.3**) essentially
equal to persistence's. Adding `cnt_std_7` helped ridge on both splits
(test R² +0.0523, average absolute error -106.8) and hurt hgb on both (test
R² -0.1984, average absolute error +135.8); we kept it, on validation, for
ridge. The ridge and hgb results are conditional on observed same-day
weather; operational performance with forecast weather is untested.

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

| method | valid R² | valid avg. absolute error | test R² | test avg. absolute error |
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
  +1.1720 on test; average absolute error -495.8 and -1117.9.
- On validation it edged past persistence (R² +0.1135, average absolute
  error -14.8). **On test it did not:** 0.4761 vs 0.5099 R², 990.5 vs 840.1
  average absolute error. The small validation advantage, which we flagged
  as within noise and had no uncertainty estimate, did not hold up.
- It stays behind ridge on both splits.
- It **does not establish why** ordinary hgb fails. Extrapolation fits the
  pattern but was not tested directly.

**Defensible, or a way to win?** It is defensible as a method. It assumes
only what persistence and the lag features already assume: yesterday's
observed count is available before today is forecast. Like ridge and
ordinary hgb, its results are conditional on observed weather. It was a
structural choice (differencing), fixed before the run and not tuned. It
applies only one day ahead; further out, yesterday's count would itself be
a prediction. But it does not let gradient boosting compete. It rescues
hgb from failure, yet on test it loses to the simplest baseline, so we
would not adopt it.

## Exercise 5: ridge vs persistence

**Proposed position: on this evidence, ridge is not worth deploying over
persistence as a day-ahead forecaster for now.** On the 184 test days the
two have essentially the same average absolute error, **840.3 vs 840.1**
rides/day. Ridge's higher R² (**0.6356 vs 0.5099**) means about **25.6%
lower total squared error** on the same rows ((1-0.6356)/(1-0.5099) ≈ 0.744,
from the rounded R² values). These aggregates do not tell us which days or
which errors ridge improves, so we make no claim about where the gain
comes from. The advantage also shrank from validation, where ridge's
average absolute error was 700.4 vs 900.6 and its squared error about 49%
lower. Ridge's numbers are conditional on observed same-day weather, so its
performance with the forecast weather a deployed system would receive is
untested. Persistence uses yesterday's validated count, has no fitted
parameters, and needs no weather feed. We estimated no uncertainty: one
split of 184 test days, including Hurricane Sandy (2012-10-29, 22 rides).
Given equal average absolute error, an untested operational setting, and
no uncertainty estimate, persistence should remain the default. Ridge is a
candidate if a forecast-weather evaluation shows it keeps its squared-error
advantage and that advantage matters for the intended use.

## Attribution

**Models:** Claude Opus 5.5 (`claude-opus-5-5`, hosted; size not
published by Anthropic) for Yash Tandon's Claude Code work and the SDK
audit. That was a switch from the planned Sonnet 5.5 and from the starter's
local `bikeshare-coder` (`b033c19`, agent-backend lines in
`docs/DECISIONS.md`). Other models: ChatGPT for planning outside the repo,
and Grok 4.7 via OpenCode for the `sdk-audit` branch (pending merge, see
below). Not all team agent work used Opus.

**Contributors and tools.**

- **Yash Tandon:** made the methodological decisions below, including which
  suggestions from ChatGPT and from the Claude agent to adopt or reject.
  Reviewed every commit on this branch, ran the SDK audit, and approved or
  denied agent actions.
- **ChatGPT (OpenAI):** planning, explanations, and methodological
  suggestions, used outside the repository. Its suggestions were inputs;
  adopting or rejecting each was a human decision.
- **Claude Opus 5.5 via Claude Code**, interactively: wrote code, tests and
  documentation drafts under Yash Tandon's direction. It used the starter's
  PostToolUse leakage hook, the starter `/new-feature` skill, and our
  `/seed-fault` skill.
- **Claude Opus 5.5 via the Agent SDK** (`agent/audit.py`,
  `AUDIT_MODEL=opus`): audited this repo.
- **Pending merge of `sdk-audit` (`a38f682`, not on this branch):** credit
  **Issac Roy**, who changed `agent/audit.py` so one raised SDK run no
  longer aborts the batch, and added `tests/test_audit.py`. The work used
  **OpenCode with Grok 4.7**, not Opus, as recorded in that branch's
  `docs/DECISIONS.md` entry. Confirm this line against the merged entry.
- The starter's `/leakage-auditor` subagent has not been run yet: the peer
  audit is pending.

**Agent-generated files and functions** (Claude Opus 5.5 via Claude Code;
reviewed before each commit):

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
- Which columns to exclude, for three different reasons (starter lines and
  column-classification line):
  - **target leakage:** `casual` and `registered` (they sum exactly to `cnt`)
    and `cnt` itself
  - **unverified historical lag:** `cnt_2d_bfr`, a two-day lag shipped with
    the mirror whose alignment we could not check. It is not leakage.
  - **modeling reasons:** the time indexes `instant`, `yr`,
    `days_since_2011`, and the redundant calendar labels `season`, `mnth`,
    `weekday`
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

### SDK audit of our repo: auditor's wording vs our assessment

Run with `env AUDIT_MODEL=opus python agent/audit.py . --out
reports/audit.jsonl` on `8450800`, 2026-11-24. `reports/audit.jsonl` is
kept verbatim as generated. Its summary fields: `"leakage": "none"`,
`"temporal_ok": true`, `"baseline_reported": true`, `"reproducible":
true`, `"confidence": "high"`.

1. **Auditor (verbatim):** "Same-day observed weather (temp, atemp, hum,
   windspeed, weather) is used as a predictor of same-day cnt. Not target
   leakage (check_identity on all 15 features: clean), but it assumes
   perfect weather knowledge at forecast time." *Why it matters,
   verbatim:* "Reported valid/test scores are an upper bound relative to a
   real forecast that would only have a weather forecast; the write-up
   should state this assumption."
   **Our assessment: substantive, accepted with one qualification.** We
   agree it is not leakage and that the assumption must be stated; it is
   at the top of this report and weighs in Exercise 5. We do not adopt
   the "upper bound" wording, because we have not tested forecast weather.
   We say instead that the ridge and hgb results are conditional on
   observed weather and that operational performance is untested. No
   number changes.
2. **Auditor (verbatim):** "README says `make test` runs 14 tests; the
   suite actually runs 22 (22 passed)." *Why it matters, verbatim:* "Minor
   doc drift; a reader can't use the stated count to confirm the full
   suite ran."
   **Our assessment: cosmetic, fixed.** README now says `make test` runs
   the verification suite, with no count, and describes the hosted setup.
