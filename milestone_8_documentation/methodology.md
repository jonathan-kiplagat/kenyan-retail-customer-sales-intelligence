# Methodology

This document explains **how** the project was carried out and **why** each method was chosen. The findings are in
the [final technical report](final_technical_report.md).

The work follows the CRISP-DM cycle: business understanding → data understanding → data preparation → analysis and
modelling → evaluation → deployment (the dashboard). Each stage maps to one milestone.

```
Problem framing ─► Data generation ─► Cleaning and features ─► EDA ─► SQL ─► Statistics ─► Models ─► Dashboard ─► Report
     M1               M1                   M2                 M3     M4        M5          M6         M7          M8
```

---

## 1. Business understanding (Milestone 1)

**Client.** Duka Bora is a fictional chain of six Kenyan supermarkets in Nairobi CBD, Westlands, Thika, Mombasa,
Kisumu and Nakuru.

**Questions management asked:**
1. Who buys what, where and when?
2. Which products and stores drive revenue and profit?
3. Which customers are drifting away?
4. What demand should be expected next month?

**Success indicators set before the analysis:**
- Every analytical question is answered with evidence.
- Every cleaning decision is logged and audited.
- Statistical claims carry effect sizes and confidence intervals.
- Models beat a naive baseline on data they never saw.
- A manager can answer the four questions from the dashboard without help.

## 2. Data acquisition: synthetic data by design (Milestone 1)

### Why synthetic data
- **No privacy risk.** Real customer-level retail data cannot be published in a public repository.
- **Every pattern has a known cause.** Because the generating rules are documented, the analysis can be checked:
  if RFM finds a loyal segment, we know whether that segment really exists.

### How the data was generated ([src/data_generation/](../src/data_generation/))
All random draws come from one NumPy generator with seed 2024, so every run produces identical files.

1. **Calendar.** 731 days (2024–2025), joined to the **real, verified Kenyan public-holiday calendar** (28 dates,
   including special gazetted holidays and Sunday substitutes), with payday-window flags around month end.
2. **Daily shopping intensity.** A product of factors:
   - Month seasonality (December ×1.35, January ×0.85).
   - Day of week (Saturday ×1.30, Monday ×0.85).
   - Payday window.
   - Public holidays and holiday eves.
   - Promotion campaigns.
   - Slow growth.
3. **Customers.** 1,800 customers, each with a **hidden behaviour segment**: one-off 78%, occasional 13%, regular
   6.5%, loyal 2.5%. The segment is never exported, so later analyses must rediscover it from behaviour.
   - Some customers are **drifters** who stop buying part-way through the period. This gives the churn model a real
     signal to find.
   - Repeat customers can start up to 180 days before 2024, so the data does not begin with an artificial wave of
     "new" customers.
4. **Orders and lines.** 2,650 orders placed on dates according to the daily intensity, mostly at each customer's
   preferred store, and filled with exactly 2,988 product lines.
   - Category choice is tilted by season (for example, clothing in January, May and September for school terms;
     electronics in November and December) and by store.
5. **Prices and promotions.**
   - 40 products with realistic Kenyan shelf prices and costs.
   - A 4% price review on 2025-01-01.
   - 20 category campaigns with fixed discounts.
   - Payment methods weighted towards M-Pesa.
6. **Data-quality issues.** A separate seeded step (seed 2025) injected **126 realistic issues** into 115 sales rows,
   plus 11 dimension-table label issues, and logged every change to
   [docs/dq_injection_log.csv](../docs/dq_injection_log.csv). Adding 12 duplicate rows brings the raw sales file to
   exactly **3,000 rows**.
   - Types: duplicates, mixed date formats, totals stored as text, payment label variants, missing values,
     quantity-entry errors, wrong prices and discount bugs.

**Validation.** Eight automated tests ([tests/test_raw_data.py](../tests/test_raw_data.py)) check the row count,
keys, period, foreign keys and reproducibility.

## 3. Data preparation (Milestone 2)

### Principles
1. **The raw files are never modified.** Cleaning reads `data/raw/` and writes `data/cleaned/`.
2. **No silent deletion or imputation.** Every change is counted in the
   [before-and-after report](../reports/data_quality_before_after.csv).
3. **Use evidence before assumptions.** A missing value is filled only when other data proves it. For example, a
   missing payment method is copied from another line of the same receipt, because payment is captured once per
   receipt. When there is no evidence, the value is labelled ("Unknown", walk-in) rather than guessed.
4. **Recalculate money from its base fields.** After cleaning, revenue, discount, cost and profit are recomputed from
   quantity, unit price, unit cost and discount, so every line reconciles exactly.
5. **Separate genuine outliers from errors.** Quantity 999 contradicts the receipt total, so it is an error and is
   corrected. A purchase of 60 bottles of water matches its total, so it is a genuine sale and is kept. High-value
   electronics lines (IQR outliers) are kept as well.

### Audit
After cleaning, the output was compared with the injection log and with the generator's true data, cell by cell. All
126 issues were detected. The only cells that still differ from the truth are the 21 customer IDs and 7 payment
methods for which no evidence existed.

### Feature engineering ([src/preprocessing/features.py](../src/preprocessing/features.py))
The analytical dataset `sales_analytical.csv` has 2,988 rows × 51 columns. It adds:
- **Calendar features:** weekend, payday window, public holiday, holiday eve.
- **Time of day.**
- **Basket features:** order value, lines and units per order.
- **Promotion and walk-in flags.**
- **Profit margin.**
- **Customer cohort month.**

## 4. Exploratory data analysis (Milestone 3)

- **Descriptive statistics first, charts second.** Each of the 18 charts has a written interpretation and a business
  implication.
- **The unit of analysis is chosen explicitly:**
  - Average order value is calculated per receipt, not per line.
  - Calendar effects are measured per calendar day, with zero-order days included.
  - Customer metrics exclude walk-ins.
- **Skew is handled visually:** log scales for customer spend, medians alongside means.
- **Confounders are shown, not ignored.** Store growth is presented with and without electronics, because a single TV
  is about 17% of Thika's annual revenue.
- **Promotion lift uses a two-sided baseline:** the same category within 28 days before and after, excluding other
  campaigns. It is described as an association.

## 5. SQL analytics (Milestone 4)

- **A 3NF PostgreSQL schema** with keys, generated money columns and CHECK constraints enforcing the cleaning rules.
- **Loaded through typed staging tables in one transaction.**
- **The data-quality queries prove the load is correct.** Revenue reconciles with Python to the cent.
- **Business queries use a range of techniques:** joins, CTEs, window functions (`RANK`, `LAG`, rolling averages,
  `NTILE`), cohort pivots and RFM segmentation.

Full reference: [sql_documentation.md](sql_documentation.md).

## 6. Statistical analysis (Milestone 5)

Every hypothesis follows the same seven steps:

1. State H₀ and H₁.
2. Choose the unit of analysis.
3. Check the assumptions:
   - normality with Shapiro-Wilk and Q-Q plots;
   - equal variances with Levene's test;
   - expected counts for chi-square tests;
   - independence.
4. Choose a test that suits those assumptions:
   - **Non-parametric tests** (Mann-Whitney U, Kruskal-Wallis) for skewed or discrete data.
   - **Welch tests** as a robustness check.
   - **Chi-square tests** for associations between categories.
