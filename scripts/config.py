"""Configuration: school metadata, file paths, chart styling."""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
CHARTS_PNG = PROJECT_ROOT / "charts" / "png"
CHARTS_SVG = PROJECT_ROOT / "charts" / "svg"
OUTPUT = PROJECT_ROOT / "output"

# ── Schools ────────────────────────────────────────────────────────────
SCHOOLS = [
    "Harvard",
    "Yale",
    "Princeton",
    "Columbia",
    "Penn",
    "Brown",
    "Cornell",
    "Dartmouth",
    "Stanford",
    "MIT",
    "Duke",
    "UChicago",
]

IVY_SCHOOLS = ["Harvard", "Yale", "Princeton", "Columbia", "Penn", "Brown", "Cornell", "Dartmouth"]
IVY_PLUS_SCHOOLS = SCHOOLS  # all 12

SCHOOL_COLORS = {
    "Harvard":    "#A51C30",
    "Yale":       "#00356B",
    "Princeton":  "#E77500",
    "Columbia":   "#B9D9EB",
    "Penn":       "#011F5B",
    "Brown":      "#4E3629",
    "Cornell":    "#B31B1B",
    "Dartmouth":  "#00693E",
    "Stanford":   "#8C1515",
    "MIT":        "#750014",
    "Duke":       "#003087",
    "UChicago":   "#800000",
}

# ── Time range ─────────────────────────────────────────────────────────
HIST_START = 2006
HIST_END = 2026
PROJ_START = 2027
PROJ_END = 2046

# ── Projection parameters ─────────────────────────────────────────────
CPI_PROJ_RATE = 0.025          # Fed long-run target
MILESTONES = [100_000, 150_000, 200_000]

# ── Chart styling ──────────────────────────────────────────────────────
CHART_DPI = 300
CHART_FIGSIZE = (12, 7)
CHART_FONT = "serif"
CHART_BG = "#FAFAFA"

CHART_STYLE = {
    "figure.figsize": CHART_FIGSIZE,
    "figure.dpi": CHART_DPI,
    "figure.facecolor": CHART_BG,
    "axes.facecolor": CHART_BG,
    "font.family": CHART_FONT,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "legend.fontsize": 9,
    "legend.framealpha": 0.9,
}
