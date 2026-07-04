"""Shared utility namespace for the repository.

The legacy implementation lives in io_utils.py to keep backward compatibility
with existing modules. New code should import from scripts/utils.py. This module
overrides table writing so every CSV output also gets a JSON records companion.
"""

from pathlib import Path

import pandas as pd

from io_utils import *  # noqa: F401,F403


def write_dataframe_json(df, path):
    """Save a DataFrame as JSON records."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if df is None or df.empty:
        path.write_text("[]\n", encoding="utf-8")
    else:
        df.to_json(path, orient="records", force_ascii=False, indent=2)
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return path


def write_csv(df, path):
    """Save a DataFrame as CSV and create the JSON records companion."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if df is None:
        df = pd.DataFrame()
    df.to_csv(path, index=False, encoding="utf-8")
    write_dataframe_json(df, path.with_suffix(".json"))
    return path
