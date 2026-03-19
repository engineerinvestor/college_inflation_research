# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research project analyzing 20 years (2006-2026) of cost-of-attendance data across 12 elite "Ivy+" universities, with projections to 2046. Produces analytical datasets, publication-quality charts (PNG + SVG), a formal research report, and a blog post.

## Commands

All scripts run from the project root as modules:

```bash
pip install -r requirements.txt

python3 -m scripts.01_validate_data    # Clean raw data, adjust for inflation
python3 -m scripts.02_analyze          # Compute CAGRs, group stats, structural breaks
python3 -m scripts.03_project          # Generate 2027-2046 projections (3 models)
python3 -m scripts.04_charts           # Render all charts to charts/png/ and charts/svg/
python3 -m scripts.05_generate_report  # Assemble output/report.md and output/blog_post.md
```

Scripts must run in order: each step depends on outputs from prior steps. Raw data lives in `data/raw/`; processed outputs go to `data/processed/`.

## Architecture

**Pipeline flow:** Raw CSVs → validate/clean → analyze → project → charts + reports

- `scripts/config.py`: Central configuration: school list, group definitions (IVY_SCHOOLS vs IVY_PLUS_SCHOOLS), color palette, file paths, time ranges, projection parameters, chart styling. All scripts import from here.
- `scripts/utils.py`: Shared functions: `cagr()`, `rolling_cagr()`, `fmt_currency()`, `fmt_pct()`, and data loaders (`load_tuition()`, `load_cleaned()`, `load_real()`, `load_projections()`, `load_cpi()`).
- Scripts 01-05 are numbered pipeline stages. Each reads from `data/` and writes outputs that downstream scripts consume.

**Key data contract:** `tuition_costs.csv` has one row per school per year (12 schools x 21 years = 252 rows). The `year` column is the academic year start (e.g., 2006 = 2006-07). School names must match `SCHOOLS` in config exactly (e.g., "UChicago" not "University of Chicago").

**Projection models** in `03_project.py`: baseline (historical CAGR), regression (log-linear OLS), and three scenarios (high/moderate/low). Projections include group averages stored as `Ivy_Average` and `IvyPlus_Average` pseudo-schools in the output CSV.

**Chart filenames** are referenced by `05_generate_report.py`. If chart names change in `04_charts.py`, the report generator's image paths must be updated to match.

## Data Caveats

All costs are **sticker price** (not net of financial aid). This distinction must be caveated in any output. CPI data uses BLS CPI-U annual averages. The 2026 CPI value is projected. Some historical tuition figures are interpolated where primary sources had gaps.

## Engineering Standards

- Python 3.10+ with type hints on all new and modified functions
- Formatting and linting: `ruff` (line-length 100, config in `pyproject.toml`)
- Type checking: `mypy` (config in `pyproject.toml`)
- Testing: `pytest` (tests live in `tests/`)
- Versioning: semver, tracked in `pyproject.toml`

## Git Configuration

- Remote: `git@github.com:engineerinvestor/college_inflation_research.git`
- Commit identity: use whatever is configured in the user's global git config
- Commit command format: `git commit -m "$(cat <<'EOF'\n<message>\n\nCo-Authored-By: ...\nEOF\n)"`

## Writing Style

- **No em-dashes.** Never use the em-dash character (U+2014, `—`) in any generated text, report templates, or documentation. Replace with the appropriate punctuation: comma, period, colon, semicolon, or parentheses.
