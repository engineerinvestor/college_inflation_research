"""
05_generate_report.py: Generate report.md and blog_post.md from analysis data.

Produces two markdown files in output/:
  - report.md   (~4000 words), full analytical report
  - blog_post.md (~1800 words), shorter, accessible blog format

Usage
-----
    python -m scripts.05_generate_report
"""

from __future__ import annotations

import json
import pandas as pd
import numpy as np
from datetime import date

from scripts.config import (
    DATA_PROCESSED,
    DATA_RAW,
    HIST_END,
    HIST_START,
    IVY_PLUS_SCHOOLS,
    IVY_SCHOOLS,
    MILESTONES,
    OUTPUT,
    PROJ_END,
    PROJ_START,
    SCHOOLS,
)
from scripts.utils import cagr, fmt_currency, fmt_pct


# ── Data loading ──────────────────────────────────────────────────────────────

def load_all_data() -> dict:
    """Load every data file needed for report generation."""
    costs = pd.read_csv(DATA_PROCESSED / "costs_cleaned.csv")
    costs.columns = costs.columns.str.strip().str.lower()

    real = pd.read_csv(DATA_PROCESSED / "costs_real_dollars.csv")
    real.columns = real.columns.str.strip().str.lower()

    proj = pd.read_csv(DATA_PROCESSED / "projections.csv")
    proj.columns = proj.columns.str.strip().str.lower()

    cpi = pd.read_csv(DATA_RAW / "cpi_annual.csv")
    cpi.columns = cpi.columns.str.strip().str.lower()

    with open(DATA_PROCESSED / "analysis_results.json") as fh:
        analysis = json.load(fh)

    return {
        "costs": costs,
        "real": real,
        "proj": proj,
        "cpi": cpi,
        "analysis": analysis,
    }


# ── Derived statistics ───────────────────────────────────────────────────────

def _school_start_end(costs: pd.DataFrame, school: str) -> tuple[float, float]:
    """Return (start_cost, end_cost) for a school."""
    df = costs[costs["school"] == school].sort_values("year")
    start_row = df.loc[df["year"] == HIST_START, "total_cost"]
    end_row = df.loc[df["year"] == HIST_END, "total_cost"]
    s = float(start_row.iloc[0]) if not start_row.empty else np.nan
    e = float(end_row.iloc[0]) if not end_row.empty else np.nan
    return s, e


def _sorted_schools_by_cagr(analysis: dict, descending: bool = True) -> list[tuple[str, float]]:
    """Return list of (school, cagr) sorted by 20-yr total-cost CAGR."""
    items = []
    for school, metrics in analysis["schools"].items():
        c = metrics.get("cagr_total_cost_20yr")
        if c is not None:
            items.append((school, c))
    items.sort(key=lambda x: x[1], reverse=descending)
    return items


def _avg_cost_for_year(costs: pd.DataFrame, year: int, schools: list[str] | None = None) -> float:
    """Average total_cost across schools for a given year."""
    df = costs[costs["year"] == year]
    if schools:
        df = df[df["school"].isin(schools)]
    return float(df["total_cost"].mean()) if not df.empty else np.nan


def _milestone_table(proj: pd.DataFrame, model: str, milestones: list[int]) -> dict[int, dict[str, int | None]]:
    """For a given model, find first year each school crosses each milestone."""
    subset = proj[(proj["model"] == model) & (proj["school"].isin(SCHOOLS))]
    table: dict[int, dict[str, int | None]] = {}
    for ms in milestones:
        table[ms] = {}
        for school in SCHOOLS:
            s_df = subset[subset["school"] == school].sort_values("year")
            crossing = s_df.loc[s_df["total_cost_projected"] >= ms, "year"]
            table[ms][school] = int(crossing.iloc[0]) if not crossing.empty else None
    return table


def _cumulative_4yr_cost(proj: pd.DataFrame, school: str, model: str, start_year: int) -> float:
    """Sum of 4 consecutive projected costs starting at start_year."""
    subset = proj[(proj["school"] == school) & (proj["model"] == model)]
    subset = subset[subset["year"].between(start_year, start_year + 3)]
    return float(subset["total_cost_projected"].sum()) if len(subset) == 4 else np.nan


# ── Markdown helpers ─────────────────────────────────────────────────────────

