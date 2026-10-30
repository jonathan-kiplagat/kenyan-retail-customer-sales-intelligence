# Milestone 6: Predictive Modelling

Two models are built here:
1. A **next-month revenue forecast**.
2. An **at-risk (churn) customer model**.

Both are validated with chronological splits and guarded against leakage. The results, including the weak ones, are reported as they are.

## Deliverables

| Deliverable | Location |
|---|---|
| Modelling notebook: build, tune and validate | [notebooks/06_predictive_modeling.ipynb](../notebooks/06_predictive_modeling.ipynb) |
| Evaluation notebook: held-out test, forecast, at-risk list | [notebooks/07_model_evaluation.ipynb](../notebooks/07_model_evaluation.ipynb) |
| Modelling code | [src/modeling/forecasting.py](../src/modeling/forecasting.py), [churn.py](../src/modeling/churn.py), [metrics.py](../src/modeling/metrics.py) |
| Leakage and correctness tests | [tests/test_modeling.py](../tests/test_modeling.py) |
| Frozen model choices | [reports/model_selection.json](../reports/model_selection.json) |
| Metrics for all models | [reports/model_metrics.csv](../reports/model_metrics.csv) |
| Forecast history, Jan 2026 forecast and ranges | [data/processed/forecast_monthly.csv](../data/processed/forecast_monthly.csv), [forecast_jan2026_by_store.csv](../data/processed/forecast_jan2026_by_store.csv) |
| At-risk customer list | [data/processed/customer_risk_scores.csv](../data/processed/customer_risk_scores.csv) |
| Charts | `reports/figures/m6_*.png`, `m7_*.png` |

---

## A. Demand forecasting

**Target:** monthly net revenue for the chain (primary) and for each store (secondary).

**Split:**

| Period | Months | Purpose |
|---|---|---|
| Training | 2024 | Fit the models |
| Validation | Jan–Jun 2025 | Choose the model and tune it |
| Test | Jul–Dec 2025 | Untouched until the final evaluation |

**Walk-forward evaluation:** each month is forecast one month ahead, using only the months before it.

| Model | Type | Validation MAE | **Test MAE** | Test RMSE | Test MAPE |
|---|---|---:|---:|---:|---:|
| **Holt exponential smoothing (damped)** | Statistical, **selected** | 10,564 | **17,500** | 22,817 | 16.5% |
| Random Forest (store panel, depth 3) | Machine learning | 10,781 | 17,678 | 20,870 | 17.8% |
| Naive (last month) | Baseline | 15,763 | 18,448 | 25,861 | 17.5% |
| Moving average (3 months) | Baseline | 13,929 | 20,328 | 26,254 | 20.0% |
| Seasonal naive (last year) | Baseline | 16,194 | 23,610 | 26,819 | 23.8% |

**Feature engineering (Random Forest):**
- Lags 1–3 and rolling means of 3 and 6 months, all shifted so they only look back.
- A store level, recomputed at each forecast origin from earlier months only.
- Month seasonality (sine and cosine), plus December and January flags.
- Public holidays per month.
- Planned promotion days and categories. The promotion plan is known in advance, so this is not leakage.
- A time index for slow growth.

**How it was chosen:** the model with the lowest validation MAE. The Random Forest settings were tuned on validation over 9 combinations.

**Generalization:**
- **Holt ranked first on both validation and test.** On test, though, it beat the naive baseline by only 5%, which is not conclusive on 6 months.
- **Test error was higher than validation error,** mainly because of the **December 2025 peak** (under-forecast by KES 48K). Holt has no seasonal component, so it forecasts an almost flat underlying level of about KES 93K.

**January 2026 forecast:**

