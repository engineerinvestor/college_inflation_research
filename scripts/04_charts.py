"""
04_charts.py: Generate all research charts (PNG @ 300 DPI + SVG).

Usage
-----
    python -m scripts.04_charts
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from scripts.config import (
    SCHOOLS,
    IVY_SCHOOLS,
    IVY_PLUS_SCHOOLS,
    SCHOOL_COLORS,
    CHARTS_PNG,
    CHARTS_SVG,
    CHART_STYLE,
    CHART_DPI,
    CHART_FIGSIZE,
    HIST_START,
    HIST_END,
    PROJ_START,
    PROJ_END,
    CPI_PROJ_RATE,
    DATA_PROCESSED,
    DATA_RAW,
)
from scripts.utils import (
    load_cleaned,
    load_real,
    load_projections,
    load_cpi,
    fmt_currency,
    fmt_pct,
    cagr,
)

# ── Apply global chart style ─────────────────────────────────────────────────
plt.rcParams.update(CHART_STYLE)


# ── Helper ────────────────────────────────────────────────────────────────────

def save_chart(fig, name: str) -> None:
    """Save figure as PNG and SVG, then close."""
    CHARTS_PNG.mkdir(parents=True, exist_ok=True)
    CHARTS_SVG.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS_PNG / f"{name}.png", dpi=CHART_DPI, bbox_inches="tight")
    fig.savefig(CHARTS_SVG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def _currency_formatter(x, _pos):
    """Axis tick formatter for US dollars."""
    if x >= 1_000_000:
        return f"${x / 1_000_000:.1f}M"
    if x >= 1_000:
        return f"${x / 1_000:.0f}K"
    return f"${x:,.0f}"


# ── Chart 01 ──────────────────────────────────────────────────────────────────

def chart_01_all_schools_total_cost() -> None:
    """Multi-line chart: all 12 schools' total_cost 2006-2026."""
    df = load_cleaned()
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)

    for school in SCHOOLS:
        sd = df[df["school"] == school].sort_values("year")
        ax.plot(
            sd["year"], sd["total_cost"],
            color=SCHOOL_COLORS.get(school, "#333333"),
            label=school, linewidth=1.8,
        )

    ax.set_title("Total Cost of Attendance: Ivy+ Schools (2006\u20132026)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Total Cost of Attendance")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    save_chart(fig, "01_all_schools_total_cost")


# ── Chart 02 ──────────────────────────────────────────────────────────────────

def chart_02_tuition_vs_total() -> None:
    """Dual-line chart for Harvard, Duke, Stanford: tuition vs total cost."""
    df = load_cleaned()
    rep_schools = ["Harvard", "Duke", "Stanford"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)

    for ax, school in zip(axes, rep_schools):
        sd = df[df["school"] == school].sort_values("year")
        color = SCHOOL_COLORS.get(school, "#333333")
        ax.plot(sd["year"], sd["total_cost"], color=color, linewidth=2, label="Total Cost")
        ax.plot(sd["year"], sd["tuition_fees"], color=color, linewidth=2,
                linestyle="--", label="Tuition & Fees")
        ax.set_title(school)
        ax.set_xlabel("Year")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
        ax.legend(fontsize=8)

    axes[0].set_ylabel("Cost")
    fig.suptitle("Tuition vs. Total Cost of Attendance", fontsize=14, y=1.02)
    fig.tight_layout()
    save_chart(fig, "02_tuition_vs_total")


# ── Chart 03 ──────────────────────────────────────────────────────────────────

def chart_03_cagr_bar() -> None:
    """Horizontal bar chart: 20-year total_cost CAGR vs CPI CAGR."""
    df = load_cleaned()
    cpi = load_cpi()

    # CPI CAGR
    cpi_indexed = cpi.set_index("year")["cpi_u"]
    cpi_cagr_val = cagr(
        float(cpi_indexed.loc[HIST_START]),
        float(cpi_indexed.loc[HIST_END]),
        HIST_END - HIST_START,
    )

    # School CAGRs
    records = []
    for school in SCHOOLS:
        sd = df[df["school"] == school].sort_values("year")
        start_row = sd.loc[sd["year"] == HIST_START, "total_cost"]
        end_row = sd.loc[sd["year"] == HIST_END, "total_cost"]
        if not start_row.empty and not end_row.empty:
            c = cagr(float(start_row.iloc[0]), float(end_row.iloc[0]), HIST_END - HIST_START)
            records.append({"school": school, "cagr": c})

    records.sort(key=lambda r: r["cagr"], reverse=True)

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    y_pos = range(len(records))
    colors = [SCHOOL_COLORS.get(r["school"], "#333333") for r in records]
    bars = ax.barh(
        y_pos, [r["cagr"] * 100 for r in records],
        color=colors, edgecolor="white", height=0.7,
    )
    ax.set_yticks(y_pos)
    ax.set_yticklabels([r["school"] for r in records])
    ax.axvline(x=cpi_cagr_val * 100, color="#E63946", linestyle="--", linewidth=2,
               label=f"CPI CAGR ({cpi_cagr_val * 100:.2f}%)")
    ax.set_xlabel("CAGR (%)")
    ax.set_title("20-Year Cost Growth Rate (CAGR) vs. Inflation")
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    save_chart(fig, "03_cagr_bar")


# ── Chart 04 ──────────────────────────────────────────────────────────────────

def chart_04_indexed_comparison() -> None:
    """Ivy+ average vs CPI indexed to 100 in 2006."""
    df = load_cleaned()
    cpi = load_cpi()

    # Ivy+ average total_cost by year
    ivy_df = df[df["school"].isin(IVY_PLUS_SCHOOLS)]
    avg_by_year = ivy_df.groupby("year")["total_cost"].mean().sort_index()
    base_cost = avg_by_year.loc[HIST_START]
    indexed_cost = (avg_by_year / base_cost) * 100

    # CPI indexed
    cpi_indexed = cpi.set_index("year")["cpi_u"]
    cpi_base = cpi_indexed.loc[HIST_START]
    indexed_cpi = (cpi_indexed / cpi_base) * 100
    # Restrict to our range
    indexed_cpi = indexed_cpi.loc[HIST_START:HIST_END]

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    ax.plot(indexed_cost.index, indexed_cost.values, color="#A51C30", linewidth=2.5,
            label="Ivy+ Average Cost")
    ax.plot(indexed_cpi.index, indexed_cpi.values, color="#457B9D", linewidth=2.5,
            label="Consumer Prices (CPI-U)")
    ax.axhline(y=100, color="gray", linestyle=":", linewidth=1)
    ax.set_title("Ivy+ Costs vs. Consumer Prices (Indexed to 2006 = 100)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Index (2006 = 100)")
    ax.legend()
    save_chart(fig, "04_indexed_comparison")


# ── Chart 05 ──────────────────────────────────────────────────────────────────

def chart_05_heatmap() -> None:
    """Heatmap: annual pct increase in total_cost, schools x years."""
    df = load_cleaned()

    pivot = df.pivot(index="school", columns="year", values="total_cost").sort_index()
    pct = pivot.pct_change(axis=1) * 100  # percentage
    pct = pct.iloc[:, 1:]  # drop first column (NaN)

    fig, ax = plt.subplots(figsize=(max(14, len(pct.columns) * 0.8), 8))
    im = ax.imshow(pct.values, aspect="auto", cmap="RdBu_r",
                   vmin=0, vmax=pct.values[~np.isnan(pct.values)].max())

    ax.set_xticks(range(len(pct.columns)))
    ax.set_xticklabels(pct.columns.astype(int), rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(pct.index)))
    ax.set_yticklabels(pct.index, fontsize=9)

    # Annotate cells
    for i in range(pct.shape[0]):
        for j in range(pct.shape[1]):
            val = pct.iloc[i, j]
            if not np.isnan(val):
                text_color = "white" if abs(val) > pct.values[~np.isnan(pct.values)].max() * 0.6 else "black"
                ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                        fontsize=7, color=text_color)

    ax.set_title("Annual Cost Increases (%)")
    fig.colorbar(im, ax=ax, label="Year-over-Year Change (%)", shrink=0.8)
    fig.tight_layout()
    save_chart(fig, "05_heatmap")


# ── Chart 06 ──────────────────────────────────────────────────────────────────

def chart_06_real_vs_nominal() -> None:
    """Ivy+ average nominal vs real (2026 dollars) with shaded gap."""
    df_nominal = load_cleaned()
    df_real = load_real()

    # Nominal average
    nom_avg = (
        df_nominal[df_nominal["school"].isin(IVY_PLUS_SCHOOLS)]
        .groupby("year")["total_cost"].mean().sort_index()
    )

    # Real average
    real_avg = (
        df_real[df_real["school"].isin(IVY_PLUS_SCHOOLS)]
        .groupby("year")["total_cost"].mean().sort_index()
    )

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    years = nom_avg.index
    ax.plot(years, nom_avg.values, color="#E63946", linewidth=2.5, label="Nominal Dollars")
    ax.plot(years, real_avg.values, color="#457B9D", linewidth=2.5, label="Real (2026) Dollars")
    ax.fill_between(years, nom_avg.values, real_avg.values, alpha=0.15, color="#E63946",
                    label="Inflation Component")
    ax.set_title("Nominal vs. Real Cost of Attendance (Ivy+ Average)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Cost of Attendance")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.legend()
    save_chart(fig, "06_real_vs_nominal")


# ── Chart 07 ──────────────────────────────────────────────────────────────────

def chart_07_school_projections() -> None:
    """Fan chart per school: historical + scenario projections."""
    df_hist = load_cleaned()
    df_proj = load_projections()

    for school in SCHOOLS:
        fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
        color = SCHOOL_COLORS.get(school, "#333333")

        # Historical
        sh = df_hist[df_hist["school"] == school].sort_values("year")
        ax.plot(sh["year"], sh["total_cost"], color=color, linewidth=2.5, label="Historical")

        # Projections
        sp = df_proj[df_proj["school"] == school]
        models = {
            "scenario_high": ("High", "--"),
            "baseline": ("Baseline", "-"),
            "scenario_moderate": ("Moderate", "-."),
            "scenario_low": ("Low", ":"),
        }
        proj_data = {}
        for model, (label, ls) in models.items():
            md = sp[sp["model"] == model].sort_values("year")
            if md.empty:
                continue
            # Connect projection to last historical point
            years = pd.concat([sh["year"].tail(1), md["year"]])
            costs = pd.concat([sh["total_cost"].tail(1), md["total_cost_projected"]])
            ax.plot(years, costs, color=color, linewidth=1.5, linestyle=ls,
                    label=f"{label}", alpha=0.8)
            proj_data[model] = md

        # Shade between high and low
        if "scenario_high" in proj_data and "scenario_low" in proj_data:
            high = proj_data["scenario_high"].sort_values("year")
            low = proj_data["scenario_low"].sort_values("year")
            ax.fill_between(
                high["year"], low["total_cost_projected"], high["total_cost_projected"],
                alpha=0.12, color=color,
            )

        ax.axvline(x=HIST_END, color="gray", linestyle=":", linewidth=1, alpha=0.6)
        ax.set_title(f"{school} Cost Projection (2006\u20132046)")
        ax.set_xlabel("Year")
        ax.set_ylabel("Total Cost of Attendance")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
        ax.legend(fontsize=8)
        save_chart(fig, f"projection_{school.lower()}")


# ── Chart 08 ──────────────────────────────────────────────────────────────────

def chart_08_group_projection() -> None:
    """Fan chart for IvyPlus_Average from projections data."""
    df_hist = load_cleaned()
    df_proj = load_projections()

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)

    # Historical Ivy+ average
    ivy_hist = (
        df_hist[df_hist["school"].isin(IVY_PLUS_SCHOOLS)]
        .groupby("year")["total_cost"].mean().reset_index().sort_values("year")
    )
    ax.plot(ivy_hist["year"], ivy_hist["total_cost"], color="#A51C30", linewidth=2.5,
            label="Historical")

    # Projections for IvyPlus_Average
    gp = df_proj[df_proj["school"] == "IvyPlus_Average"]
    models = {
        "scenario_high": ("High", "--"),
        "baseline": ("Baseline", "-"),
        "scenario_moderate": ("Moderate", "-."),
        "scenario_low": ("Low", ":"),
    }
    proj_data = {}
    for model, (label, ls) in models.items():
        md = gp[gp["model"] == model].sort_values("year")
        if md.empty:
            continue
        years = pd.concat([ivy_hist["year"].tail(1), md["year"]])
        costs = pd.concat([ivy_hist["total_cost"].tail(1), md["total_cost_projected"]])
        ax.plot(years, costs, color="#A51C30", linewidth=1.5, linestyle=ls,
                label=label, alpha=0.8)
        proj_data[model] = md

    if "scenario_high" in proj_data and "scenario_low" in proj_data:
        high = proj_data["scenario_high"].sort_values("year")
        low = proj_data["scenario_low"].sort_values("year")
        ax.fill_between(
            high["year"], low["total_cost_projected"], high["total_cost_projected"],
            alpha=0.12, color="#A51C30",
        )

    ax.axvline(x=HIST_END, color="gray", linestyle=":", linewidth=1, alpha=0.6)
    ax.set_title("Ivy+ Average Cost Projection (2006\u20132046)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Total Cost of Attendance")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.legend(fontsize=9)
    save_chart(fig, "08_group_projection")


