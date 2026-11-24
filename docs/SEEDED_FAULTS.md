# Seeded faults

## Feature test before implementation

Feature: `cnt_std_7`, the population standard deviation (ddof=0) of `cnt` over
the seven calendar days strictly before the prediction date.

Availability: for prediction date d, the feature uses only `cnt` on d-7..d-1.
Those counts are all observed before d, so nothing measured on or after d is used.

Test: `tests/test_leakage.py::test_rolling_std_excludes_today`. For 2011-02-01,
the raw counts for 2011-01-25..31 are [1985, 506, 431, 1167, 1098, 1096, 1501],
checked against `data/raw/bike_daily.csv`. Mean = 1112, sum of squared
deviations = 1,747,924, variance = 249,703.43, so expected sigma = 499.70.

The test fails because `src/features.py` does not yet build `cnt_std_7`. The
raw-count check passes and all 14 existing tests pass.

Command:

```
$ make test
python -m pytest tests/ -q
.........F.....                                                          [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_std_excludes_today ________________________

feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 28 columns]

    def test_rolling_std_excludes_today(feats):
        """cnt_std_7 on 2011-02-01 is the population std (ddof=0) of cnt over
        2011-01-25..2011-01-31 -- the 7 calendar days strictly before it.
        Expected value is computed from literal counts, not from pandas."""
        window_counts = [1985, 506, 431, 1167, 1098, 1096, 1501]  # Jan 25..31
    
        raw = load_raw().set_index("dteday")[TARGET]
        window = pd.date_range("2011-01-25", "2011-01-31", freq="D")
        assert [raw[d] for d in window] == window_counts
    
        mean = sum(window_counts) / len(window_counts)
        squared_devs = [(x - mean) ** 2 for x in window_counts]
        expected = (sum(squared_devs) / len(window_counts)) ** 0.5  # ddof=0, ~499.70
    
>       assert feats.set_index("dteday").cnt_std_7[pd.Timestamp("2011-02-01")] == pytest.approx(expected)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_leakage.py:74: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self =             instant  season      yr  ... cnt_lag_1 cnt_lag_7   cnt_roll_7
dteday                               ...    ... 1787.0  1530.142857
2012-12-31    731.0  WINTER  2012.0  ...    1796.0     920.0  1531.428571

[714 rows x 27 columns]
name = 'cnt_std_7'

    @final
    def __getattr__(self, name: str):
        """
        After regular attribute access, try looking up the name
        This allows simpler access to columns for interactive use.
        """
        # Note: obj.x will always call obj.__getattribute__('x') prior to
        # calling obj.__getattr__('x').
        if (
            name not in self._internal_names_set
            and name not in self._metadata
            and name not in self._accessors
            and self._info_axis._can_hold_identifiers_and_holds_name(name)
        ):
            return self[name]
>       return object.__getattribute__(self, name)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: 'DataFrame' object has no attribute 'cnt_std_7'. Did you mean: 'cnt_lag_7'?

.venv/lib/python3.12/site-packages/pandas/core/generic.py:6194: AttributeError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_std_excludes_today - AttributeErro...
1 failed, 14 passed in 1.51s
make: *** [Makefile:16: test] Error 1
```

## Unclassified raw column rejected

Guard: `assert_all_columns_classified` in `tests/test_contract.py`, used by
`test_raw_columns_are_all_classified`. Allowed columns: `CLASSIFIED_RAW_COLS` in
`src/config.py`, typed out by hand and never taken from the CSV header, dtypes,
or `feature_columns()`.

Seeded fault: add a numeric column `surge_index` to an in-memory copy of the raw
DataFrame. `data/raw/bike_daily.csv` is not modified (sha256 a6bed157... before
and after). Without the guard, `feature_columns()` passes the new column to the
model, as the first output line shows.

Command (from the repo root):

