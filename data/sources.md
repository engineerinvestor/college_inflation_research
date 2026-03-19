# Data Sources

## Overview

This document describes the sources used to compile cost-of-attendance and CPI data for the college inflation research project. All tuition, fees, room, and board figures represent published sticker prices and are not net of financial aid, grants, or scholarships. Data spans academic years 2005-06 through 2025-26 (or 2026, depending on the dataset) across 12 institutions.

Primary source categories:
- **IPEDS** (Integrated Postsecondary Education Data System) : institutional cost data reported annually to the federal government
- **Common Data Sets (CDS)** : standardized institutional data published annually by each school
- **University financial aid offices** : cost-of-attendance figures published for prospective students
- **University press releases and news offices** : announcements of tuition increases
- **Bureau of Labor Statistics (BLS)** : Consumer Price Index data

---

## Per-School Source Notes

### 1. Harvard University
- Primary: IPEDS Institutional Characteristics and Student Financial Aid surveys
- Secondary: Harvard Financial Aid Office cost-of-attendance pages (archived via Wayback Machine for pre-2015 years)
- Common Data Set filings (Section G: Annual Expenses), published on Harvard's Institutional Research site
- Some years between 2005 and 2010 required interpolation due to gaps in archived CDS filings

### 2. Yale University
- Primary: IPEDS data via the College Navigator tool
- Secondary: Yale Office of Undergraduate Admissions cost-of-attendance archives
- Common Data Set filings available on Yale's Institutional Research website
- Press releases from Yale News used to verify tuition increase announcements

### 3. Princeton University
- Primary: IPEDS Institutional Characteristics survey
- Secondary: Princeton's Office of Undergraduate Admission published cost summaries
- Common Data Set filings (Section G)
- Note: Princeton's comprehensive fee structure differs slightly from peers; room and board figures reflect standard double-occupancy dormitory and full meal plan

### 4. MIT (Massachusetts Institute of Technology)
- Primary: IPEDS data
- Secondary: MIT Student Financial Services cost-of-attendance archives
- Common Data Set filings published on MIT's Institutional Research site
- Press releases from MIT News Office for years with notable tuition changes

### 5. Stanford University
- Primary: IPEDS data via College Navigator
- Secondary: Stanford University Financial Aid Office cost pages (archived)
- Common Data Set filings (Section G), available on Stanford's Common Data Set archive
- Some early years (2005-2008) required interpolation from adjacent known values

### 6. University of Chicago
- Primary: IPEDS Institutional Characteristics survey
- Secondary: UChicago Financial Aid Office cost-of-attendance publications
- Common Data Set filings
- Press releases from UChicago News for tuition announcements

### 7. Columbia University
- Primary: IPEDS data
- Secondary: Columbia University Financial Aid and Educational Financing cost-of-attendance archives
- Common Data Set filings (Section G)
- Note: Columbia's tuition figures reflect the undergraduate Columbia College and Columbia Engineering rates, which are unified

### 8. University of Pennsylvania
- Primary: IPEDS data via College Navigator
- Secondary: Penn Student Registration & Financial Services cost pages (archived)
- Common Data Set filings published on Penn's Institutional Research website
- Some years required cross-referencing with archived press releases

### 9. Duke University
- Primary: IPEDS Institutional Characteristics survey
- Secondary: Duke Office of Undergraduate Financial Aid cost-of-attendance pages
- Common Data Set filings (Section G)
- Press releases from Duke Today for tuition increase announcements

### 10. Dartmouth College
- Primary: IPEDS data
- Secondary: Dartmouth Financial Aid Office cost-of-attendance archives
- Common Data Set filings available via Dartmouth's Institutional Research office
- Some years between 2005 and 2009 interpolated due to incomplete archived records

### 11. Brown University
- Primary: IPEDS Institutional Characteristics and Student Financial Aid surveys
- Secondary: Brown University Financial Aid Office published cost summaries
- Common Data Set filings (Section G)
- Press releases from Brown News for notable tuition changes

### 12. Cornell University
- Primary: IPEDS data via College Navigator
- Secondary: Cornell University Student Services cost-of-attendance archives
- Common Data Set filings published on Cornell's Institutional Research and Planning site
- Note: All figures reflect Endowed College rates (e.g., Arts & Sciences, Engineering); Cornell's statutory colleges (e.g., ILR, Human Ecology) carry different in-state/out-of-state tuition structures and are excluded

---

## CPI Data Sources

- **Source:** U.S. Bureau of Labor Statistics (BLS), Consumer Price Index for All Urban Consumers (CPI-U), U.S. City Average, All Items
- **Series ID:** CUUR0000SA0
- **URL:** https://www.bls.gov/cpi/
- **Data file:** `data/raw/cpi_annual.csv`
- **Coverage:** Annual averages, 2005-2026
- **2026 note:** The 2026 CPI-U value (327.3) and annual inflation rate (2.40%) are projected/estimated figures based on available data as of early 2026 and BLS forecasts. This value should be updated once the full-year 2026 annual average is published by BLS (typically in January of the following year).
- Annual inflation rates are calculated as the year-over-year percentage change: `(CPI_t - CPI_{t-1}) / CPI_{t-1}`. The 2005 rate is recorded as 0 (baseline year for this dataset).

---

## Notes on Data Quality and Interpolation

### Sticker Prices vs. Net Costs
All cost figures in this dataset represent published sticker prices: the full, undiscounted tuition, fees, room, and board as listed by each institution. They do not reflect:
- Institutional grant aid or need-based scholarships
- Merit scholarships
- Federal or state grants
- Net price (which can differ substantially from sticker price, particularly at high-endowment institutions)

Researchers should be aware that trends in sticker price inflation may not reflect the actual cost burden experienced by students, especially at schools with robust financial aid programs.

### Interpolation
For a subset of school-years, complete historical cost-of-attendance data was not available from primary sources. In these cases, values were linearly interpolated between the nearest available known data points. Affected institutions and approximate ranges:
- Harvard University: select years 2005-2010
- Stanford University: select years 2005-2008
- Dartmouth College: select years 2005-2009
- Brown University: isolated years, flagged in the processed dataset

Interpolated values are marked in the processed data files where applicable. Users should exercise caution when drawing conclusions from interpolated data points.

### IPEDS Reporting Lags and Revisions
IPEDS data is self-reported by institutions and is occasionally revised in subsequent years. Where IPEDS figures conflicted with CDS filings or institutional press releases, the more granular or recently revised figure was preferred, and a note was added to the relevant record.

### Academic Year vs. Calendar Year Alignment
Tuition data reflects academic years (e.g., AY 2022-23), while CPI data is reported on a calendar year basis. For inflation adjustment purposes, academic year costs are aligned to the calendar year in which the fall semester begins (e.g., AY 2022-23 is treated as calendar year 2022).
