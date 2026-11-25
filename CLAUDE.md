# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make all` - `make data`, `make features`, `make train` in order;
  reproduces the headline metrics in `reports/metrics.json`
- `make test` - pytest; run this before claiming anything works
- `/seed-fault <forbidden-column|rolling-leakage|weather-guard>` - one
  seeded-fault experiment: inject, capture hook and red tests, revert, record
- After each checkpoint, update `docs/RUBRIC_CHECKLIST.md`; tick a box only
  with a cited file, commit, or recorded output

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `FORBIDDEN` in `src/config.py`
  lists every excluded column with its reason. Derive feature lists from
  `FORBIDDEN`; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`.
  Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
- Any new lag or rolling feature must be built on a gap-free calendar
  index (`src.features.reindex_to_calendar`) and must `.shift(1)` before
  it aggregates. Add a test for it in `tests/test_leakage.py`.
- `cnt_std_7` is the population std (`ddof=0`, not pandas' default
  `ddof=1`) of `cnt` over the seven prior calendar days, d-7..d-1.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) alongside every model. A negative R^2 is a finding, not a bug
  to hide.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Keep pipeline stages runnable with `python -m src.<module>`.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- The mirror in `DATA_URL` is missing 2011-03-10. It is NOT the UCI file:
  728 rows from 2011-01-03, not 731 from 2011-01-01.
- `weather` uses the labels `GOOD` / `MISTY` / `BAD`, not the UCI codes 1-4.
- A `load_raw()` checksum mismatch means the raw CSV changed. Investigate,
  then restore the trusted file; never edit `RAW_SHA256` to match.
- Ridership grew ~65% from 2011 to 2012. "Trees cannot extrapolate past
  2011 levels" is an untested explanation for hgb's failure, not a result;
  the headline must follow the measured comparisons with both baselines.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set. Expect it in
  any residual plot.
