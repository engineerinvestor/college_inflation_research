"""
02_analyze.py: Compute per-school and group metrics for college cost inflation.

Run from project root:
    python -m scripts.02_analyze
"""

import json
import numpy as np
import pandas as pd

from scripts.config import (
    DATA_PROCESSED,
    DATA_RAW,
    HIST_START,
    HIST_END,
    IVY_SCHOOLS,
    IVY_PLUS_SCHOOLS,
)
from scripts.utils import cagr, rolling_cagr, fmt_pct

# ── Constants ───────────────────────────────────────────────────────────────
CAGR_YEARS = HIST_END - HIST_START  # 20
ROLLING_WINDOW = 5

CRISIS_YEARS = list(range(2008, 2011))   # 2008–2010 financial crisis
COVID_YEARS = [2020, 2021]              # COVID impact window


# ── Helpers ─────────────────────────────────────────────────────────────────

def _safe(val):
    """Convert numpy scalars / NaN to JSON-serialisable Python types."""
    if isinstance(val, float) and np.isnan(val):
        return None
    if isinstance(val, (np.floating, np.integer)):
        return val.item()
    return val


def _group_cagr_stats(cagr_values: list) -> dict:
    """Return mean / median / std dev for a list of CAGR values, ignoring NaN."""
    arr = np.array([v for v in cagr_values if v is not None], dtype=float)
    if len(arr) == 0:
        return {"mean": None, "median": None, "std_dev": None}
    return {
        "mean":    _safe(float(np.mean(arr))),
        "median":  _safe(float(np.median(arr))),
        "std_dev": _safe(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0),
    }


# ── Load data ────────────────────────────────────────────────────────────────

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned_path = DATA_PROCESSED / "costs_cleaned.csv"
    cpi_path = DATA_RAW / "cpi_annual.csv"

    costs = pd.read_csv(cleaned_path)
    cpi = pd.read_csv(cpi_path)

    # Normalise column names
    costs.columns = costs.columns.str.strip().str.lower()
    cpi.columns = cpi.columns.str.strip().str.lower()

    return costs, cpi


# ── CPI CAGR ─────────────────────────────────────────────────────────────────

def compute_cpi_cagr(cpi: pd.DataFrame) -> float:
    """20-year CPI CAGR from HIST_START to HIST_END."""
    cpi_indexed = cpi.set_index("year")["cpi_u"]

    start_val = float(cpi_indexed.loc[HIST_START])
    end_val = float(cpi_indexed.loc[HIST_END])

    return cagr(start_val, end_val, CAGR_YEARS)


# ── Per-school metrics ────────────────────────────────────────────────────────

def compute_school_metrics(costs: pd.DataFrame, cpi_cagr: float) -> dict:
    """Return a dict keyed by school name with all per-school metrics."""
    results = {}

    for school in costs["school"].unique():
        df = (
            costs[costs["school"] == school]
            .sort_values("year")
            .set_index("year")
        )

        # ── 20-year CAGRs ────────────────────────────────────────────────────
        def _point(col: str, yr: int):
            if yr in df.index and col in df.columns:
                return float(df.loc[yr, col])
            return np.nan

        tc_start = _point("total_cost", HIST_START)
        tc_end   = _point("total_cost", HIST_END)
        tf_start = _point("tuition_fees", HIST_START)
        tf_end   = _point("tuition_fees", HIST_END)

        cagr_total_cost   = cagr(tc_start, tc_end, CAGR_YEARS)
        cagr_tuition_fees = cagr(tf_start, tf_end, CAGR_YEARS)

        # ── Cumulative multiplier ────────────────────────────────────────────
        cum_multiplier = (tc_end / tc_start) if (tc_start > 0 and not np.isnan(tc_start)) else np.nan

        # ── Annual pct changes ───────────────────────────────────────────────
        if "total_cost" in df.columns:
            annual_pct = df["total_cost"].pct_change().dropna()
            min_pct_increase = _safe(float(annual_pct.min())) if not annual_pct.empty else None
            max_pct_increase = _safe(float(annual_pct.max())) if not annual_pct.empty else None
            min_pct_year     = _safe(int(annual_pct.idxmin())) if not annual_pct.empty else None
            max_pct_year     = _safe(int(annual_pct.idxmax())) if not annual_pct.empty else None
        else:
            annual_pct = pd.Series(dtype=float)
            min_pct_increase = max_pct_increase = min_pct_year = max_pct_year = None

        # ── 5-year rolling CAGRs for total_cost ─────────────────────────────
        if "total_cost" in df.columns:
            rolling = rolling_cagr(df["total_cost"], window=ROLLING_WINDOW).dropna()
            rolling_cagrs = {
                str(yr): _safe(float(val))
                for yr, val in rolling.items()
            }
        else:
            rolling_cagrs = {}

        # ── College premium ──────────────────────────────────────────────────
        college_premium = (
            _safe(cagr_total_cost / cpi_cagr)
            if (not np.isnan(cagr_total_cost) and cpi_cagr != 0)
            else None
        )

        results[school] = {
            "cagr_total_cost_20yr":   _safe(cagr_total_cost),
            "cagr_tuition_fees_20yr": _safe(cagr_tuition_fees),
            "cumulative_multiplier":  _safe(cum_multiplier),
            "min_annual_pct_increase": min_pct_increase,
            "min_annual_pct_year":     min_pct_year,
            "max_annual_pct_increase": max_pct_increase,
            "max_annual_pct_year":     max_pct_year,
            "rolling_5yr_cagrs":      rolling_cagrs,
            "college_premium_vs_cpi": college_premium,
        }

    return results


