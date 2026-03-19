"""
03_project.py: Project college costs for 2027-2046 using three models.

Models
------
1. Baseline  : cost(y) = cost_2026 × (1 + CAGR_20yr)^(y-2026)
2. Regression: Log-linear OLS fit on historical data; extrapolate with fitted slope
3. Scenarios : High / Moderate / Low with distinct rate logic

Also computes CPI-projected costs and milestone crossing years.

Usage
-----
    python -m scripts.03_project
"""

from __future__ import annotations

import sys
import numpy as np
import pandas as pd
from scipy.stats import linregress

from scripts.config import (
    CPI_PROJ_RATE,
    DATA_PROCESSED,
    HIST_END,
    IVY_PLUS_SCHOOLS,
    IVY_SCHOOLS,
    MILESTONES,
    PROJ_END,
    PROJ_START,
    SCHOOLS,
)
from scripts.utils import cagr, fmt_currency, load_cleaned

# ── Constants ──────────────────────────────────────────────────────────────────
PROJ_YEARS = list(range(PROJ_START, PROJ_END + 1))  # 2027-2046
N_PROJ = len(PROJ_YEARS)                             # 20 years


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cagr_window(df_school: pd.DataFrame, n_years: int) -> float:
    """CAGR over the last *n_years* of historical data for a single school."""
    df_sorted = df_school.sort_values("year")
    cost_end = df_sorted.loc[df_sorted["year"] == HIST_END, "total_cost"]
    cost_start = df_sorted.loc[df_sorted["year"] == HIST_END - n_years, "total_cost"]
    if cost_end.empty or cost_start.empty:
        return np.nan
    return cagr(float(cost_start.iloc[0]), float(cost_end.iloc[0]), n_years)


def _regression_params(df_school: pd.DataFrame) -> tuple[float, float]:
    """
    OLS log-linear fit: log(cost) = slope * year + intercept.
    Returns (slope, intercept).
    """
    df_sorted = df_school.dropna(subset=["total_cost"]).sort_values("year")
    years = df_sorted["year"].values
    log_costs = np.log(df_sorted["total_cost"].values)
    slope, intercept, *_ = linregress(years, log_costs)
    return float(slope), float(intercept)


# ── Per-school projection ─────────────────────────────────────────────────────

def project_school(school: str, df_school: pd.DataFrame) -> pd.DataFrame:
    """
    Build projection rows for a single school across all models/scenarios.
    Returns a DataFrame with columns: school, year, model, total_cost_projected.
    """
    df_school = df_school.sort_values("year")

    # Base values
    cost_2026_row = df_school.loc[df_school["year"] == HIST_END, "total_cost"]
    if cost_2026_row.empty:
        print(f"  WARNING: {school} has no 2026 cost, skipping.", file=sys.stderr)
        return pd.DataFrame()
    cost_2026 = float(cost_2026_row.iloc[0])

    cagr_20 = _cagr_window(df_school, 20)
    cagr_10 = _cagr_window(df_school, 10)
    reg_slope, reg_intercept = _regression_params(df_school)

    rows: list[dict] = []

    for y in PROJ_YEARS:
        t = y - HIST_END  # years past 2026

        # ── 1. Baseline (20-yr CAGR) ──────────────────────────────────────
        if not np.isnan(cagr_20):
            baseline_cost = cost_2026 * (1 + cagr_20) ** t
        else:
            baseline_cost = np.nan
        rows.append({
            "school": school,
            "year": y,
            "model": "baseline",
            "total_cost_projected": baseline_cost,
        })

        # ── 2. Regression (log-linear OLS extrapolation) ──────────────────
        reg_cost = np.exp(reg_slope * y + reg_intercept)
        rows.append({
            "school": school,
            "year": y,
            "model": "regression",
            "total_cost_projected": reg_cost,
        })

        # ── 3a. Scenario: High ────────────────────────────────────────────
        if not np.isnan(cagr_10) and not np.isnan(cagr_20):
            rate_high = max(cagr_10, cagr_20 + 0.005)
        elif not np.isnan(cagr_20):
            rate_high = cagr_20 + 0.005
        else:
            rate_high = np.nan
        high_cost = cost_2026 * (1 + rate_high) ** t if not np.isnan(rate_high) else np.nan
        rows.append({
            "school": school,
            "year": y,
            "model": "scenario_high",
            "total_cost_projected": high_cost,
        })

        # ── 3b. Scenario: Moderate ────────────────────────────────────────
        if not np.isnan(cagr_20):
            rate_mod = max(cagr_20 - 0.005, CPI_PROJ_RATE + 0.01)
        else:
            rate_mod = np.nan
        mod_cost = cost_2026 * (1 + rate_mod) ** t if not np.isnan(rate_mod) else np.nan
        rows.append({
            "school": school,
            "year": y,
            "model": "scenario_moderate",
            "total_cost_projected": mod_cost,
        })

        # ── 3c. Scenario: Low (linear convergence over 20 years) ──────────
        # Rate linearly interpolates from cagr_20 at t=1 to CPI_PROJ_RATE+0.005 at t=20.
        # Compounding: cost(y) = cost_2026 × ∏_{i=1}^{t} (1 + r_i)
        if not np.isnan(cagr_20):
            rate_start = cagr_20
            rate_end = CPI_PROJ_RATE + 0.005
            # weight = fraction through the 20-year window (0 at t=1, 1 at t=20)
            weight = (t - 1) / (N_PROJ - 1) if N_PROJ > 1 else 0.0
            rate_low_t = rate_start + weight * (rate_end - rate_start)
            # For a single projected year we only need the compound product.
            # Accumulate product ∏ (1 + r_i) for i = 1..t
            product = 1.0
            for i in range(1, t + 1):
                w_i = (i - 1) / (N_PROJ - 1) if N_PROJ > 1 else 0.0
                r_i = rate_start + w_i * (rate_end - rate_start)
                product *= (1 + r_i)
            low_cost = cost_2026 * product
        else:
            low_cost = np.nan
        rows.append({
            "school": school,
            "year": y,
            "model": "scenario_low",
            "total_cost_projected": low_cost,
        })

        # ── CPI-projected cost ────────────────────────────────────────────
        cpi_cost = cost_2026 * (1 + CPI_PROJ_RATE) ** t
        rows.append({
            "school": school,
            "year": y,
            "model": "cpi_projection",
            "total_cost_projected": cpi_cost,
        })

    return pd.DataFrame(rows)