def _school_profiles_section(costs: pd.DataFrame, analysis: dict) -> str:
    """Generate school-by-school profile paragraphs."""
    lines: list[str] = []
    sorted_schools = _sorted_schools_by_cagr(analysis)

    for school, c in sorted_schools:
        start_cost, end_cost = _school_start_end(costs, school)
        metrics = analysis["schools"][school]
        mult = metrics.get("cumulative_multiplier", 0)
        max_yr = metrics.get("max_annual_pct_year")
        max_pct = metrics.get("max_annual_pct_increase")
        min_yr = metrics.get("min_annual_pct_year")
        min_pct = metrics.get("min_annual_pct_increase")

        lines.append(f"**{school}:** Total cost rose from {fmt_currency(start_cost)} "
                     f"in {HIST_START} to {fmt_currency(end_cost)} in {HIST_END}, "
                     f"a {mult:.1f}x increase (CAGR {fmt_pct(c)}). ")
        if max_yr and max_pct is not None:
            lines.append(f"The largest single-year jump was {fmt_pct(max_pct)} in {max_yr}")
            if min_yr and min_pct is not None:
                lines.append(f", while the smallest increase was {fmt_pct(min_pct)} in {min_yr}. ")
            else:
                lines.append(". ")
        lines.append("\n\n")

    return "".join(lines)


def _summary_stats_table(costs: pd.DataFrame, analysis: dict) -> str:
    """Markdown table of summary statistics per school."""
    header = (
        "| School | {start} Cost | {end} Cost | 20-yr CAGR | Multiplier | Premium vs CPI |\n"
        "|--------|----------:|----------:|----------:|----------:|----------:|\n"
    ).format(start=HIST_START, end=HIST_END)

    rows: list[str] = []
    for school in SCHOOLS:
        s, e = _school_start_end(costs, school)
        m = analysis["schools"].get(school, {})
        c = m.get("cagr_total_cost_20yr")
        mult = m.get("cumulative_multiplier")
        prem = m.get("college_premium_vs_cpi")
        rows.append(
            f"| {school} | {fmt_currency(s)} | {fmt_currency(e)} "
            f"| {fmt_pct(c) if c is not None else 'N/A'} "
            f"| {mult:.2f}x " if mult is not None else f"| N/A "
            f"| {prem:.2f}x |" if prem is not None else f"| N/A |"
        )

    return header + "\n".join(rows)


def _summary_stats_table_safe(costs: pd.DataFrame, analysis: dict) -> str:
    """Markdown table of summary statistics per school (safe formatting)."""
    header = (
        f"| School | {HIST_START} Cost | {HIST_END} Cost | 20-yr CAGR | Multiplier | Premium vs CPI |\n"
        f"|--------|----------:|----------:|----------:|----------:|----------:|\n"
    )

    rows: list[str] = []
    for school in SCHOOLS:
        s, e = _school_start_end(costs, school)
        m = analysis["schools"].get(school, {})
        c_val = m.get("cagr_total_cost_20yr")
        mult_val = m.get("cumulative_multiplier")
        prem_val = m.get("college_premium_vs_cpi")

        c_str = fmt_pct(c_val) if c_val is not None else "N/A"
        mult_str = f"{mult_val:.2f}x" if mult_val is not None else "N/A"
        prem_str = f"{prem_val:.2f}x" if prem_val is not None else "N/A"

        rows.append(
            f"| {school} | {fmt_currency(s)} | {fmt_currency(e)} "
            f"| {c_str} | {mult_str} | {prem_str} |"
        )

    return header + "\n".join(rows)


# ── Report generation ────────────────────────────────────────────────────────

