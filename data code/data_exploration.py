# data_code/data_exploration.py
from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

REAL_ESTATE_VARS = [
    {"col": "Real_GDP_per_Capita_USD", "label": "GDP per Capita (USD)", "dir": +1},
    {"col": "Total_Population", "label": "Population", "dir": +1},
    {"col": "Population_Growth_Rate", "label": "Population Growth (%)", "dir": +1},
    {"col": "Net_Migration_Rate", "label": "Net Migration Rate", "dir": +1},
    {"col": "Unemployment_Rate_percent", "label": "Unemployment (%)", "dir": -1},
    {"col": "Public_Debt_percent_of_GDP", "label": "Public Debt (% of GDP)", "dir": -1},
]

_NUM_TOKEN = re.compile(r"-?\d+(?:\.\d+)?")

def _to_decimal(val) -> Decimal | None:
    """
    Parse messy numeric cells like '652,230 sq km', '12%', '', NaN, etc.
    Returns Decimal for safe formatting (no scientific notation).
    """
    if val is None:
        return None

    # pandas NaN
    try:
        if isinstance(val, float) and math.isnan(val):
            return None
    except Exception:
        pass

    # already numeric
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        try:
            return Decimal(str(val))
        except InvalidOperation:
            return None

    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None

    # strip quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    # remove thousands separators
    s = s.replace(",", "")

    m = _NUM_TOKEN.search(s)
    if not m:
        return None

    try:
        return Decimal(m.group(0))
    except InvalidOperation:
        return None


def _decimal_to_plain_str(d: Decimal, max_decimals: int = 12) -> str:
    """
    Convert Decimal to a plain (non-scientific) string.
    Trims trailing zeros and dot.
    """
    # quantize-ish without forcing fixed decimals:
    s = format(d, "f")  # never 'e'
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    # optional: keep it from being overly long
    if "." in s:
        whole, frac = s.split(".", 1)
        frac = frac[:max_decimals].rstrip("0")
        s = whole if frac == "" else f"{whole}.{frac}"
    return s


def compute_min_max(df: pd.DataFrame, variables=REAL_ESTATE_VARS) -> pd.DataFrame:
    rows = []
    for v in variables:
        col = v["col"]
        label = v.get("label", col)
        direction = v.get("dir")

        if col not in df.columns:
            rows.append(
                {"col": col, "label": label, "dir": direction, "min": None, "max": None, "note": "MISSING COLUMN"}
            )
            continue

        mn: Decimal | None = None
        mx: Decimal | None = None

        for raw in df[col].tolist():
            x = _to_decimal(raw)
            if x is None:
                continue
            mn = x if mn is None or x < mn else mn
            mx = x if mx is None or x > mx else mx

        rows.append(
            {
                "col": col,
                "label": label,
                "dir": direction,
                "min": (_decimal_to_plain_str(mn) if mn is not None else None),
                "max": (_decimal_to_plain_str(mx) if mx is not None else None),
                "note": "",
            }
        )

    return pd.DataFrame(rows)


def load_real_estate_view() -> pd.DataFrame:
    # project layout: data_curated/investor_views/real_estate_view.csv
    here = Path(__file__).resolve()
    project_root = here.parents[1]  # .../VISUALIZATION-PROJECT-GROUP-5
    csv_path = project_root / "data_curated" / "investor_views" / "real_estate_view.csv"
    return pd.read_csv(csv_path)


if __name__ == "__main__":
    df = load_real_estate_view()
    out = compute_min_max(df)

    print("\n=== REAL ESTATE min/max (plain numbers, no scientific notation) ===")
    print(out.to_string(index=False))

    # Save for your visualization tool
    here = Path(__file__).resolve()
    project_root = here.parents[1]
    save_path = project_root / "data_curated" / "investor_views" / "real_estate_min_max.csv"
    out.to_csv(save_path, index=False)
    print(f"\nSaved -> {save_path}")
