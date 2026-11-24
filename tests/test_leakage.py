"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import pandas as pd
import pytest

from src.config import FORBIDDEN, TARGET
from src.features import build_features, encode_weather, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


def test_lags_are_true_calendar_lags(feats):
    """cnt_lag_1 for date d must equal cnt on d-1, in calendar days."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_1.items():
        prev = date - pd.Timedelta(days=1)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


def test_rolling_mean_excludes_today(feats):
    """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
    by_date = feats.set_index("dteday")[TARGET]
    date = feats.dteday.iloc[200]
    window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
    missing = [d.date() for d in window if d not in by_date.index]
    assert not missing, f"reference window for {date.date()} has gaps: {missing}"
    expected = sum(by_date[d] for d in window) / 7
    assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)


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

    assert feats.set_index("dteday").cnt_std_7[pd.Timestamp("2011-02-01")] == pytest.approx(expected)


def test_unknown_weather_label_is_rejected():
    """An unmapped label must raise, not become a NaN that dropna() deletes.
    The raw data only has known labels, so without this test nothing would
    notice if the guard in encode_weather were removed."""
    labels = pd.Series(["GOOD", "UNSEEN", "BAD"])
    with pytest.raises(ValueError, match=r"unmapped weather labels: \['UNSEEN'\]"):
        encode_weather(labels)


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique
