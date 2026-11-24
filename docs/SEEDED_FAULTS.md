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

## Fault 4: Bash raw-data copy

- Date: 2026-11-24, run by hand outside `/seed-fault`, using Claude's Bash tool
- Starting commit: `a0d7ab1`. The tree was clean and `make test` printed `19 passed in 1.39s` (exit 0) before the experiment.
- Evidence directory: `/tmp/fault4-raw-cp-20261124T131120-dL9J`
- Permission outcome: the `cp` was **not denied**. It ran and printed `cp exit=0`. No settings or permissions were changed for this experiment.

### Preparation (separate Bash call, before any change)

The original was backed up byte for byte with `cp -p data/raw/bike_daily.csv "$T/bike_daily.backup.csv"` (`backup cp exit=0`), then checked:

```
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  /tmp/fault4-raw-cp-20261124T131120-dL9J/bike_daily.backup.csv
backup byte-identical
```

`1.032178` appears exactly once in the file, on line 31 (2011-02-01).

### The experiment (one Bash call)

The `EXIT` trap is installed before the raw file is touched, and the original bytes are also restored explicitly before the call ends. Exact command:

```bash
cd /home/ytandon/dsc180-methodology/bikeshare-open || exit 1
T=/tmp/fault4-raw-cp-20261124T131120-dL9J; RAW=data/raw/bike_daily.csv; BK="$T/bike_daily.backup.csv"; ALT="$T/bike_daily.altered.csv"
exec > >(tee "$T/experiment_log.txt") 2>&1
echo "== 1. build altered copy in $T (raw file untouched) =="
sed '31s/,"TUE",1\.032178,/,"TUE",1.042178,/' "$BK" > "$ALT"; echo "sed exit=$?"
echo "rows: backup=$(wc -l < "$BK") altered=$(wc -l < "$ALT")"
echo "header identical: $(cmp -s <(head -1 "$BK") <(head -1 "$ALT") && echo yes || echo NO)"
echo "differing bytes (cmp -l):"; cmp -l "$BK" "$ALT"
echo "diff backup altered:"; diff "$BK" "$ALT"; echo "diff exit=$?"
echo "== 2. install restore trap BEFORE touching raw =="
trap 'cp "$BK" "$RAW"; echo "[EXIT trap] restore cp exit=$?"; sha256sum "$RAW"' EXIT
trap -p EXIT
echo "== 3. the fault =="
echo '$ cp "$ALT" data/raw/bike_daily.csv'
cp "$ALT" "$RAW"; echo "cp exit=$?"
echo "original hash: $(sha256sum "$BK" | cut -d' ' -f1)"
echo "raw hash now : $(sha256sum "$RAW" | cut -d' ' -f1)"
echo "git diff of raw while altered:"; git --no-pager diff --word-diff=plain -- "$RAW"; git diff --numstat -- "$RAW"
echo "== 4. make test with altered raw =="
make test > "$T/make_test_altered.txt" 2>&1; echo "exit=$?" >> "$T/make_test_altered.txt"
cat "$T/make_test_altered.txt"
echo "== 5. restore and verify =="
cp "$BK" "$RAW"; echo "restore cp exit=$?"
cmp "$BK" "$RAW" && echo "cmp: raw byte-identical to backup"
echo "raw hash restored: $(sha256sum "$RAW" | cut -d' ' -f1)"
git diff --quiet -- "$RAW" && echo "git diff: no changes to $RAW"
make test > "$T/make_test_restored.txt" 2>&1; echo "exit=$?" >> "$T/make_test_restored.txt"
tail -2 "$T/make_test_restored.txt"
echo "== end of call; EXIT trap runs next =="
```

### Output (verbatim, from `experiment_log.txt`)

The data difference is the single byte at offset 3616 (`cmp -l` prints octal: `63` is `'3'`, `64` is `'4'`). That byte changes `temp` on 2011-02-01 from `1.032178` to `1.042178`. Row count (729 lines), header, columns, and dates are unchanged.

