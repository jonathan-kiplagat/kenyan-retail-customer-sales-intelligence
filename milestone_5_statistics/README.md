# Milestone 5: Statistical Analysis

This milestone uses hypothesis tests to check whether the patterns seen in the EDA are **statistically significant**, using Python (SciPy, statsmodels).

**Every test follows the same procedure:**
1. State the hypotheses (H₀, H₁).
2. Choose the unit of analysis.
3. Check the assumptions.
4. Choose a test that suits those assumptions.
5. Use α = 0.05.
6. Report the statistic, p-value, effect size and 95% confidence interval.
7. Interpret the result and state the business implication.

## Deliverables

| Deliverable | Location |
|---|---|
| Statistical analysis notebook (executed) | [notebooks/05_statistical_analysis.ipynb](../notebooks/05_statistical_analysis.ipynb) |
| Reusable test functions | [src/analysis/stats_tests.py](../src/analysis/stats_tests.py) |
| Unit tests for those functions | [tests/test_stats_tests.py](../tests/test_stats_tests.py) |
| Results table | [reports/hypothesis_test_results.csv](../reports/hypothesis_test_results.csv) |
| Charts | `reports/figures/m5_*.png` |

## Results

| # | Hypothesis (H₁) | Assumption checks | Test | Result | Effect size / 95% CI | Decision |
|---|---|---|---|---|---|---|
| Q1 | Promotion lines have **more units per line** | Discrete, skewed (skew 15–20), unequal variances | Mann-Whitney U, one-sided; Welch t as robustness check | p = 6.7×10⁻¹¹ (Welch p = 0.006) | r = 0.19 (small); **+0.49 units per line (0.21 to 0.93)** | **Reject H₀** |
| Q1 | Same, **within each category** | As above | Mann-Whitney per category + Holm correction | All 6 categories: adjusted p ≤ 0.007 | +0.23 (groceries) to +1.14 (personal care) units | **Reject H₀ in 6 of 6** |
| Q1 | Category **units per day** are higher on campaign days | Skewed daily counts, zero days included | Mann-Whitney per category + Holm correction | 5 of 6 significant; personal care p = 0.25 | Beverages +3.3 units/day (1.6 to 6.0) | **Reject H₀ in 5 of 6** |
| Q2 | **Order value** differs across stores | Skew 2.5–9.5, Shapiro p < 0.001; Levene p = 0.19 | Kruskal-Wallis (primary); Welch ANOVA on log values | Kruskal p = 0.017; Welch log p = 0.008; *raw ANOVA p = 0.076* | ε² = 0.003 (very small) | **Reject H₀** |
| Q2 | Post-hoc pairwise comparisons | — | Mann-Whitney + Holm correction (15 pairs) | Only **Mombasa vs Westlands** significant (adjusted p = 0.013) | Median KES 411 vs 480 | — |
| Q2 | Customer **total spend** differs by home store (robustness check) | Skewed | Kruskal-Wallis | p = 0.79 | ε² ≈ 0 | Fail to reject |
| Q3 | **Units per line** differ across categories | Skewed counts | Kruskal-Wallis | Holm p ≈ 10⁻⁵² | ε² = 0.083 (small to medium) | **Reject H₀** |
| Q3 | **Payment method** differs across categories | All expected counts ≥ 5.4; single-line-order robustness check | Chi-square test of independence | Holm p = 0.043 (single-line orders p = 0.009) | Cramér's V = 0.056 (weak) | **Reject H₀** |
| Q3 | **Time of day** differs across categories | All expected counts ≥ 17 | Chi-square test of independence | p = 0.33 | V = 0.043 | Fail to reject |

## Interpretation and business implications

1. **Promotions are associated with larger purchases.** Customers buy about half an extra unit per line on promotion, and this holds in every category. The result survives removing the two genuine bulk purchases (+0.32 units, CI 0.21 to 0.45).
   - The effect is small. It does not pay for discounts that exceed category margins, as Milestone 3 showed for groceries and electronics.
   - **This is not proof of causation.** Promotions were not randomly assigned, and campaigns coincide with seasonal peaks.
   - **Recommendation:** run a controlled store-level trial to measure the true effect.
2. **Store spending differences are statistically real but tiny.**
   - The store explains about 0.3% of the variation in order value. The difference comes from Mombasa's smaller baskets.
   - Customers spend similar amounts over two years wherever they shop.
   - **Recommendation:** focus basket-building at Mombasa; there is no need for store-specific customer strategies.
3. **Categories differ in how much customers buy and how they pay, but not in when they shop.**
   - Multi-buy offers suit beverages and groceries.
   - Electronics customers need card and bank payment options.
   - One staffing plan works for every category.

## Analytical decisions to be able to defend
- **Why non-parametric tests?**
  - Units and order values are discrete or heavily right-skewed, and Shapiro-Wilk rejects normality for every group.
  - Mann-Whitney and Kruskal-Wallis compare ranks, so a few huge electronics baskets cannot dominate the result.
  - Welch tests on log values are reported as support.
- **Why does the raw ANOVA disagree?** The large baskets inflate the within-group variance, which hides the difference between stores. It is shown deliberately, to demonstrate that **test choice must follow from the assumption checks**.
- **Why compare within each category for Q1?** Promotions are concentrated in categories that are naturally bought in multiples, so a pooled comparison partly measures category mix.
- **Why use effect sizes and bootstrap confidence intervals?**
  - With thousands of rows, trivial differences become "significant", so effect sizes show whether a difference matters.
  - Bootstrap intervals need no normality assumption.
- **Why Holm correction?** Running many tests at α = 0.05 inflates the chance of a false positive. For example, 15 store pairs give about a 54% chance of at least one false positive.
- **How was independence handled?** Lines in the same multi-item order share a payment method, so the payment test was repeated on single-line orders. It gave the same conclusion.
- **No causal claims** are made anywhere: the data is observational.