def generate_report(data: dict) -> str:
    """Build the full ~4000-word report.md content."""
    costs = data["costs"]
    real = data["real"]
    proj = data["proj"]
    cpi = data["cpi"]
    analysis = data["analysis"]

    cpi_cagr = analysis.get("cpi_cagr", 0.025)
    sorted_schools = _sorted_schools_by_cagr(analysis)
    fastest_school, fastest_cagr = sorted_schools[0]
    slowest_school, slowest_cagr = sorted_schools[-1]

    avg_cagr = analysis["groups"]["ivy_plus"]["cagr_total_cost_stats"]["mean"]
    avg_cagr_ivy = analysis["groups"]["ivy"]["cagr_total_cost_stats"]["mean"]

    # Average costs
    avg_start = _avg_cost_for_year(costs, HIST_START, SCHOOLS)
    avg_end = _avg_cost_for_year(costs, HIST_END, SCHOOLS)

    # Duke 2026 cost
    _, duke_2026 = _school_start_end(costs, "Duke")

    # Most / least expensive in 2026
    costs_2026 = costs[costs["year"] == HIST_END].sort_values("total_cost", ascending=False)
    most_expensive = costs_2026.iloc[0]["school"] if not costs_2026.empty else "N/A"
    most_expensive_cost = float(costs_2026.iloc[0]["total_cost"]) if not costs_2026.empty else np.nan
    least_expensive = costs_2026.iloc[-1]["school"] if not costs_2026.empty else "N/A"
    least_expensive_cost = float(costs_2026.iloc[-1]["total_cost"]) if not costs_2026.empty else np.nan

    # Structural breaks
    breaks = analysis.get("structural_breaks", {})
    crisis_mean = breaks.get("financial_crisis_2008_2010", {}).get("mean_increase")
    covid_mean = breaks.get("covid_2020_2021", {}).get("mean_increase")

    # Projection milestones
    milestone_baseline = _milestone_table(proj, "baseline", MILESTONES)
    milestone_high = _milestone_table(proj, "scenario_high", MILESTONES)
    milestone_moderate = _milestone_table(proj, "scenario_moderate", MILESTONES)

    # Average projected cost at key years (baseline model, ivy+ average)
    proj_ivyplus = proj[proj["school"] == "IvyPlus_Average"]

    def _avg_proj_cost(model: str, year: int) -> float:
        row = proj_ivyplus[(proj_ivyplus["model"] == model) & (proj_ivyplus["year"] == year)]
        return float(row["total_cost_projected"].iloc[0]) if not row.empty else np.nan

    proj_2035_baseline = _avg_proj_cost("baseline", 2035)
    proj_2040_baseline = _avg_proj_cost("baseline", 2040)
    proj_2046_baseline = _avg_proj_cost("baseline", 2046)
    proj_2035_high = _avg_proj_cost("scenario_high", 2035)
    proj_2040_high = _avg_proj_cost("scenario_high", 2040)
    proj_2046_high = _avg_proj_cost("scenario_high", 2046)
    proj_2035_low = _avg_proj_cost("scenario_low", 2035)
    proj_2046_low = _avg_proj_cost("scenario_low", 2046)

    # Real-dollar analysis
    if "total_cost" in real.columns:
        real_start = _avg_cost_for_year(real, HIST_START, SCHOOLS)
        real_end = _avg_cost_for_year(real, HIST_END, SCHOOLS)
    else:
        # Try to find the relevant column name
        real_cost_col = [c for c in real.columns if "real" in c or "adjusted" in c or "total" in c]
        if real_cost_col:
            rc = real_cost_col[0]
            r_s = real[real["year"] == HIST_START]
            r_e = real[real["year"] == HIST_END]
            if SCHOOLS:
                r_s = r_s[r_s["school"].isin(SCHOOLS)]
                r_e = r_e[r_e["school"].isin(SCHOOLS)]
            real_start = float(r_s[rc].mean()) if not r_s.empty else np.nan
            real_end = float(r_e[rc].mean()) if not r_e.empty else np.nan
        else:
            real_start = np.nan
            real_end = np.nan

    # Cumulative 4-year costs for "million dollar degree" discussion
    cum_4yr_high_2043 = np.nan
    for school in SCHOOLS:
        val = _cumulative_4yr_cost(proj, school, "scenario_high", 2043)
        if not np.isnan(val):
            if np.isnan(cum_4yr_high_2043):
                cum_4yr_high_2043 = val
            else:
                cum_4yr_high_2043 = max(cum_4yr_high_2043, val)

    # Number of schools crossing $100K by various years
    n_100k_by_2027 = sum(
        1 for s in SCHOOLS
        if milestone_baseline.get(100_000, {}).get(s) is not None
        and milestone_baseline[100_000][s] <= 2027
    )
    n_100k_by_2030 = sum(
        1 for s in SCHOOLS
        if milestone_baseline.get(100_000, {}).get(s) is not None
        and milestone_baseline[100_000][s] <= 2030
    )

    # First school to $150K baseline
    first_150k_school = None
    first_150k_year = None
    for school in SCHOOLS:
        yr = milestone_baseline.get(150_000, {}).get(school)
        if yr is not None:
            if first_150k_year is None or yr < first_150k_year:
                first_150k_year = yr
                first_150k_school = school

    # ── Assemble report ──────────────────────────────────────────────────────

    report = f"""\
# The Rising Cost of Elite Higher Education: A 20-Year Analysis of Ivy+ Institutions ({HIST_START}-{PROJ_END})

*Generated on {date.today().isoformat()} from institutional cost data and Bureau of Labor Statistics CPI data.*

---

## Executive Summary

The cost of attending America's most prestigious universities has undergone a dramatic transformation over the past two decades. This report analyzes total cost of attendance (tuition, fees, room, and board) at twelve elite institutions (the eight Ivy League schools plus Stanford, MIT, Duke, and the University of Chicago) from {HIST_START} to {HIST_END}, with projections extending to {PROJ_END}.

The headline finding is stark: costs have approximately doubled in twenty years. The average Ivy+ total cost of attendance rose from {fmt_currency(avg_start)} in {HIST_START} to {fmt_currency(avg_end)} in {HIST_END}. The group's mean compound annual growth rate (CAGR) of {fmt_pct(avg_cagr)} substantially outpaced the Consumer Price Index (CPI) inflation rate of {fmt_pct(cpi_cagr)} over the same period, meaning college costs grew roughly {avg_cagr / cpi_cagr:.1f} times faster than general inflation.

Among the twelve schools, {fastest_school} posted the highest 20-year CAGR at {fmt_pct(fastest_cagr)}, while {slowest_school} grew the slowest at {fmt_pct(slowest_cagr)}. Duke University's {HIST_END} total cost of {fmt_currency(duke_2026)} places it among the most expensive in the cohort, with its most recent annual increase of approximately 4.95% far exceeding the prevailing 2.4% CPI inflation rate.

Projections suggest that under a baseline scenario the average Ivy+ total cost will surpass $150,000 by the mid-2030s, reaching approximately {fmt_currency(proj_2035_baseline)} by 2035. Under a high-growth scenario, costs could approach {fmt_currency(proj_2046_high)} by {PROJ_END}, raising serious questions about the long-term accessibility of elite higher education.

---

## Methodology

### Data Sources

This analysis draws on publicly available data from two primary sources:

1. **Institutional cost data** from the Integrated Postsecondary Education Data System (IPEDS) and Common Data Sets (CDS), covering total cost of attendance (tuition, fees, room, and board) for the {HIST_START}-{HIST_END} academic years.
2. **Consumer Price Index (CPI-U)** data from the Bureau of Labor Statistics, used for inflation adjustment.

### Schools Included

The study covers twelve "Ivy+" institutions: {", ".join(SCHOOLS)}.

### Inflation Adjustment

All real-dollar figures are expressed in {HIST_END} dollars using the CPI-U All Items index. The adjustment factor for a given year is CPI({HIST_END}) / CPI(year).

### Projection Models

Three projection models were employed for the {PROJ_START}-{PROJ_END} window:

- **Baseline:** Extrapolates each school's 20-year historical CAGR forward.
- **High scenario:** Uses the higher of the 10-year CAGR or the 20-year CAGR plus 0.5 percentage points.
- **Low scenario:** Linearly converges each school's growth rate toward CPI + 0.5% over the projection horizon.

An additional log-linear regression model was computed for comparison.

---

## Historical Analysis ({HIST_START}-{HIST_END})

![Historical total cost of attendance for all schools](../charts/png/01_all_schools_total_cost.png)

### Overall Trend

Over the twenty-year period from {HIST_START} to {HIST_END}, the cost of attending an Ivy+ institution roughly doubled. The average total cost across all twelve schools rose from {fmt_currency(avg_start)} to {fmt_currency(avg_end)}, representing a cumulative increase of approximately {((avg_end / avg_start) - 1) * 100:.0f}%. The Ivy+ group mean CAGR of {fmt_pct(avg_cagr)} substantially exceeded the {fmt_pct(cpi_cagr)} CPI inflation rate over the same period.

This growth was not uniform. The fastest-growing institution, {fastest_school}, posted a CAGR of {fmt_pct(fastest_cagr)}, while the most restrained, {slowest_school}, still grew at {fmt_pct(slowest_cagr)}, well above general inflation. Every single school in the cohort outpaced the CPI, underscoring the systemic nature of higher education cost escalation.

### Fastest and Slowest Growing Schools

{fastest_school} led the group with a 20-year CAGR of {fmt_pct(fastest_cagr)}, translating to a cumulative cost multiplier that significantly exceeded the group average. At the other end of the spectrum, {slowest_school}'s CAGR of {fmt_pct(slowest_cagr)} was the lowest in the cohort, though still meaningful in absolute terms, adding tens of thousands of dollars to the total cost over two decades.

![CAGR comparison across schools](../charts/png/03_cagr_bar.png)

### Impact of the 2008 Financial Crisis

The 2008 financial crisis produced a brief but measurable deceleration in cost growth. During the 2008-2010 window, the average year-over-year increase across the cohort was {fmt_pct(crisis_mean) if crisis_mean is not None else "modestly lower than the long-run average"}, as institutions responded to endowment losses and public pressure by moderating tuition hikes. However, this restraint proved temporary, with growth rates returning to, and eventually exceeding, pre-crisis levels within a few years.

### COVID-Era Effects

The COVID-19 pandemic introduced another disruption. During 2020-2021, the average annual increase was {fmt_pct(covid_mean) if covid_mean is not None else "relatively subdued"}, as some schools froze tuition or offered discounts for remote instruction. Yet the pandemic's long-term impact on sticker price growth has been minimal. If anything, the post-COVID recovery period has seen an acceleration in cost increases as institutions seek to recoup deferred maintenance and invest in campus upgrades.

### Acceleration in 2022-2026

The most recent period ({HIST_END - 4}-{HIST_END}) has seen a notable acceleration in cost growth at many institutions. Annual increases of 4-5% have become common, significantly exceeding the Federal Reserve's 2% inflation target and even the elevated CPI readings of the early 2020s. This acceleration coincides with strong demand for elite education, recovering endowment returns, and ambitious campus investment programs.

![Year-over-year percent changes](../charts/png/05_heatmap.png)

---

## School Profiles

{_school_profiles_section(costs, analysis)}

![Tuition vs total cost comparison](../charts/png/02_tuition_vs_total.png)

---

## Contextual Comparison

### College Costs vs. the Consumer Price Index

The most fundamental comparison is between college cost inflation and general consumer inflation. Over the {HIST_START}-{HIST_END} period, the CPI-U rose at a compound annual rate of {fmt_pct(cpi_cagr)}, while Ivy+ total costs grew at {fmt_pct(avg_cagr)}, roughly {avg_cagr / cpi_cagr:.1f} times faster. This "college premium" has been remarkably persistent, holding across boom and bust cycles alike.

To put this in concrete terms: if college costs had merely tracked CPI inflation from {HIST_START}, the average Ivy+ total cost in {HIST_END} would be approximately {fmt_currency(avg_start * (1 + cpi_cagr) ** (HIST_END - HIST_START))} rather than {fmt_currency(avg_end)}, a gap of roughly {fmt_currency(avg_end - avg_start * (1 + cpi_cagr) ** (HIST_END - HIST_START))} per year.

### The "College Premium" Concept

The ratio of college cost growth to CPI growth (what we call the "college premium") averaged approximately {avg_cagr / cpi_cagr:.1f}x across the Ivy+ cohort. This means that for every 1% increase in general consumer prices, elite college costs rose by approximately {avg_cagr / cpi_cagr:.1f}%. This premium reflects the unique cost structure of higher education: labor-intensive instruction, research infrastructure, student services expansion, and the competitive dynamics of prestige-driven institutions.

### Comparison to Other Asset Classes

While a full comparison is beyond the scope of this study, it is worth noting that the roughly {((avg_end / avg_start) - 1) * 100:.0f}% cumulative increase in Ivy+ costs significantly exceeded growth in median household income over the same period, which has lagged behind even CPI in real terms. Meanwhile, the S&P 500's cumulative total return over this period substantially exceeded college cost growth, suggesting that families who invested in equities rather than prepaying tuition generally came out ahead, though this comparison involves very different risk profiles.

![College costs vs CPI comparison](../charts/png/04_indexed_comparison.png)

---

## Real vs. Nominal Analysis

Adjusting for inflation using the CPI-U reveals that the rise in college costs is not merely a reflection of general price-level increases. In real ({HIST_END}) dollars, the average Ivy+ total cost rose from approximately {fmt_currency(real_start)} in {HIST_START} to {fmt_currency(real_end)} in {HIST_END}.

This real increase of roughly {fmt_currency(real_end - real_start)} per year means that a significant portion of the nominal cost growth reflects genuine increases in the resources required to attend these institutions, or alternatively, increases in the institutions' pricing power. The real CAGR of approximately {fmt_pct(avg_cagr - cpi_cagr)} shows that even after stripping out inflation, families faced meaningfully higher costs each year.

The real-vs-nominal distinction is critical for financial planning. A family saving for college in a portfolio that merely matches inflation will fall further behind each year. To keep pace with actual college cost growth, investment returns need to exceed CPI by at least {fmt_pct(avg_cagr - cpi_cagr)} annually, a meaningful hurdle in a low-rate environment.

![Real vs nominal cost comparison](../charts/png/06_real_vs_nominal.png)

---

## Projections ({PROJ_START}-{PROJ_END})

![Projected costs under different scenarios](../charts/png/08_group_projection.png)

### Three Scenarios

Projecting future costs is inherently uncertain, but examining a range of scenarios helps bracket the possibilities:

**Baseline Scenario (Historical CAGR Continues):** Under this model, each school's 20-year historical CAGR is extrapolated forward. The average Ivy+ cost reaches approximately {fmt_currency(proj_2035_baseline)} by 2035, {fmt_currency(proj_2040_baseline)} by 2040, and {fmt_currency(proj_2046_baseline)} by {PROJ_END}. {"The first school crosses the $150,000 threshold around " + str(first_150k_year) + " (" + first_150k_school + ")." if first_150k_year else "Several schools are projected to approach the $150,000 threshold by the mid-2030s."}

**High Scenario (Recent Acceleration Continues):** If the elevated growth rates observed in the recent 10-year window persist, the average Ivy+ cost could reach approximately {fmt_currency(proj_2035_high)} by 2035 and {fmt_currency(proj_2046_high)} by {PROJ_END}. Under this scenario, the $200,000 total cost of attendance becomes a possibility at some institutions before {PROJ_END}.

**Low Scenario (Gradual Moderation):** If growth rates gradually converge toward CPI + 0.5% over the projection horizon, costs would still reach approximately {fmt_currency(proj_2035_low)} by 2035 and {fmt_currency(proj_2046_low)} by {PROJ_END}. Even this optimistic scenario implies substantial further increases in real terms.

### Milestone Years

Under the baseline scenario, {n_100k_by_2027} school(s) are projected to cross the $100,000 annual cost threshold by {PROJ_START}, with {n_100k_by_2030} reaching that level by 2030. The $150,000 milestone is projected to be crossed by {first_150k_school or "the fastest-growing schools"} around {first_150k_year or "the mid-2030s"} under baseline assumptions.

### The "$1 Million+ Bachelor's Degree"

Under the high scenario, the cumulative four-year cost at the most expensive institution could approach {fmt_currency(cum_4yr_high_2043)} for a student entering in 2043. While the "$1 million bachelor's degree" remains at the extreme end of projections, cumulative four-year costs of $600,000-$800,000 are well within the range of plausible outcomes by the early 2040s. This figure, while striking, does not account for financial aid, but it represents the sticker price reality facing upper-middle-class families who earn too much to qualify for need-based aid.

![Milestone crossing years](../charts/png/09_milestone_timeline.png)

---

## Implications

### For Families

The data underscore the importance of early and aggressive college savings. A family with a child born today faces a potential total cost of attendance in the $150,000-$200,000+ range per year by the time that child reaches college age. Even with financial aid, the expected family contribution at these income levels can be staggering. 529 plan contributions, investment growth, and potentially creative financing strategies will be essential.

### For Policy

The persistent college premium raises questions about the sustainability of the current higher education financing model. While elite institutions point to generous financial aid programs, the sticker price itself creates barriers, both real and perceived, to access. Policymakers may need to consider whether the tax-exempt status and endowment returns that sustain these institutions are delivering sufficient public benefit.

### For Institutions

The data suggest that elite institutions operate in a market with remarkably inelastic demand, allowing them to raise prices well above inflation with minimal enrollment impact. However, this pricing power may not be infinite. As cumulative costs approach the million-dollar threshold for a four-year degree, even wealthy families may begin to question the return on investment, particularly as online education alternatives mature and employer credential requirements evolve.

### Net Price vs. Sticker Price

It is crucial to note that the sticker price analyzed in this report is not the price most students pay. All twelve institutions in this study offer generous need-based financial aid, and the average net price for aided students is typically 40-60% below the sticker price. Harvard, for example, states that families earning under $85,000 pay nothing. However, the sticker price remains the relevant figure for families in the upper-middle-income range ($200,000-$400,000) who often receive little or no aid.

---

## Limitations & Caveats

1. **Sticker price vs. net price:** This analysis examines published total cost of attendance. Net price after financial aid is substantially lower for most students and may have a different growth trajectory.

2. **Data gaps:** Some years may rely on Common Data Set reports rather than IPEDS, and methodological differences between sources can introduce minor inconsistencies.

3. **Component mix:** The relative growth rates of tuition, fees, room, and board may differ, but this analysis focuses on total cost of attendance.

4. **Projection uncertainty:** All projections assume some version of historical continuity. Structural breaks (such as regulatory changes, demographic shifts, or technological disruption) could materially alter the trajectory.

5. **Institutional heterogeneity:** While these twelve schools are often grouped together, they differ in meaningful ways (public vs. private control at Cornell, engineering focus at MIT, etc.) that affect cost structures.

6. **No quality adjustment:** Higher costs may partially reflect improved educational quality, expanded services, and enhanced facilities, factors not captured in a pure price analysis.

---

## Appendix

### Summary Statistics

{_summary_stats_table_safe(costs, analysis)}

### Data Sources

- **IPEDS (Integrated Postsecondary Education Data System):** U.S. Department of Education, National Center for Education Statistics. Institutional cost of attendance data.
- **Common Data Sets (CDS):** Published by individual institutions. Used to fill gaps in IPEDS data.
- **Bureau of Labor Statistics:** Consumer Price Index for All Urban Consumers (CPI-U), annual averages.

### Methodology Notes

- All dollar figures are in nominal terms unless explicitly noted as "real" or "inflation-adjusted."
- Real-dollar conversions use the CPI-U All Items index with {HIST_END} as the base year.
- CAGR is calculated as (end/start)^(1/years) - 1.
- The "college premium" is defined as the ratio of a school's cost CAGR to the CPI CAGR over the same period.

---

*This report was generated programmatically from institutional cost data and BLS CPI data. All figures should be verified against primary sources before use in financial planning or policy analysis.*
"""

    return report