| Estimate | Value |
|---|---|
| Holt point forecast | **KES 98,788** |
| 80% range (from the model's own walk-forward errors) | KES 82,007 – 120,796 |
| 95% range (±1.96 × RMSE) | KES 61,993 – 135,582 |
| Seasonal scenario, not validated (Holt × average January ratio of 0.74) | KES 73,442 |
| Actual January 2024 / January 2025 | KES 64,546 / KES 70,471 |

**Recommendation:** plan stock and cash for about **KES 75–85K**. January is reliably the weakest month, and both previous Januaries fell below the model's 80% range.

**Limitations:**
- Only 24 months of data, so seasonality can't be modelled and validated (that needs at least 2 years *before* the first forecast).
- Only 6 test months.
- Electronics make store-months very noisy: store-level MAPE is about 50%.
- The January 2026 promotion and holiday calendar is assumed to repeat January 2025.
- The data is synthetic.

---

## B. At-risk customers (churn)

**Inactivity threshold: 180 days.**
- From 841 observed repeat-purchase gaps: median 47 days, **90th percentile 173 days**.
- Silence beyond 180 days is unlike 9 in 10 genuine returns.
- Caveat: gaps longer than the 2-year window can't be observed, so the threshold is slightly strict.

**Set-up:**

| | Snapshot | Features | Label (`churned = 1`) | Customers | Churn rate |
|---|---|---|---|---|---|
| Train | 31 Dec 2024 | Orders up to the snapshot | No purchase in Jan–Jun 2025 | 210 (2+ orders) | 84.3% |
| Test (out of time) | 30 Jun 2025 | Orders up to the snapshot | No purchase in Jul–Dec 2025 | 308 | 80.5% |
| Score | 31 Dec 2025 | All orders | Unknown, giving the current list | 419 | — |

**Features:**
- Recency, frequency, monetary value.
- Tenure.
- Average order value.
- The customer's own average gap between orders.
- Overdue ratio (recency ÷ own average gap).
- Number of categories bought.
- Promotion share.
- Loyalty membership.

**Model selection: repeated cross-validation on the training snapshot only, plus the one-standard-error rule.**

| Model | CV AUC (5 × 10 folds) | Train AUC | **Test AUC (95% CI)** | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| **Recency rule: silent > 180 days (selected)** | 0.749 | 0.75 | **0.80 (0.73–0.85)** | 0.93 | 0.67 | 0.78 |
| Logistic regression | 0.735 | 0.81 | 0.83 (0.78–0.88) | 0.90 | 0.81 | 0.85 |
| Random Forest classifier | 0.753 | 0.96 | 0.82 (0.76–0.87) | 0.87 | 0.92 | 0.90 |

**Interpretation:**
- **In cross-validation the three approaches were statistically tied.** Only 33 training customers returned. Under the one-standard-error rule, the simplest approach (the recency rule) was selected.
- **On the later test period, logistic regression ranked customers better** (AUC +0.037, 95% CI +0.002 to +0.073).
  - The rule remains the operational flag, because it was chosen before testing and is highly precise: 93% of flagged customers really did not return.
  - Logistic regression is used as a **priority score**. It should become the primary model if its advantage holds at the next review.
- **The Random Forest overfits:** training AUC 0.96 falls to 0.82 on test.

**What drives churn risk (logistic regression coefficients):**
- **Raises risk:** long recency (the strongest signal), being overdue relative to one's own buying rhythm, and a high average order value. Occasional big-ticket buyers return less often.
- **Lowers risk:** higher total spend, loyalty membership and longer tenure.

**Current at-risk list (31 Dec 2025):**
- **249 of 419 established customers (59%)** have been silent for more than 180 days, with **KES 541,641** of lifetime spend.
- Nairobi CBD has the most value at risk (64 customers, KES 160K).
- The list is ordered by value at risk. Holding back a random 20% as a control group would measure the true effect of a win-back campaign.

**Limitations:**
- Small samples.
- Censored gaps (long gaps are unobserved).
- No data on competitors, complaints or relocation.
- Probabilities are not calibrated, so treat them as a ranking.
- The data is observational, so no causal claims are made.

## Leakage safeguards (tested in `tests/test_modeling.py`)
- **Features use only the past.** Every feature uses data from before the prediction point. Lags are shifted, and store levels are recomputed at each forecast origin.
- **Proven by a test:** multiplying all future revenue by 10 leaves the forecast **unchanged**.
- **Churn features stop at the snapshot,** and labels use only the 6 months after it.
- **Splits are chronological,** and model choices were frozen in `reports/model_selection.json` *before* the test evaluation in notebook 07.
