"""Shared helpers: CAGR, formatting, data loaders."""

import pandas as pd
import numpy as np
from pathlib import Path
from scripts.config import DATA_RAW, DATA_PROCESSED


def cagr(start_val: float, end_val: float, years: int) -> float:
    """Compound annual growth rate."""
    if start_val <= 0 or years <= 0:
        return np.nan
    return (end_val / start_val) ** (1 / years) - 1


def rolling_cagr(series: pd.Series, window: int = 5) -> pd.Series:
    """Rolling CAGR over a fixed window of years."""
    result = pd.Series(np.nan, index=series.index)
    for i in range(window, len(series)):
        result.iloc[i] = cagr(series.iloc[i - window], series.iloc[i], window)
    return result


def fmt_currency(val: float, decimals: int = 0) -> str:
    """Format as US currency string."""
    if pd.isna(val):
        return "N/A"
    return f"${val:,.{decimals}f}"


def fmt_pct(val: float, decimals: int = 2) -> str:
    """Format as percentage string."""
    if pd.isna(val):
        return "N/A"
    return f"{val * 100:.{decimals}f}%"


def load_tuition() -> pd.DataFrame:
    """Load raw tuition data."""
    return pd.read_csv(DATA_RAW / "tuition_costs.csv")


def load_cpi() -> pd.DataFrame:
    """Load CPI data."""
    return pd.read_csv(DATA_RAW / "cpi_annual.csv")


def load_cleaned() -> pd.DataFrame:
    """Load cleaned cost data."""
    return pd.read_csv(DATA_PROCESSED / "costs_cleaned.csv")


def load_real() -> pd.DataFrame:
    """Load inflation-adjusted cost data."""
    return pd.read_csv(DATA_PROCESSED / "costs_real_dollars.csv")


def load_projections() -> pd.DataFrame:
    """Load projection data."""
    return pd.read_csv(DATA_PROCESSED / "projections.csv")