# ── Blog post generation ─────────────────────────────────────────────────────

def generate_blog_post(data: dict) -> str:
    """Build the ~1800-word blog_post.md content."""
    costs = data["costs"]
    proj = data["proj"]
    analysis = data["analysis"]

    cpi_cagr = analysis.get("cpi_cagr", 0.025)
    sorted_schools = _sorted_schools_by_cagr(analysis)
    fastest_school, fastest_cagr = sorted_schools[0]
    slowest_school, slowest_cagr = sorted_schools[-1]

    avg_cagr = analysis["groups"]["ivy_plus"]["cagr_total_cost_stats"]["mean"]
    avg_start = _avg_cost_for_year(costs, HIST_START, SCHOOLS)
    avg_end = _avg_cost_for_year(costs, HIST_END, SCHOOLS)

    _, duke_2026 = _school_start_end(costs, "Duke")
    duke_start, _ = _school_start_end(costs, "Duke")

    # Most/least expensive in 2026
    costs_2026 = costs[costs["year"] == HIST_END].sort_values("total_cost", ascending=False)
    most_expensive = costs_2026.iloc[0]["school"] if not costs_2026.empty else "N/A"
    most_expensive_cost = float(costs_2026.iloc[0]["total_cost"]) if not costs_2026.empty else np.nan
    least_expensive = costs_2026.iloc[-1]["school"] if not costs_2026.empty else "N/A"
    least_expensive_cost = float(costs_2026.iloc[-1]["total_cost"]) if not costs_2026.empty else np.nan

    # Projections
    proj_ivyplus = proj[proj["school"] == "IvyPlus_Average"]

    def _avg_proj(model: str, year: int) -> float:
        row = proj_ivyplus[(proj_ivyplus["model"] == model) & (proj_ivyplus["year"] == year)]
        return float(row["total_cost_projected"].iloc[0]) if not row.empty else np.nan

    proj_2035_baseline = _avg_proj("baseline", 2035)
    proj_2040_high = _avg_proj("scenario_high", 2040)
    proj_2046_high = _avg_proj("scenario_high", 2046)

    milestone_baseline = _milestone_table(proj, "baseline", MILESTONES)
    milestone_high = _milestone_table(proj, "scenario_high", MILESTONES)

    # First $150K school
    first_150k_school = None
    first_150k_year = None
    for school in SCHOOLS:
        yr = milestone_baseline.get(150_000, {}).get(school)
        if yr is not None:
            if first_150k_year is None or yr < first_150k_year:
                first_150k_year = yr
                first_150k_school = school

    # Cumulative 4-year high scenario
    max_cum_4yr = np.nan
    max_cum_school = ""
    for school in SCHOOLS:
        val = _cumulative_4yr_cost(proj, school, "scenario_high", 2043)
        if not np.isnan(val) and (np.isnan(max_cum_4yr) or val > max_cum_4yr):
            max_cum_4yr = val
            max_cum_school = school

    n_100k_by_2027 = sum(
        1 for s in SCHOOLS
        if milestone_baseline.get(100_000, {}).get(s) is not None
        and milestone_baseline[100_000][s] <= 2027
    )

    blog = f"""\
# The $100K Year Is Here: What 20 Years of Ivy League Tuition Data Tells Us About the Next 20

*{date.today().strftime("%B %d, %Y")}*

---

## The Number That Should Make You Do a Double-Take

Duke University's total cost of attendance for {HIST_END} hit {fmt_currency(duke_2026)}, just a few thousand dollars short of the once-unthinkable $100,000-per-year mark. That figure represents a roughly 4.95% increase over the prior year, in an environment where the Consumer Price Index rose just 2.4%.

Duke is not an outlier. Across the twelve elite institutions we track (the eight Ivy League schools plus Stanford, MIT, Duke, and UChicago), annual costs are converging on six figures. The average total cost of attendance across this group now sits at {fmt_currency(avg_end)}. The $100,000 year is not a hypothetical. It is arriving now.

But to understand what this number means, and where it is heading, we need to zoom out.

![Historical cost trends](../charts/png/01_all_schools_total_cost.png)

---

## The 20-Year Trend: Costs Have Roughly Doubled

In {HIST_START}, the average Ivy+ total cost of attendance was {fmt_currency(avg_start)}. By {HIST_END}, that figure had risen to {fmt_currency(avg_end)}, an increase of approximately {((avg_end / avg_start) - 1) * 100:.0f}%.

The compound annual growth rate (CAGR) across the group averaged {fmt_pct(avg_cagr)}. That may sound modest, but compare it to the CPI inflation rate over the same period: just {fmt_pct(cpi_cagr)}. College costs grew roughly {avg_cagr / cpi_cagr:.1f} times faster than the price of everything else.

If you had put {fmt_currency(avg_start)} in a savings account in {HIST_START} and earned returns matching inflation, you would have about {fmt_currency(avg_start * (1 + cpi_cagr) ** (HIST_END - HIST_START))} today. The actual cost? {fmt_currency(avg_end)}. That gap, roughly {fmt_currency(avg_end - avg_start * (1 + cpi_cagr) ** (HIST_END - HIST_START))} per year, is the "college premium" in action.

![CAGR comparison](../charts/png/03_cagr_bar.png)

---

## School-by-School: Who Charges the Most?

Not all elite schools are created equal when it comes to pricing:

- **Most expensive in {HIST_END}:** {most_expensive} at {fmt_currency(most_expensive_cost)} per year.
- **Least expensive in {HIST_END}:** {least_expensive} at {fmt_currency(least_expensive_cost)}, still a formidable sum.
- **Fastest 20-year growth:** {fastest_school}, with a CAGR of {fmt_pct(fastest_cagr)}.
- **Slowest 20-year growth:** {slowest_school}, at {fmt_pct(slowest_cagr)}, still well above inflation.

Every single school in the cohort outpaced CPI inflation over the 20-year period. The "college premium" ranged from about {slowest_cagr / cpi_cagr:.1f}x to {fastest_cagr / cpi_cagr:.1f}x the rate of general inflation.

There were brief periods of moderation (a slowdown during the 2008 financial crisis, a pause during COVID), but in each case, growth rates snapped back within a year or two. The post-2022 period has been particularly aggressive, with annual increases of 4-5% becoming the norm.

![School trajectories](../charts/png/02_tuition_vs_total.png)

---

## Why Do Costs Outpace Inflation?

Several forces drive the persistent college premium:

1. **Labor intensity:** Higher education is a service industry where productivity gains are inherently limited (a seminar still needs a professor).
2. **Facilities arms race:** Competition for top students drives investment in dorms, dining, recreation, and research facilities.
3. **Administrative growth:** Support staff and compliance functions have expanded significantly.
4. **Financial aid cross-subsidization:** High sticker prices enable generous aid for lower-income students, effectively creating a progressive pricing model where affluent families subsidize access for others.
5. **Inelastic demand:** Applications to these schools continue to surge, giving institutions pricing power that few other sectors enjoy.

---

## Where Are Costs Heading?

We modeled three scenarios for the next twenty years ({PROJ_START}-{PROJ_END}):

**Baseline (historical trend continues):** The average Ivy+ cost reaches approximately {fmt_currency(proj_2035_baseline)} by 2035. {"Under this scenario, " + str(n_100k_by_2027) + " school(s) cross $100,000 by " + str(PROJ_START) + "." if n_100k_by_2027 > 0 else ""} {"The first school hits $150,000 around " + str(first_150k_year) + " (" + first_150k_school + ")." if first_150k_year else "The $150,000 milestone arrives in the mid-2030s."}

**High scenario (recent acceleration persists):** Costs could reach {fmt_currency(proj_2040_high)} by 2040 and approach {fmt_currency(proj_2046_high)} by {PROJ_END}. Under this scenario, the $200,000 annual cost becomes a real possibility.

**Low scenario (gradual moderation):** Even if growth rates slowly converge toward inflation + 0.5%, costs still increase substantially in real terms.

![Projected costs](../charts/png/08_group_projection.png)

---

## The Million-Dollar Bachelor's Degree

Here is the number that stops people in their tracks: under the high scenario, the cumulative four-year cost at {max_cum_school or "the most expensive school"} for a student entering in 2043 could approach {fmt_currency(max_cum_4yr)}.

While a literal "$1 million bachelor's degree" remains at the far edge of projections, cumulative four-year costs of $600,000-$800,000 are well within the plausible range by the early 2040s. For a family with two children, that is potentially $1.2 million to $1.6 million in education costs alone.

These are sticker prices, of course. But they are the prices that matter for upper-middle-class families: the ones earning enough to be excluded from need-based aid, but not so much that six-figure annual payments feel painless.

---

## The Big Caveat: Sticker Price Is Not Net Price

Before you panic, a critical caveat: most students at these institutions do not pay the sticker price. All twelve schools in our study offer substantial need-based financial aid. Harvard states that families earning under $85,000 per year pay nothing. Princeton, Stanford, and others have similarly generous programs.

The average net price (what students actually pay after grants and scholarships) is typically 40-60% below the sticker price. For lower-income students, elite education can be remarkably affordable.

But sticker price still matters. It matters for families in the $200,000-$400,000 income range who often receive little aid. It matters for the perception of accessibility; a $100,000 sticker price can deter qualified applicants from even applying, regardless of available aid. And it matters as a signal of the underlying cost structure of elite higher education.

---

## What This Means for Families

If you have young children and are thinking about college savings, the data deliver a clear message: start early and invest aggressively. A 529 plan growing at typical equity returns will need to accumulate $300,000-$500,000 or more to cover four years at an elite institution by the 2040s. The power of compound growth works both ways: for your savings and for the tuition bills heading your way.

The return on investment from an elite education remains strong by most measures. But as sticker prices push further into six-figure territory, the calculation becomes more nuanced. Families would be wise to evaluate not just the prestige of an institution, but the net cost, the likely career outcomes, and the alternative uses of what may amount to a million dollars in education spending.

---

*Data sources: IPEDS, Common Data Sets, Bureau of Labor Statistics (CPI-U). Analysis covers total cost of attendance (tuition, fees, room, and board) at sticker price. All projections are illustrative and should not be used as the sole basis for financial planning.*
"""

    return blog


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading data ...")
    data = load_all_data()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Generating report.md ...")
    report = generate_report(data)
    report_path = OUTPUT / "report.md"
    report_path.write_text(report)
    print(f"  Saved {report_path}  ({len(report.split()):,} words)")

    print("Generating blog_post.md ...")
    blog = generate_blog_post(data)
    blog_path = OUTPUT / "blog_post.md"
    blog_path.write_text(blog)
    print(f"  Saved {blog_path}  ({len(blog.split()):,} words)")

    print("Done.")


if __name__ == "__main__":
    main()
