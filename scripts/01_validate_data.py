"""
01_validate_data.py
-------------------
Validates raw tuition data, interpolates minor gaps, and produces:
  - data/processed/costs_cleaned.csv       (validated + interpolated)
  - data/processed/costs_real_dollars.csv  (inflation-adjusted to 2026 dollars)

Run from project root:
    python -m scripts.01_validate_data
"""

import sys
import numpy as np
import pandas as pd

from scripts.config import DATA_RAW, DATA_PROCESSED, SCHOOLS, HIST_START, HIST_END
from scripts.utils import load_tuition, load_cpi


# ── Constants ──────────────────────────────────────────────────────────────────

KEY_COLS = ["school", "year", "tuition_fees", "total_cost"]
YOY_THRESHOLD = 0.15          # flag year-over-year changes larger than 15%
CPI_BASE_YEAR = 2026          # target year for real-dollar conversion


# ── Helpers ────────────────────────────────────────────────────────────────────

def _log_linear_interp(series: pd.Series) -> pd.Series:
    """
    Fill NaN gaps using log-linear interpolation (equivalent to geometric
    interpolation in linear space).  Only values that are already present
    serve as anchors; gaps larger than 1 year are left as NaN so they are
    surfaced in validation rather than silently filled.
    """
    log_s = np.log(series.replace(0, np.nan))
    log_interp = log_s.interpolate(method="linear", limit=1)
    filled = np.exp(log_interp)
    # Restore original non-NaN values exactly (avoids floating-point drift)
    filled[series.notna()] = series[series.notna()]
    return filled