```
$ python - <<EOF
from src.features import build_features, feature_columns
from src.ingest import load_raw
from tests.test_contract import assert_all_columns_classified

raw = load_raw()
tampered = raw.copy()            # in memory; data/raw/bike_daily.csv untouched
tampered["surge_index"] = 1.0    # unexpected numeric column
print("feature_columns would include it:",
      "surge_index" in feature_columns(build_features(tampered)))
assert_all_columns_classified(raw)
print("real raw data: all", len(raw.columns), "columns classified")
assert_all_columns_classified(tampered)
EOF
feature_columns would include it: True
real raw data: all 18 columns classified
Traceback (most recent call last):
  File "<stdin>", line 12, in <module>
  File "/home/ytandon/dsc180-methodology/bikeshare-open/tests/test_contract.py", line 37, in assert_all_columns_classified
    assert not unclassified, (
           ^^^^^^^^^^^^^^^^
AssertionError: unclassified raw columns: ['surge_index']; give each a role in src/config.py (DATE_COL, PREDICTOR_INPUT_COLS, or FORBIDDEN)
exit=1
```

## Fault: forbidden-column

- Date: 2026-11-24, run with `/seed-fault forbidden-column`
- Starting commit: `040ee64` (clean tree; pre-check `make test`: 19 passed in 1.49s, exit=0)
- Evidence directory: `/tmp/seed-fault-forbidden-column-20261124T125934-LGYN`
- Raw CSV sha256 before: `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`; after repair: `sha256sum -c` printed `data/raw/bike_daily.csv: OK`

### Change

One `Edit` to `src/features.py`, which admits `casual` through `feature_columns()`.

```diff
diff --git a/src/features.py b/src/features.py
index 3a3c96e..fd19ff9 100644
--- a/src/features.py
+++ b/src/features.py
@@ -83,7 +83,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN or c == "casual"]
 
 
 if __name__ == "__main__":
```

`git diff --numstat -- src/`:

```
1	1	src/features.py
```

### Automatic hook feedback (PostToolUse)

Shown by Claude Code right after the seeding `Edit`. Copied verbatim. Exit code: 2, inferred from the blocking-error report (Claude Code does not display it).

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /home/ytandon/dsc180-methodology/bikeshare-open/src/features.py:

feats =         dteday  instant  season      yr mnth  ... weather_severity cnt_lag_1  cnt_lag_7   cnt_roll_7    cnt_std_7
0   ...31.0  WINTER  2012.0  DEC  ...              1.0    1796.0      920.0  1531.428571   821.327646

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'mnth', ...})

tests/test_leakage.py:31: AssertionError
=============================================== short test summary info ================================================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in feature set: {'casual'}
1 failed, 8 passed in 0.43s
```

### Manual hook diagnostic (run by hand, not the automatic trigger)

Run while the fault was in place by piping a synthetic payload into the hook script. Exit code measured: `exit=` is the last line.

```
$ printf '{"tool_input":{"file_path":"%s"}}' "$PWD/src/features.py" \
    | CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/check_leakage.sh; echo "exit=$?"
