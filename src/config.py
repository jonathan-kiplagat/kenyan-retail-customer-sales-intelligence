"""Project-wide settings: paths, random seed and study period.

Every script and notebook imports paths from here, so the project runs on any
computer without editing hard-coded folders.
"""

from pathlib import Path

# Repository root = the folder that contains this "src" package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"

DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Fixed seed: running the generator twice produces identical CSV files.
RANDOM_SEED = 2024

# Study period covered by the sales data.
START_DATE = "2024-01-01"
END_DATE = "2025-12-31"

# The raw sales file must contain exactly this many rows (assignment requirement).
RAW_SALES_ROWS = 3000
