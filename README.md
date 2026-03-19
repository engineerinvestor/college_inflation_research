# College Inflation Research

20-year analysis of cost-of-attendance at 12 elite "Ivy+" universities (2006-2026), with projections to 2046.

![Historical total cost of attendance](charts/png/01_all_schools_total_cost.png)

## Key Findings

- Average Ivy+ total cost of attendance roughly doubled from ~$44,000 (2006) to ~$94,000 (2026).
- The group's mean compound annual growth rate (CAGR) of ~3.8% ran roughly 1.6x faster than CPI inflation (~2.5%).
- Every school in the cohort outpaced CPI over the full 20-year period.
- Under a baseline projection, average costs surpass $150,000 by the mid-2030s.
- Under a high-growth scenario, cumulative four-year costs could approach $800,000+ by the early 2040s.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (scripts must execute in order)
python3 -m scripts.01_validate_data    # Clean raw data, adjust for inflation
python3 -m scripts.02_analyze          # Compute CAGRs, group stats, structural breaks
python3 -m scripts.03_project          # Generate 2027-2046 projections
python3 -m scripts.04_charts           # Render charts to charts/png/ and charts/svg/
python3 -m scripts.05_generate_report  # Assemble output/report.md and output/blog_post.md
```

Requires Python 3.10+.

## Project Structure

```
data/raw/             Source CSVs (tuition costs, CPI data)
data/processed/       Cleaned and derived datasets (generated)
scripts/              Pipeline scripts (01-05), config, and utilities
charts/png/           Publication-quality charts at 300 DPI (generated)
charts/svg/           Vector charts (generated)
output/               report.md and blog_post.md (generated)
```

## Data Sources

- **IPEDS** (Integrated Postsecondary Education Data System) for institutional cost data
- **Common Data Sets** published by individual institutions
- **Bureau of Labor Statistics** CPI-U annual averages for inflation adjustment

See `data/sources.md` for detailed per-school source notes.

## Caveats

All cost figures are **sticker prices** (published total cost of attendance: tuition, fees, room, and board). They do not reflect financial aid, grants, or scholarships. Most students at these institutions pay substantially less than sticker price. See the generated report for a full discussion of limitations.

## Citation

If you use this data or analysis in your own work, please cite:

```
@misc{engineerinvestor2026collegeplan,
  author       = {Engineer Investor},
  title        = {College Inflation Research: 20-Year Analysis of Ivy+ Cost of Attendance},
  year         = {2026},
  url          = {https://github.com/engineerinvestor/collegeplan}
}
```

## License

[MIT](LICENSE)
