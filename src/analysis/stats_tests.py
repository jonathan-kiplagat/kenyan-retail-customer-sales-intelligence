"""Hypothesis-testing helpers for Milestone 5.

Each function returns a plain dict or DataFrame so the notebook can show the
statistic, p-value, effect size and confidence interval side by side.
Significance level used throughout the project: ALPHA = 0.05.
"""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.oneway import anova_oneway

ALPHA = 0.05


# ---------------------------------------------------------------------------
# Assumption checks
# ---------------------------------------------------------------------------
def assumption_checks(groups: dict) -> pd.DataFrame:
    """Normality per group (Shapiro-Wilk + skewness) and equal variances (Levene).

    Shapiro-Wilk is very sensitive with large samples, so skewness is shown too:
    |skew| > 1 means the distribution is clearly asymmetric.
    """
    rows = []
    for name, values in groups.items():
        v = np.asarray(values, dtype=float)
        sample = v if len(v) <= 5000 else np.random.default_rng(0).choice(v, 5000, replace=False)
        rows.append({"group": name, "n": len(v), "mean": v.mean(), "median": np.median(v),
                     "std": v.std(ddof=1), "skewness": stats.skew(v),
                     "shapiro_p": stats.shapiro(sample).pvalue})
    table = pd.DataFrame(rows)
    table["normal_at_5pct"] = table["shapiro_p"] > ALPHA
    levene_p = stats.levene(*[np.asarray(v, dtype=float) for v in groups.values()], center="median").pvalue
    table.attrs["levene_p"] = levene_p          # Brown-Forsythe version (robust to skew)
    return table


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------
def bootstrap_ci(a, b=None, statistic=np.mean, n_boot: int = 10_000, level: float = 0.95, seed: int = 42):
    """Percentile bootstrap CI for statistic(a), or for statistic(a) - statistic(b).

    The bootstrap resamples the observed data with replacement many times, so it
    needs no normality assumption: suitable for skewed sales data.
    """
    rng = np.random.default_rng(seed)
    a = np.asarray(a, dtype=float)
    if b is None:
        boot = np.array([statistic(rng.choice(a, len(a))) for _ in range(n_boot)])
        estimate = statistic(a)
    else:
        b = np.asarray(b, dtype=float)
        boot = np.array([statistic(rng.choice(a, len(a))) - statistic(rng.choice(b, len(b)))
                         for _ in range(n_boot)])
        estimate = statistic(a) - statistic(b)
    lower, upper = np.percentile(boot, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return estimate, lower, upper


def mean_ci(values, level: float = 0.95):
    """Classical t-based confidence interval for a mean."""
    v = np.asarray(values, dtype=float)
    half = stats.t.ppf((1 + level) / 2, len(v) - 1) * stats.sem(v)
    return v.mean(), v.mean() - half, v.mean() + half


# ---------------------------------------------------------------------------
# Two-group tests
# ---------------------------------------------------------------------------
def mann_whitney(a, b, alternative: str = "two-sided") -> dict:
    """Mann-Whitney U with rank-biserial correlation as effect size.

    Rank-biserial r = probability(a > b) - probability(a < b), from -1 to 1;
    |r| around 0.1 is small, 0.3 medium, 0.5 large.
    """
    res = stats.mannwhitneyu(a, b, alternative=alternative)
    r = 2 * res.statistic / (len(a) * len(b)) - 1
    return {"test": "Mann-Whitney U", "statistic": res.statistic, "p_value": res.pvalue,
            "effect_size": r, "effect_measure": "rank-biserial r"}


def welch_t(a, b, alternative: str = "two-sided") -> dict:
    """Welch's t-test (does not assume equal variances)."""
    res = stats.ttest_ind(a, b, equal_var=False, alternative=alternative)
    return {"test": "Welch t-test", "statistic": res.statistic, "p_value": res.pvalue}


# ---------------------------------------------------------------------------
# Multi-group tests
# ---------------------------------------------------------------------------
def kruskal_wallis(groups: dict) -> dict:
    """Kruskal-Wallis H with epsilon-squared effect size.

    epsilon^2 = (H - k + 1) / (n - k): share of rank variation explained by the
    grouping; about 0.01 small, 0.06 medium, 0.14 large.
    """
    values = [np.asarray(v, dtype=float) for v in groups.values()]
    res = stats.kruskal(*values)
    n, k = sum(len(v) for v in values), len(values)
    return {"test": "Kruskal-Wallis H", "statistic": res.statistic, "p_value": res.pvalue,
            "effect_size": (res.statistic - k + 1) / (n - k), "effect_measure": "epsilon-squared"}


def one_way_anova(groups: dict) -> dict:
    res = stats.f_oneway(*[np.asarray(v, dtype=float) for v in groups.values()])
    return {"test": "One-way ANOVA (raw values)", "statistic": res.statistic, "p_value": res.pvalue}


def welch_anova(groups: dict, log: bool = True) -> dict:
    """Welch's ANOVA (unequal variances), optionally on log values to reduce skew."""
    values = [np.log(np.asarray(v, dtype=float)) if log else np.asarray(v, dtype=float)
              for v in groups.values()]
    res = anova_oneway(values, use_var="unequal")
    return {"test": f"Welch ANOVA ({'log' if log else 'raw'} values)",
            "statistic": float(res.statistic), "p_value": float(res.pvalue)}


def pairwise_mann_whitney(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    """All pairwise Mann-Whitney tests with Holm correction for multiple comparisons.

    Running 15 tests at alpha = 0.05 would give about a 54% chance of at least one
    false positive; Holm adjusts p-values to keep that family-wise risk at 5%.
    """
    names = sorted(df[group_col].unique())
    rows = []
    for i, g1 in enumerate(names):
        for g2 in names[i + 1:]:
            a = df.loc[df[group_col] == g1, value_col]
            b = df.loc[df[group_col] == g2, value_col]
            res = mann_whitney(a, b)
            rows.append({"group_1": g1, "group_2": g2, "median_1": a.median(), "median_2": b.median(),
                         "p_value": res["p_value"], "rank_biserial_r": res["effect_size"]})
    out = pd.DataFrame(rows)
    out["p_holm"] = multipletests(out["p_value"], method="holm")[1]
    out["significant"] = out["p_holm"] < ALPHA
    return out.sort_values("p_holm").reset_index(drop=True)


def chi_square(table: pd.DataFrame) -> dict:
    """Chi-square test of independence with Cramer's V and the expected-count check.

    Assumption: expected count >= 5 in (at least 80% of) cells. Cramer's V runs
    from 0 (no association) to 1; about 0.1 small, 0.3 medium, 0.5 large.
    """
    res = stats.chi2_contingency(table)
    n = table.to_numpy().sum()
    v = np.sqrt(res.statistic / (n * (min(table.shape) - 1)))
    expected = res.expected_freq
    return {"test": "Chi-square independence", "statistic": res.statistic, "p_value": res.pvalue,
            "dof": res.dof, "effect_size": v, "effect_measure": "Cramer's V",
            "min_expected": expected.min(), "share_cells_expected_lt5": (expected < 5).mean()}


def holm(p_values) -> np.ndarray:
    return multipletests(p_values, method="holm")[1]