```
== 1. build altered copy in /tmp/fault4-raw-cp-20261124T131120-dL9J (raw file untouched) ==
sed exit=0
rows: backup=729 altered=729
header identical: yes
differing bytes (cmp -l):
 3616  63  64
diff backup altered:
31c31
< 32,"2011-02-01","WINTER","2011","FEB","N","TUE",1.032178,23.97402,82.9565,3.565271,47,1313,1360,"Y","MISTY",31,1096
---
> 32,"2011-02-01","WINTER","2011","FEB","N","TUE",1.042178,23.97402,82.9565,3.565271,47,1313,1360,"Y","MISTY",31,1096
diff exit=1
== 2. install restore trap BEFORE touching raw ==
trap -- 'cp "$BK" "$RAW"; echo "[EXIT trap] restore cp exit=$?"; sha256sum "$RAW"' EXIT
== 3. the fault ==
$ cp "$ALT" data/raw/bike_daily.csv
cp exit=0
original hash: a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
raw hash now : cae60e1ce7bc3229d1019db51930e4a88911978264206bb0abe8c187157a92ac
git diff of raw while altered:
diff --git a/data/raw/bike_daily.csv b/data/raw/bike_daily.csv
index cc36935..a4c3de6 100644
--- a/data/raw/bike_daily.csv
+++ b/data/raw/bike_daily.csv
@@ -28,7 +28,7 @@
29,"2011-01-29","WINTER","2011","JAN","N","SAT",1.236534,23.212284,65.1739,9.739455,123,975,1098,"N","GOOD",28,431
30,"2011-01-30","WINTER","2011","JAN","N","SUN",2.176534,24.510948,72.2174,4.9568342,140,956,1096,"N","GOOD",29,1167
31,"2011-01-31","WINTER","2011","JAN","N","MON",0.499150999999999,22.3325,60.375,12.541864,42,1459,1501,"Y","MISTY",30,1098
[-32,"2011-02-01","WINTER","2011","FEB","N","TUE",1.032178,23.97402,82.9565,3.565271,47,1313,1360,"Y","MISTY",31,1096-]{+32,"2011-02-01","WINTER","2011","FEB","N","TUE",1.042178,23.97402,82.9565,3.565271,47,1313,1360,"Y","MISTY",31,1096+}
33,"2011-02-02","WINTER","2011","FEB","N","WED",4.22,24.650178,77.5417,17.708636,72,1454,1526,"Y","MISTY",32,1501
34,"2011-02-03","WINTER","2011","FEB","N","THU",0.786979,22.047852,43.7826,18.609384,61,1489,1550,"Y","GOOD",33,1360
35,"2011-02-04","WINTER","2011","FEB","N","FRI",1.931288,23.771958,58.5217,8.565213,88,1620,1708,"Y","MISTY",34,1526
1	1	data/raw/bike_daily.csv
== 4. make test with altered raw ==
python -m pytest tests/ -q
...................                                                      [100%]
19 passed in 1.44s
exit=0
== 5. restore and verify ==
restore cp exit=0
cmp: raw byte-identical to backup
raw hash restored: a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
git diff: no changes to data/raw/bike_daily.csv
19 passed in 1.38s
exit=0
== end of call; EXIT trap runs next ==
[EXIT trap] restore cp exit=0
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
```

### Automatic hook feedback

**Did not appear.** Claude Code showed no hook message after this Bash call, and none after the preparation or verification calls either.

### Why the hook was silent, and why the suite stayed green

- **Matcher.** `.claude/settings.json` registers `check_leakage.sh` under `PostToolUse` with `"matcher": "Edit|Write"`. The matcher selects by tool name, so a `Bash` tool call never invokes the hook, whatever the command does. Even when it is invoked, the script exits 0 for any path not matching `*src/*.py`. The permission rules `Write(./data/raw/**)` and `Edit(./data/raw/**)` are also scoped to those two tools, so they do not stop a `cp` run through Bash. What we saw matches this: `cp exit=0`, no denial, no hook output.
- **Tests.** With the altered file in place, `make test` printed `19 passed` and `exit=0`. The change kept the row count, columns, dates, weather labels, and every `cnt` value, so `load_raw()`'s shape checks, the column classification, the calendar and row-loss checks, and the hand-computed `cnt` windows all still hold. No test looks at the contents of `temp`. A silently corrupted raw file passes the whole suite. A `Stop` hook that only runs `make test` would not have caught this either.

### What would catch it: a checksum check when the data is loaded

Record the expected digest once in `src/config.py`, e.g. `RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"`. Have `load_raw()` hash the file bytes with `hashlib.sha256` before parsing, and raise `ValueError` on a mismatch, naming the expected and actual digests. Every stage reads the data through `load_raw()`: `make data`, `make features`, `make train`, and the `raw`/`feats` fixtures in both test files. So the altered file above (digest `cae60e1c...`) would stop every pipeline stage and turn `make test` red, however the file was changed: `cp`, an editor, or a fresh download. It does not stop the write; it stops the bad bytes from producing a number. It uses only the standard library (`hashlib`), so no new dependency. **This defence is not implemented here. It is scheduled for the next checkpoint.**

Other catches the rubric names: a `PreToolUse` hook on `Bash` that blocks commands writing under `data/raw/`, which only sees commands that name the path; or a filesystem permission (a read-only raw file).

### Restoration

Inside the same call: `restore cp exit=0`, `cmp` byte-identical to the backup, full hash `a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`, no `git diff` for the raw CSV, and `make test` printed `19 passed` with `exit=0`. The `EXIT` trap then ran its own restore and printed the same hash. A separate later Bash call confirmed the same full hash, byte equality with the backup, and `git status --porcelain` empty.