# ── Chart 09 ──────────────────────────────────────────────────────────────────

def chart_09_milestone_timeline() -> None:
    """Dot plot: year each school crosses $100K, $150K, $200K (baseline)."""
    df_proj = load_projections()
    df_hist = load_cleaned()

    milestones = [100_000, 150_000, 200_000]
    markers = {100_000: ("o", "#2A9D8F"), 150_000: ("s", "#E9C46A"), 200_000: ("D", "#E76F51")}
    milestone_labels = {100_000: "$100K", 150_000: "$150K", 200_000: "$200K"}

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)

    y_positions = {school: i for i, school in enumerate(SCHOOLS)}

    for milestone in milestones:
        marker, color = markers[milestone]
        for school in SCHOOLS:
            # Combine historical and baseline projection
            sh = df_hist[df_hist["school"] == school].sort_values("year")
            sp = df_proj[(df_proj["school"] == school) & (df_proj["model"] == "baseline")].sort_values("year")

            # Build full series
            hist_costs = sh[["year", "total_cost"]].rename(columns={"total_cost": "cost"})
            proj_costs = sp[["year", "total_cost_projected"]].rename(columns={"total_cost_projected": "cost"})
            full = pd.concat([hist_costs, proj_costs]).sort_values("year")

            crossing = full.loc[full["cost"] >= milestone, "year"]
            if not crossing.empty:
                yr = int(crossing.iloc[0])
                ax.scatter(yr, y_positions[school], marker=marker, color=color,
                           s=80, zorder=5, edgecolors="white", linewidths=0.5)

    # Legend entries
    for milestone in milestones:
        marker, color = markers[milestone]
        ax.scatter([], [], marker=marker, color=color, s=80, label=milestone_labels[milestone],
                   edgecolors="white", linewidths=0.5)

    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(list(y_positions.keys()))
    ax.set_xlabel("Year")
    ax.set_title("Projected Cost Milestones by School")
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    save_chart(fig, "09_milestone_timeline")


# ── Chart 10 ──────────────────────────────────────────────────────────────────