# ── Group averages ────────────────────────────────────────────────────────────

def compute_group_averages(df_proj: pd.DataFrame) -> pd.DataFrame:
    """
    Compute mean projected costs for Ivy and Ivy+ groups across all models/years.
    Returns rows tagged with school='Ivy_Average' or 'IvyPlus_Average'.
    """
    groups = {
        "Ivy_Average": IVY_SCHOOLS,
        "IvyPlus_Average": IVY_PLUS_SCHOOLS,
    }
    avg_rows = []
    for group_name, members in groups.items():
        subset = df_proj[df_proj["school"].isin(members)]
        grp = (
            subset.groupby(["year", "model"], as_index=False)["total_cost_projected"]
            .mean()
        )
        grp.insert(0, "school", group_name)
        avg_rows.append(grp)
    return pd.concat(avg_rows, ignore_index=True)


# ── Milestone detection ───────────────────────────────────────────────────────

def find_milestones(df_proj: pd.DataFrame) -> pd.DataFrame:
    """
    For each (school, model), find the first year each MILESTONE threshold is crossed.
    Only individual schools (not group averages) are included.
    """
    individual = df_proj[df_proj["school"].isin(SCHOOLS)].copy()
    records = []
    for (school, model), grp in individual.groupby(["school", "model"]):
        grp_sorted = grp.sort_values("year")
        for milestone in MILESTONES:
            crossing = grp_sorted.loc[
                grp_sorted["total_cost_projected"] >= milestone, "year"
            ]
            records.append({
                "school": school,
                "model": model,
                "milestone": milestone,
                "crossing_year": int(crossing.iloc[0]) if not crossing.empty else None,
            })
    return pd.DataFrame(records)


# ── Print milestone summary ───────────────────────────────────────────────────

def print_milestone_summary(df_milestones: pd.DataFrame) -> None:
    """Print a readable milestone summary to stdout."""
    scenario_models = ["scenario_high", "scenario_moderate", "scenario_low", "baseline"]
    print("\n" + "=" * 72)
    print("MILESTONE CROSSING YEARS")
    print("=" * 72)

    for milestone in MILESTONES:
        print(f"\n  {fmt_currency(milestone)} threshold")
        print(f"  {'School':<14}", end="")
        for m in scenario_models:
            label = m.replace("scenario_", "").capitalize()
            print(f"  {label:>10}", end="")
        print()
        print("  " + "-" * (14 + 14 * len(scenario_models)))

        df_m = df_milestones[df_milestones["milestone"] == milestone]
        for school in SCHOOLS:
            print(f"  {school:<14}", end="")
            for m in scenario_models:
                row = df_m[(df_m["school"] == school) & (df_m["model"] == m)]
                if row.empty or row["crossing_year"].isna().all():
                    yr = ">2046"
                else:
                    yr = str(int(row["crossing_year"].iloc[0]))
                print(f"  {yr:>10}", end="")
            print()

    print("\n" + "=" * 72 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading cleaned data …")
    df = load_cleaned()

    # Validate expected columns
    required_cols = {"school", "year", "total_cost"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"costs_cleaned.csv is missing columns: {missing}")

    # Filter to known schools and historical window
    df = df[df["school"].isin(SCHOOLS)].copy()

    # ── Project each school ───────────────────────────────────────────────
    print("Projecting costs for each school …")
    school_frames: list[pd.DataFrame] = []
    for school in SCHOOLS:
        df_school = df[df["school"] == school]
        result = project_school(school, df_school)
        if not result.empty:
            school_frames.append(result)
            print(f"  {school}: done")

    df_proj = pd.concat(school_frames, ignore_index=True)

    # ── Group averages ────────────────────────────────────────────────────
    print("Computing group averages …")
    df_avg = compute_group_averages(df_proj)
    df_all = pd.concat([df_proj, df_avg], ignore_index=True)

    # ── Enforce column order ──────────────────────────────────────────────
    df_all = df_all[["school", "year", "model", "total_cost_projected"]]
    df_all = df_all.sort_values(["school", "model", "year"]).reset_index(drop=True)

    # ── Save projections ──────────────────────────────────────────────────
    out_path = DATA_PROCESSED / "projections.csv"
    df_all.to_csv(out_path, index=False)
    print(f"\nProjections saved → {out_path}")
    print(f"  Rows : {len(df_all):,}")
    print(f"  Models: {sorted(df_all['model'].unique())}")

    # ── Milestones ────────────────────────────────────────────────────────
    print("Computing milestone crossing years …")
    df_milestones = find_milestones(df_proj)
    print_milestone_summary(df_milestones)


if __name__ == "__main__":
    main()
