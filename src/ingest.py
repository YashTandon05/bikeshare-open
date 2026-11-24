"""Stage 1: fetch the raw dataset and assert its checksum and shape.

Run: python -m src.ingest
"""
import hashlib
import sys
import urllib.request

import pandas as pd

from src.config import DATA_URL, RAW, RAW_SHA256

EXPECTED_MIN_ROWS = 700
REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


def download(force: bool = False) -> None:
    if RAW.exists() and not force:
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, RAW)


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw() -> pd.DataFrame:
    """Read RAW only if its bytes match RAW_SHA256.

    Every stage and every test fixture loads data through here, so a raw file
    changed by any route (editor, `cp` from Bash, a drifting mirror) stops the
    pipeline instead of quietly moving the numbers. This detects corruption
    on load; it cannot stop the write itself.
    """
    actual = file_sha256(RAW)
    if actual != RAW_SHA256:
        raise ValueError(
            f"raw data checksum mismatch for {RAW}: expected sha256 {RAW_SHA256}, "
            f"got {actual}. Restore the trusted file (git checkout -- "
            "data/raw/bike_daily.csv); do not edit RAW_SHA256 to match."
        )
    df = pd.read_csv(RAW, parse_dates=["dteday"])
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
    if len(df) < EXPECTED_MIN_ROWS:
        raise ValueError(f"raw data has only {len(df)} rows; expected >= {EXPECTED_MIN_ROWS}")
    return df


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    df = load_raw()
    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}")