Leakage tests failed after editing /home/ytandon/dsc180-methodology/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7    cnt_std_7
0   2011-01-10     10.0  WINTER  ...     134....142857   820.919420
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571   821.327646

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'mnth', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 8 passed in 0.44s
exit=2
```

### Red test output

As predicted, only `test_no_forbidden_features` went red. `make` exits 2 when a recipe fails.

```
$ make test
python -m pytest tests/ -q
........F..........                                                      [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7    cnt_std_7
0   2011-01-10     10.0  WINTER  ...     134....142857   820.919420
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571   821.327646

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'mnth', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 18 passed in 1.56s
make: *** [Makefile:16: test] Error 1
exit=2
```

### Repair

Counting convention: we count from the end of evidence capture to the first fully green `make test`, and we do not count conversational turns. A repair tool call is any tool call in that span. A repair cycle is one attempted edit to `src/` followed by one `make test`. The agent seeded this fault itself, so both numbers are lower bounds, not a measure of blind diagnosis.

- Repair tool calls: **2** (1 `Edit` reversing the seeded line; 1 Bash verification running `make test`)
- Repair cycles: **1**
- Automatic hook after the repair `Edit`: silent (no feedback appeared)
- `git diff --quiet -- src/`: printed `src/ identical to HEAD`

```
$ make test
19 passed in 1.38s
exit=0
```

## Fault: rolling-leakage

- Date: 2026-11-24, run with `/seed-fault rolling-leakage`
- Starting commit: `226ddae` (clean tree; pre-check `make test`: 19 passed in 1.55s, exit=0)
- Evidence directory: `/tmp/seed-fault-rolling-leakage-20261124T130334-mGNN`
- Raw CSV sha256 before: `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`; after repair: `sha256sum -c` printed `data/raw/bike_daily.csv: OK`

### Change

One `Edit` to `src/features.py`, which removes the `.shift(1)` before the `cnt_roll_7` rolling mean so each window includes the day being predicted.

```diff
diff --git a/src/features.py b/src/features.py
index 3a3c96e..010b64b 100644
--- a/src/features.py
+++ b/src/features.py
@@ -73,7 +73,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(WEEK_DAYS)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(WEEK_DAYS).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(WEEK_DAYS).mean()
     # Population std (ddof=0); pandas defaults to the sample std (ddof=1).
     out["cnt_std_7"] = out[TARGET].shift(1).rolling(WEEK_DAYS).std(ddof=0)
 
```

`git diff --numstat -- src/`:

```
1	1	src/features.py
```

### Automatic hook feedback (PostToolUse)

Shown by Claude Code right after the seeding `Edit`. Copied verbatim. Exit code: 2, inferred from the blocking-error report (Claude Code does not display it).

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /home/ytandon/dsc180-methodology/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
======================================================================= short test summary info ========================================================================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
1 failed, 8 passed in 0.46s
```

### Manual hook diagnostic (run by hand, not the automatic trigger)

Run while the fault was in place by piping a synthetic payload into the hook script. Exit code measured: `exit=` is the last line.

```
$ printf '{"tool_input":{"file_path":"%s"}}' "$PWD/src/features.py" \
    | CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/check_leakage.sh; echo "exit=$?"
Leakage tests failed after editing /home/ytandon/dsc180-methodology/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 8 passed in 0.40s
exit=2
```

### Red test output

As predicted, only `test_rolling_mean_excludes_today` went red. `make` exits 2 when a recipe fails.

```
$ make test
python -m pytest tests/ -q
...........F.......                                                      [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7    cnt_std_7
0   2011-01-10     10.0  WINTER  ...     134....428571   820.919420
713 2012-12-31    731.0  WINTER  ...      920.0  1789.857143   821.327646

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 18 passed in 1.38s
make: *** [Makefile:16: test] Error 1
exit=2
```

### Repair

Counting convention: we count from the end of evidence capture to the first fully green `make test`, and we do not count conversational turns. A repair tool call is any tool call in that span. A repair cycle is one attempted edit to `src/` followed by one `make test`. The agent seeded this fault itself, so both numbers are lower bounds, not a measure of blind diagnosis.

- Repair tool calls: **2** (1 `Edit` restoring `.shift(1)`; 1 Bash verification running `make test`)
- Repair cycles: **1**
- Automatic hook after the repair `Edit`: silent (no feedback appeared)
- `git diff --quiet -- src/`: printed `src/ identical to HEAD`

```
$ make test
19 passed in 1.25s
exit=0
```

## Fault: weather-guard

- Date: 2026-11-24, run with `/seed-fault weather-guard`
- Starting commit: `6f69ea5` (clean tree; pre-check `make test`: 19 passed in 1.37s, exit=0)
- Evidence directory: `/tmp/seed-fault-weather-guard-20261124T130651-9mzx`
- Raw CSV sha256 before: `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`; after repair: `sha256sum -c` printed `data/raw/bike_daily.csv: OK`

### Change

One `Edit` to `src/features.py` deleted the `if unknown:` / `raise ValueError(...)` guard in `encode_weather`. Without it, an unmapped label silently becomes NaN. Deviation from the skill: the `Edit` also included the unchanged line `unknown = set(known.unique()) - set(WEATHER_ORDER)` as context in both `old_string` and `new_string`, so the strings were not literally the table's. The numstat below shows the net change is exactly the required 2 deletions and 0 additions. The repair `Edit` used the same context line.

```diff
diff --git a/src/features.py b/src/features.py
index 3a3c96e..debee3e 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

`git diff --numstat -- src/`:

```
0	2	src/features.py
```

### Automatic hook feedback (PostToolUse)

Shown by Claude Code right after the seeding `Edit`. Copied verbatim. Exit code: 2, inferred from the blocking-error report (Claude Code does not display it).

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /home/ytandon/dsc180-methodology/bikeshare-open/src/features.py:
......F..                                                                                                                                                        [100%]
=============================================================================== FAILURES ===============================================================================
________________________________________________________________ test_unknown_weather_label_is_rejected ________________________________________________________________

    def test_unknown_weather_label_is_rejected():
        """An unmapped label must raise, not become a NaN that dropna() deletes.
        The raw data only has known labels, so without this test nothing would
        notice if the guard in encode_weather were removed."""
        labels = pd.Series(["GOOD", "UNSEEN", "BAD"])
>       with pytest.raises(ValueError, match=r"unmapped weather labels: \['UNSEEN'\]"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
======================================================================= short test summary info ========================================================================
FAILED tests/test_leakage.py::test_unknown_weather_label_is_rejected - Failed: DID NOT RAISE ValueError
1 failed, 8 passed in 0.50s
```

### Manual hook diagnostic (run by hand, not the automatic trigger)

Run while the fault was in place by piping a synthetic payload into the hook script. Exit code measured: `exit=` is the last line.

```
$ printf '{"tool_input":{"file_path":"%s"}}' "$PWD/src/features.py" \
    | CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/check_leakage.sh; echo "exit=$?"
Leakage tests failed after editing /home/ytandon/dsc180-methodology/bikeshare-open/src/features.py:
......F..                                                                [100%]
=================================== FAILURES ===================================
____________________ test_unknown_weather_label_is_rejected ____________________

    def test_unknown_weather_label_is_rejected():
        """An unmapped label must raise, not become a NaN that dropna() deletes.
        The raw data only has known labels, so without this test nothing would
        notice if the guard in encode_weather were removed."""
        labels = pd.Series(["GOOD", "UNSEEN", "BAD"])
>       with pytest.raises(ValueError, match=r"unmapped weather labels: \['UNSEEN'\]"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_unknown_weather_label_is_rejected - Failed...
1 failed, 8 passed in 0.44s
exit=2
```

### Red test output

As predicted, only `test_unknown_weather_label_is_rejected` went red (`DID NOT RAISE ValueError`). `make` exits 2 when a recipe fails. This test was added in `6fb1c66` for exactly this fault: the raw data has only known labels, so every other test passes with the guard removed.

```
$ make test
python -m pytest tests/ -q
.............F.....                                                      [100%]
=================================== FAILURES ===================================
____________________ test_unknown_weather_label_is_rejected ____________________

    def test_unknown_weather_label_is_rejected():
        """An unmapped label must raise, not become a NaN that dropna() deletes.
        The raw data only has known labels, so without this test nothing would
        notice if the guard in encode_weather were removed."""
        labels = pd.Series(["GOOD", "UNSEEN", "BAD"])
>       with pytest.raises(ValueError, match=r"unmapped weather labels: \['UNSEEN'\]"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_unknown_weather_label_is_rejected - Failed...
1 failed, 18 passed in 1.47s
make: *** [Makefile:16: test] Error 1
exit=2
```

### Repair

Counting convention: we count from the end of evidence capture to the first fully green `make test`, and we do not count conversational turns. A repair tool call is any tool call in that span. A repair cycle is one attempted edit to `src/` followed by one `make test`. The agent seeded this fault itself, so both numbers are lower bounds, not a measure of blind diagnosis.

- Repair tool calls: **2** (1 `Edit` restoring the two guard lines; 1 Bash verification running `make test`)
- Repair cycles: **1**
- Automatic hook after the repair `Edit`: silent (no feedback appeared)
- `git diff --quiet -- src/`: printed `src/ identical to HEAD`

```
$ make test
19 passed in 1.45s
exit=0
```
