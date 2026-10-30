"""One consistent chart style for every notebook.

Rules applied here (so each notebook does not repeat them):
- A colour belongs to an ENTITY (a category or a store), never to its rank,
  so "Electronics" is the same colour in every chart of the project.
- Thin bars, light recessive gridlines, no top/right spines, no dual axes.
- Money axes are formatted in KES (e.g. "KES 1.2M").
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from src import config

# Validated categorical palette (fixed order; colour-blind-safe for adjacent pairs).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
NEUTRAL = "#898781"        # muted ink for "other"/context series
HIGHLIGHT = SERIES[0]      # single-series charts use slot 1 (blue)
SEQUENTIAL = "Blues"       # one hue, light -> dark, for heatmaps
DIVERGING = "RdBu_r"       # two poles around a neutral midpoint

CATEGORY_COLORS = dict(zip(
    ["Food and Groceries", "Beverages", "Household Products",
     "Personal Care", "Clothing", "Electronics"], SERIES))

STORE_COLORS = dict(zip(
    ["Nairobi CBD", "Westlands", "Thika", "Mombasa Town", "Kisumu Town", "Nakuru Town"], SERIES))

INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "surface": "#fcfcfb"}


def apply_style():
    """Call once at the top of a notebook."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "figure.figsize": (10, 5),
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "figure.facecolor": INK["surface"],
        "axes.facecolor": INK["surface"],
        "axes.edgecolor": INK["axis"],
        "axes.labelcolor": INK["secondary"],
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK["primary"],
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": plt.cycler(color=SERIES),
        "grid.color": INK["grid"],
        "grid.linewidth": 0.6,
        "xtick.color": INK["muted"],
        "ytick.color": INK["muted"],
        "lines.linewidth": 2,
        "lines.markersize": 6,
        "legend.frameon": False,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    })


def kes(value, _pos=None):
    """Axis formatter: 1_250_000 -> 'KES 1.25M', 85_000 -> 'KES 85K'."""
    if abs(value) >= 1_000_000:
        return f"KES {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"KES {value / 1_000:.0f}K"
    return f"KES {value:.0f}"


KES_FORMATTER = mticker.FuncFormatter(kes)


def save(fig, name: str):
    """Save a figure into reports/figures/ (PNG) and return the path."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    return path
