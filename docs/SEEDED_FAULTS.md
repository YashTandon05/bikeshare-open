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