# ── Group metrics ────────────────────────────────────────────────────────────

def compute_group_metrics(school_metrics: dict, costs: pd.DataFrame) -> dict:
    """Ivy / Ivy+ CAGR summary stats and average total_cost per year."""

    def _extract_cagrs(group: list, metric: str) -> list:
        return [
            school_metrics[s][metric]
            for s in group
            if s in school_metrics and school_metrics[s][metric] is not None
        ]

    groups = {
        "ivy":      IVY_SCHOOLS,
        "ivy_plus": IVY_PLUS_SCHOOLS,
    }

    group_results = {}
    for label, members in groups.items():
        tc_cagrs  = _extract_cagrs(members, "cagr_total_cost_20yr")
        tuf_cagrs = _extract_cagrs(members, "cagr_tuition_fees_20yr")

        # Average total_cost per year across group
        group_df = costs[costs["school"].isin(members)]
        if "total_cost" in group_df.columns:
            avg_by_year = (
                group_df.groupby("year")["total_cost"]
                .mean()
                .round(2)
                .to_dict()
            )
            avg_by_year = {str(k): _safe(v) for k, v in avg_by_year.items()}
        else:
            avg_by_year = {}

        group_results[label] = {
            "schools": members,
            "cagr_total_cost_stats":   _group_cagr_stats(tc_cagrs),
            "cagr_tuition_fees_stats": _group_cagr_stats(tuf_cagrs),
            "avg_total_cost_by_year":  avg_by_year,
        }

    return group_results


# ── Structural breaks ────────────────────────────────────────────────────────

def compute_structural_breaks(costs: pd.DataFrame) -> dict:
    """Average year-over-year pct increase during crisis windows."""
    if "total_cost" not in costs.columns:
        return {}

    # Build a wide pivot: index=year, columns=school
    pivot = costs.pivot(index="year", columns="school", values="total_cost").sort_index()
    pct_changes = pivot.pct_change()

    def _window_stats(years: list) -> dict:
        window = pct_changes[pct_changes.index.isin(years)]
        if window.empty:
            return {"years": years, "mean_increase": None, "median_increase": None}
        vals = window.values.flatten()
        vals = vals[~np.isnan(vals)]
        return {
            "years":           years,
            "mean_increase":   _safe(float(np.mean(vals))) if len(vals) else None,
            "median_increase": _safe(float(np.median(vals))) if len(vals) else None,
        }

    return {
        "financial_crisis_2008_2010": _window_stats(CRISIS_YEARS),
        "covid_2020_2021":            _window_stats(COVID_YEARS),
    }


# ── Print key findings ────────────────────────────────────────────────────────

def print_findings(cpi_cagr: float, school_metrics: dict, group_metrics: dict,
                   structural_breaks: dict) -> None:
    sep = "-" * 60

    print("\n" + sep)
    print("KEY FINDINGS: College Cost Inflation Analysis")
    print(f"Period: {HIST_START}–{HIST_END}  ({CAGR_YEARS} years)")
    print(sep)

    print(f"\nCPI CAGR ({HIST_START}–{HIST_END}): {fmt_pct(cpi_cagr)}")

    print("\n-- 20-Year Total-Cost CAGR by School --")
    sorted_schools = sorted(
        school_metrics.items(),
        key=lambda x: (x[1]["cagr_total_cost_20yr"] or 0),
        reverse=True,
    )
    for school, m in sorted_schools:
        cagr_val = m["cagr_total_cost_20yr"]
        premium  = m["college_premium_vs_cpi"]
        mult     = m["cumulative_multiplier"]
        print(
            f"  {school:<12} CAGR={fmt_pct(cagr_val)}  "
            f"Premium={premium:.2f}x CPI  "
            f"Multiplier={mult:.2f}x"
            if (cagr_val is not None and premium is not None and mult is not None)
            else f"  {school:<12} (insufficient data)"
        )

    print("\n-- Group CAGR Stats (total_cost) --")
    for label, gm in group_metrics.items():
        stats = gm["cagr_total_cost_stats"]
        print(
            f"  {label.upper():<10}  "
            f"mean={fmt_pct(stats['mean'])}  "
            f"median={fmt_pct(stats['median'])}  "
            f"std={fmt_pct(stats['std_dev'])}"
        )

    print("\n-- Structural Breaks --")
    for event, sb in structural_breaks.items():
        mean_i   = sb.get("mean_increase")
        median_i = sb.get("median_increase")
        years    = sb.get("years", [])
        print(
            f"  {event}: years={years}  "
            f"mean={fmt_pct(mean_i)}  median={fmt_pct(median_i)}"
        )

    print(sep + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Load
    costs, cpi = load_data()

    # CPI CAGR
    cpi_cagr = compute_cpi_cagr(cpi)

    # Per-school
    school_metrics = compute_school_metrics(costs, cpi_cagr)

    # Group
    group_metrics = compute_group_metrics(school_metrics, costs)

    # Structural breaks
    structural_breaks = compute_structural_breaks(costs)

    # Assemble output
    results = {
        "metadata": {
            "hist_start":  HIST_START,
            "hist_end":    HIST_END,
            "cagr_years":  CAGR_YEARS,
            "rolling_window": ROLLING_WINDOW,
        },
        "cpi_cagr": _safe(cpi_cagr),
        "schools":  school_metrics,
        "groups":   group_metrics,
        "structural_breaks": structural_breaks,
    }

    # Save
    out_path = DATA_PROCESSED / "analysis_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"Results saved to {out_path}")

    # Print findings
    print_findings(cpi_cagr, school_metrics, group_metrics, structural_breaks)


if __name__ == "__main__":
    main()