5. Use α = 0.05, with **Holm correction** for families of tests.
6. Report the test statistic, p-value, **effect size** (rank-biserial r, ε², Cramér's V) and a **95% confidence
   interval** (bootstrap, 10,000 resamples by default, where no closed form fits).
7. Interpret the result for the business, with no causal claims from observational data.

**Robustness checks:**
- **Bulk purchases.** The promotion test is repeated without the two genuine bulk purchases.
- **Shared payment method.** Lines in the same receipt share a payment method, so the payment test is repeated on
  single-line orders.
- **Raw ANOVA.** It is reported alongside the robust tests, to show why test choice must follow the assumption
  checks.

## 7. Predictive modelling (Milestone 6)

### Demand forecasting
- **Target:** next month's chain revenue.
- **Chronological split:** train 2024, validation January–June 2025, test July–December 2025.
- **Walk-forward evaluation:** each month is predicted one step ahead using only earlier months.
- **Candidates:**
  - **Baselines:** naive, seasonal naive, 3-month moving average.
  - **Statistical model:** damped Holt exponential smoothing.
  - **Machine learning:** a Random Forest trained on a store × month panel, with leak-free lags, rolling means,
    seasonality, holidays, planned promotions and a store level recomputed at each forecast origin.
- **Selection:** lowest validation MAE. The model choice was frozen in
  [reports/model_selection.json](../reports/model_selection.json) before the test months were scored.
- **Uncertainty:**
  - an 80% range from the 10th–90th percentile of the model's own walk-forward errors;
  - a 95% range of ±1.96 × RMSE;
  - an unvalidated seasonal scenario.

### At-risk customers (churn)
- **The inactivity threshold of 180 days comes from the data:** the 90th percentile of 841 repeat-purchase gaps is
  173 days.
- **Population:** established customers only (2+ orders). One-off buyers have no buying rhythm to break.
- **Snapshots:**
  - Train: features at 31 Dec 2024, label = no purchase in January–June 2025.
  - Out-of-time test: features at 30 Jun 2025, label = no purchase in July–December 2025.
  - Score: 31 Dec 2025.
- **Candidates:** a recency rule (silent for more than 180 days), logistic regression (scaled features, balanced
  class weights) and a Random Forest classifier.
- **Selection:** repeated stratified cross-validation (5 folds × 10 repeats) on the training snapshot, with the
  **one-standard-error rule**: choose the simplest model whose CV AUC is within one standard error of the best.
- **Test metrics:** AUC with a bootstrap 95% CI, precision, recall and F1, and a paired bootstrap of the AUC
  difference between the logistic regression and the rule.

### Leakage controls
- Every feature uses data from before the prediction point only.
- Lags are shifted, and store levels are recomputed at each forecast origin.
- **A unit test proves it:** multiplying all future revenue by 10 leaves the forecast unchanged.
- Churn features stop at the snapshot date. Labels use only the six months after it.

Full results: [model_evaluation_report.md](model_evaluation_report.md).

## 8. Dashboard (Milestone 7)

- **A star schema** exported by [src/visualization/powerbi_export.py](../src/visualization/powerbi_export.py): one
  fact table, four dimensions and four pre-calculated summary tables.
- **DAX measures** with written KPI definitions.
- **Five pages,** one for each management question area.
- **Synced slicers** and cross-filtering.
- **Headline figures checked** against the Python and SQL results.

Details: [milestone_7_dashboard/README.md](../milestone_7_dashboard/README.md).

## 9. Reproducibility and engineering

| Practice | Implementation |
|---|---|
| One source of paths and settings | [src/config.py](../src/config.py): all paths relative to the project root; seed 2024 |
| Reusable code, thin notebooks | Logic in `src/`; notebooks import it and add the narrative |
| Automated tests | 28 pytest tests: raw data, cleaning, statistics functions, modelling (including leakage) |
| Executed notebooks | All 7 notebooks are committed with outputs, and they re-run end to end |
| Environment | Python virtual environment and [requirements.txt](../requirements.txt) (Windows / VS Code) |
| Secrets | The PostgreSQL password lives in a git-ignored `.env` file |
| Version control | One commit per milestone on GitHub |

## 10. Ethics and limitations of the method
- **Synthetic data.** The figures illustrate the methods. They are not real market facts about Kenyan retail.
- **No personal identifiers.** Customers are IDs, gender, age band and county only.
- **Observational analysis.** Promotion and loyalty effects are associations. Measuring them causally would need
  controlled trials, which the report recommends.
- **Short history.** Two years is not enough to validate a seasonal forecasting model.