def chart_10_cumulative_4year() -> None:
    """Grouped bar chart: cumulative 4-year cost for representative years."""
    df_hist = load_cleaned()
    df_proj = load_projections()

    target_years = [2006, 2026, 2036, 2046]
    n_schools = len(SCHOOLS)
    n_years = len(target_years)
    bar_width = 0.18

    fig, ax = plt.subplots(figsize=(16, 8))
    x = np.arange(n_schools)

    for i, yr in enumerate(target_years):
        costs_4yr = []
        for school in SCHOOLS:
            if yr <= HIST_END:
                row = df_hist[(df_hist["school"] == school) & (df_hist["year"] == yr)]
                cost = float(row["total_cost"].iloc[0]) * 4 if not row.empty else 0
            else:
                row = df_proj[
                    (df_proj["school"] == school) &
                    (df_proj["year"] == yr) &
                    (df_proj["model"] == "baseline")
                ]
                cost = float(row["total_cost_projected"].iloc[0]) * 4 if not row.empty else 0
            costs_4yr.append(cost)

        offset = (i - n_years / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, costs_4yr, bar_width, label=str(yr), alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(SCHOOLS, rotation=45, ha="right")
    ax.set_ylabel("Cumulative 4-Year Cost")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.set_title("Cumulative 4-Year Cost of Attendance")
    ax.legend(title="Entering Year")
    fig.tight_layout()
    save_chart(fig, "10_cumulative_4year")


# ── Chart 11 ──────────────────────────────────────────────────────────────────

def chart_11_context_comparison() -> None:
    """Ivy+ costs in context: indexed vs income, home prices, S&P 500."""
    df = load_cleaned()
    cpi_df = load_cpi()

    years = np.arange(HIST_START, HIST_END + 1)

    # Ivy+ average indexed
    ivy_avg = (
        df[df["school"].isin(IVY_PLUS_SCHOOLS)]
        .groupby("year")["total_cost"].mean().sort_index()
    )
    ivy_base = ivy_avg.loc[HIST_START]
    ivy_indexed = (ivy_avg / ivy_base) * 100

    # CPI indexed
    cpi_s = cpi_df.set_index("year")["cpi_u"]
    cpi_base = cpi_s.loc[HIST_START]
    cpi_indexed = (cpi_s / cpi_base) * 100
    cpi_indexed = cpi_indexed.reindex(years)

    # Synthetic series using approximate CAGRs
    def _synthetic_indexed(cagr_rate: float) -> np.ndarray:
        return 100 * (1 + cagr_rate) ** (years - HIST_START)

    income_indexed = _synthetic_indexed(0.026)
    home_indexed = _synthetic_indexed(0.032)
    sp500_indexed = _synthetic_indexed(0.073)

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    ax.plot(ivy_indexed.index, ivy_indexed.values, color="#A51C30", linewidth=2.5,
            label="Ivy+ Average Cost")
    ax.plot(years, cpi_indexed.values, color="#457B9D", linewidth=2, label="CPI")
    ax.plot(years, income_indexed, color="#2A9D8F", linewidth=2,
            linestyle="--", label="Median Household Income (~2.6% CAGR)")
    ax.plot(years, home_indexed, color="#E9C46A", linewidth=2,
            linestyle="-.", label="Median Home Price (~3.2% CAGR)")
    ax.plot(years, sp500_indexed, color="#6A4C93", linewidth=2,
            linestyle=":", label="S&P 500 (~7.3% CAGR)")

    ax.axhline(y=100, color="gray", linestyle=":", linewidth=0.8)
    ax.set_title("College Costs in Context (Indexed to 2006 = 100)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Index (2006 = 100)")
    ax.legend(loc="upper left", fontsize=9)
    save_chart(fig, "11_context_comparison")


# ── Chart 12 ──────────────────────────────────────────────────────────────────

def chart_12_cost_breakdown() -> None:
    """Stacked bar: tuition & fees vs room & board for 2026-27."""
    df = load_cleaned()
    latest = df[df["year"] == HIST_END].copy()
    latest = latest.sort_values("total_cost", ascending=False)

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    x = np.arange(len(latest))

    ax.bar(x, latest["tuition_fees"].values, color="#A51C30", label="Tuition & Fees")
    ax.bar(x, latest["room_board"].values, bottom=latest["tuition_fees"].values,
           color="#457B9D", label="Room & Board")

    ax.set_xticks(x)
    ax.set_xticklabels(latest["school"].values, rotation=45, ha="right")
    ax.set_ylabel("Cost")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.set_title("Cost Breakdown 2026\u201327: Tuition & Fees vs. Room & Board")
    ax.legend()
    fig.tight_layout()
    save_chart(fig, "12_cost_breakdown")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Generating charts ...\n")

    charts = [
        ("01", "All Schools Total Cost", chart_01_all_schools_total_cost),
        ("02", "Tuition vs Total", chart_02_tuition_vs_total),
        ("03", "CAGR Bar", chart_03_cagr_bar),
        ("04", "Indexed Comparison", chart_04_indexed_comparison),
        ("05", "Heatmap", chart_05_heatmap),
        ("06", "Real vs Nominal", chart_06_real_vs_nominal),
        ("07", "School Projections (12 charts)", chart_07_school_projections),
        ("08", "Group Projection", chart_08_group_projection),
        ("09", "Milestone Timeline", chart_09_milestone_timeline),
        ("10", "Cumulative 4-Year", chart_10_cumulative_4year),
        ("11", "Context Comparison", chart_11_context_comparison),
        ("12", "Cost Breakdown", chart_12_cost_breakdown),
    ]

    for num, label, fn in charts:
        print(f"  Chart {num}: {label} ... ", end="", flush=True)
        try:
            fn()
            print("done")
        except Exception as exc:
            print(f"FAILED ({exc})")

    print(f"\nPNG charts saved to: {CHARTS_PNG}")
    print(f"SVG charts saved to: {CHARTS_SVG}")
    print("All charts complete.")


if __name__ == "__main__":
    main()