def _interpolate_school(df_school: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    """
    For one school's data (sorted by year), fill single-year gaps via
    log-linear interpolation.
    """
    df_school = df_school.set_index("year").sort_index()
    # Re-index to the full year range so gaps become explicit NaNs
    full_index = range(HIST_START, HIST_END + 1)
    df_school = df_school.reindex(full_index)
    df_school.index.name = "year"

    for col in numeric_cols:
        if col in df_school.columns:
            df_school[col] = _log_linear_interp(df_school[col])

    df_school = df_school.reset_index()
    return df_school


# ── Validation steps ───────────────────────────────────────────────────────────

def check_missing_values(df: pd.DataFrame) -> dict:
    """Return counts of missing values in key columns."""
    missing = {col: int(df[col].isna().sum()) for col in KEY_COLS if col in df.columns}
    return missing


def check_yoy_changes(df: pd.DataFrame, col: str = "total_cost") -> pd.DataFrame:
    """Flag rows where year-over-year change in *col* exceeds YOY_THRESHOLD."""
    df_sorted = df.sort_values(["school", "year"]).copy()
    df_sorted["_pct_chg"] = df_sorted.groupby("school")[col].pct_change()
    flagged = df_sorted[df_sorted["_pct_chg"].abs() > YOY_THRESHOLD].copy()
    flagged = flagged.drop(columns=["_pct_chg"])
    return flagged


def check_total_cost_integrity(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows where total_cost < tuition_fees (logical error)."""
    mask = df["total_cost"] < df["tuition_fees"]
    return df[mask].copy()


def check_year_coverage(df: pd.DataFrame) -> dict:
    """
    For each school in SCHOOLS, report which years in [HIST_START, HIST_END]
    are missing from the raw data.
    """
    expected_years = set(range(HIST_START, HIST_END + 1))
    coverage = {}
    for school in SCHOOLS:
        school_years = set(df[df["school"] == school]["year"].tolist())
        missing_years = sorted(expected_years - school_years)
        if missing_years:
            coverage[school] = missing_years
    return coverage


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_validation() -> None:
    # ── 1. Load raw data ───────────────────────────────────────────────────────
    print("=" * 60)
    print("01_validate_data.py")
    print("=" * 60)

    try:
        df_raw = load_tuition()
    except FileNotFoundError as exc:
        sys.exit(
            f"ERROR: Could not load tuition data.\n"
            f"  Expected: {DATA_RAW / 'tuition_costs.csv'}\n"
            f"  Detail:   {exc}"
        )

    try:
        df_cpi = load_cpi()
    except FileNotFoundError as exc:
        sys.exit(
            f"ERROR: Could not load CPI data.\n"
            f"  Expected: {DATA_RAW / 'cpi_annual.csv'}\n"
            f"  Detail:   {exc}"
        )

    print(f"\nLoaded tuition data:  {len(df_raw):,} rows, {df_raw['school'].nunique()} schools")
    print(f"Loaded CPI data:      {len(df_cpi):,} rows ({df_cpi['year'].min()}–{df_cpi['year'].max()})")

    # ── 2. Missing-value check ─────────────────────────────────────────────────
    print("\n── Missing values (key columns) ─────────────────────────────")
    missing = check_missing_values(df_raw)
    any_missing = False
    for col, count in missing.items():
        status = "OK" if count == 0 else f"WARNING  {count} missing"
        print(f"  {col:<20} {status}")
        if count > 0:
            any_missing = True

    # ── 3. Year-over-year spike check ─────────────────────────────────────────
    print(f"\n── Year-over-year changes > {YOY_THRESHOLD:.0%} (total_cost) ──────────")
    flagged_yoy = check_yoy_changes(df_raw, col="total_cost")
    if flagged_yoy.empty:
        print("  None flagged.")
    else:
        print(f"  {len(flagged_yoy)} row(s) flagged:")
        for _, row in flagged_yoy.iterrows():
            print(f"    {row['school']} {int(row['year'])}: total_cost = ${row['total_cost']:,.0f}")

    # ── 4. Total-cost integrity check ─────────────────────────────────────────
    print("\n── total_cost < tuition_fees (integrity check) ───────────────")
    bad_rows = check_total_cost_integrity(df_raw)
    if bad_rows.empty:
        print("  All rows OK.")
    else:
        print(f"  {len(bad_rows)} row(s) with total_cost < tuition_fees:")
        for _, row in bad_rows.iterrows():
            print(
                f"    {row['school']} {int(row['year'])}: "
                f"tuition_fees={row['tuition_fees']:,.0f}  total_cost={row['total_cost']:,.0f}"
            )

    # ── 5. Year-coverage check ────────────────────────────────────────────────
    print(f"\n── Year coverage ({HIST_START}–{HIST_END}) per school ──────────────────")
    coverage_gaps = check_year_coverage(df_raw)
    if not coverage_gaps:
        print("  All schools have complete year coverage.")
    else:
        for school, missing_years in coverage_gaps.items():
            print(f"  {school}: missing {missing_years}")

    # ── 6. Interpolate single-year gaps ───────────────────────────────────────
    print("\n── Interpolating single-year gaps (log-linear) ───────────────")
    numeric_cols = [c for c in df_raw.select_dtypes(include="number").columns if c != "year"]
    parts = []
    for school in df_raw["school"].unique():
        chunk = df_raw[df_raw["school"] == school].copy()
        chunk_filled = _interpolate_school(chunk, numeric_cols)
        chunk_filled["school"] = school
        parts.append(chunk_filled)

    df_clean = pd.concat(parts, ignore_index=True)
    df_clean = df_clean.sort_values(["school", "year"]).reset_index(drop=True)

    # Count how many values were interpolated
    original_non_null = df_raw[numeric_cols].notna().sum().sum()
    cleaned_non_null = df_clean[numeric_cols].notna().sum().sum()
    interpolated_count = cleaned_non_null - original_non_null
    print(f"  {interpolated_count} value(s) filled via interpolation.")

    # ── 7. Save cleaned data ───────────────────────────────────────────────────
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    cleaned_path = DATA_PROCESSED / "costs_cleaned.csv"
    df_clean.to_csv(cleaned_path, index=False)
    print(f"\n  Saved cleaned data  →  {cleaned_path}")

    # ── 8. Merge with CPI and compute real dollars ─────────────────────────────
    print(f"\n── Inflation adjustment to {CPI_BASE_YEAR} dollars ───────────────────")

    # Validate that CPI covers the base year
    cpi_lookup = df_cpi.set_index("year")["cpi_u"]
    if CPI_BASE_YEAR not in cpi_lookup.index:
        sys.exit(
            f"ERROR: CPI data does not contain base year {CPI_BASE_YEAR}. "
            f"Available years: {sorted(cpi_lookup.index.tolist())}"
        )

    cpi_base = float(cpi_lookup[CPI_BASE_YEAR])
    print(f"  CPI base ({CPI_BASE_YEAR}): {cpi_base:.1f}")

    df_real = df_clean.merge(
        df_cpi[["year", "cpi_u"]],
        on="year",
        how="left",
        validate="m:1",
    )

    missing_cpi = df_real["cpi_u"].isna().sum()
    if missing_cpi > 0:
        print(f"  WARNING: {missing_cpi} row(s) have no CPI match and will have NaN real values.")

    # Columns to adjust (must exist in cleaned data)
    value_cols = [c for c in ["tuition_fees", "room_board", "total_cost"] if c in df_clean.columns]
    for col in value_cols:
        df_real[f"{col}_real"] = df_real[col] * (cpi_base / df_real["cpi_u"])

    # Select and order output columns
    real_cols = (
        ["school", "year"]
        + value_cols
        + [f"{c}_real" for c in value_cols]
        + ["cpi_u"]
    )
    real_cols = [c for c in real_cols if c in df_real.columns]
    df_real = df_real[real_cols].sort_values(["school", "year"]).reset_index(drop=True)

    real_path = DATA_PROCESSED / "costs_real_dollars.csv"
    df_real.to_csv(real_path, index=False)
    print(f"  Saved real-dollar data  →  {real_path}")
    print(f"  Columns: {', '.join(df_real.columns.tolist())}")

    # ── 9. Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Raw rows loaded:          {len(df_raw):>6,}")
    print(f"  Cleaned rows (output):    {len(df_clean):>6,}")
    print(f"  Schools:                  {df_clean['school'].nunique():>6}")
    print(f"  Year range:               {int(df_clean['year'].min())}–{int(df_clean['year'].max())}")
    print(f"  Missing key-col values:   {sum(missing.values()):>6}")
    print(f"  YoY spikes flagged:       {len(flagged_yoy):>6}")
    print(f"  Integrity violations:     {len(bad_rows):>6}")
    print(f"  Schools with gaps:        {len(coverage_gaps):>6}")
    print(f"  Values interpolated:      {interpolated_count:>6}")
    overall = (
        "PASS"
        if not any_missing and bad_rows.empty and not coverage_gaps
        else "WARNINGS: review output above"
    )
    print(f"\n  Overall status: {overall}")
    print("=" * 60)


if __name__ == "__main__":
    run_validation()
