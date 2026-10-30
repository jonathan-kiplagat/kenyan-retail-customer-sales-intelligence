# Model Evaluation Report

Evaluation of the two Milestone 6 models on data they never saw during development. Code and outputs:
[notebooks/06_predictive_modeling.ipynb](../notebooks/06_predictive_modeling.ipynb) (development),
[notebooks/07_model_evaluation.ipynb](../notebooks/07_model_evaluation.ipynb) (final test),
[reports/model_metrics.csv](../reports/model_metrics.csv) (every metric).

**Evaluation rule:** each model was chosen using training and validation data only. The choice was then frozen in
[reports/model_selection.json](../reports/model_selection.json). The test period was scored once, afterwards, and
the results are reported as they came out, including where the selected model was not the best.

---

## Part A: Next-month revenue forecast

### Metrics
- **MAE (mean absolute error, KES):** the average size of a monthly miss. It is the primary metric because a manager
  can read it directly as "typically off by KES X".
- **RMSE:** penalizes large misses more heavily.
- **MAPE:** error as a percentage of actual revenue.

### Results (walk-forward, one month ahead)

| Model | Validation MAE (Jan–Jun 2025) | Test MAE (Jul–Dec 2025) | Test RMSE | Test MAPE |
|---|---:|---:|---:|---:|
| **Holt exponential smoothing, damped (selected)** | **10,564** | **17,500** | 22,817 | **16.5%** |
| Random Forest (store panel) | 10,781 | 17,678 | **20,870** | 17.8% |
| Naive (last month) | 15,763 | 18,448 | 25,861 | 17.5% |
| Moving average (3 months) | 13,929 | 20,328 | 26,254 | 20.0% |
| Seasonal naive (same month last year) | 16,194 | 23,610 | 26,819 | 23.8% |

### Month-by-month errors of the selected model

| Month | Split | Actual | Holt forecast | Error (actual − forecast) |
|---|---|---:|---:|---:|
| Jan 2025 | validation | 70,471 | 91,428 | −20,957 |
| Feb 2025 | validation | 86,167 | 87,242 | −1,075 |
| Mar 2025 | validation | 84,030 | 87,076 | −3,047 |
| Apr 2025 | validation | 91,047 | 86,406 | +4,641 |
| May 2025 | validation | 98,379 | 87,358 | +11,021 |
| Jun 2025 | validation | 111,928 | 89,285 | +22,643 |
| Jul 2025 | test | 109,353 | 93,062 | +16,291 |
| Aug 2025 | test | 78,915 | 95,899 | −16,984 |
| Sep 2025 | test | 78,927 | 93,876 | −14,949 |
| Oct 2025 | test | 96,734 | 92,172 | +4,562 |
| Nov 2025 | test | 88,843 | 93,013 | −4,171 |
| Dec 2025 | test | 140,808 | 92,765 | **+48,043** |

### Interpretation
- **Holt ranked first on both validation and test,** so the selection generalized. On test, though, it beat the naive
  baseline by only about 5% (17,500 vs 18,448). With six test months, that margin is **not conclusive**.
- **December drives most of the test error.** Holt has no seasonal component and forecasts a flat underlying level
  of about KES 93K. December 2025 (KES 141K) was under-forecast by KES 48K. Without December, the test MAE is about
  KES 11,400.
- **The Random Forest has the lowest RMSE,** meaning fewer very large misses, because its December flag partly
  anticipates the peak. Its MAE was slightly worse, and it is far less transparent. The simpler model was kept.
- **The seasonal naive model was the worst.** One prior year is too noisy to copy as a seasonal pattern, mainly
  because single electronics sales swing individual months.

### January 2026 forecast

| Estimate | KES |
|---|---:|
| Holt point forecast | **98,788** |
| 80% range (10th–90th percentile of 12 walk-forward errors) | 82,007 – 120,796 |
| 95% range (±1.96 × RMSE) | 61,993 – 135,582 |
| Seasonal scenario, not validated (Holt × average January ratio of 0.74) | 73,442 |
| Actual January 2024 / January 2025 | 64,546 / 70,471 |

**Recommendation:** plan for **KES 75–85K**. Both previous Januaries fell **below** the model's 80% range, and the
model's largest validation miss was January 2025 (over-forecast by KES 21K). The point forecast is the underlying
level, not a January-specific number.

### Store-level forecasts
Store-month revenue is very noisy. Store-level MAPE was about 50% for every model: the Random Forest had the lower
MAE (KES 6,444 vs 7,485 for naive) but a slightly higher MAPE (50.9% vs 48.6%). Store figures are therefore shown only as a rough allocation of the chain forecast, rescaled to add up
to it.

---

## Part B: At-risk customers (churn)

### Definition
A customer with 2 or more orders who makes **no purchase in the next 6 months** after a snapshot date. The 180-day
threshold is the point beyond which silence is unusual: 90% of 841 observed repeat-purchase gaps are 173 days or
shorter.

### Metrics
- **AUC:** ranking quality (the probability that a random churner is scored above a random returner).
- **Precision:** the share of flagged customers who really did not return. This is what wastes or saves campaign
  money.
- **Recall:** the share of real churners who were flagged.
- **F1.**

Accuracy is not used. With about 80% churn, a model that flags everyone would be "80% accurate" and useless.

### Results

| Model | CV AUC (train, 5×10 folds) | Train AUC | **Test AUC (95% CI)** | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| **Recency rule: silent > 180 days (selected)** | 0.749 | 0.75 | **0.80 (0.73–0.85)** | **0.93** | 0.67 | 0.78 |
| Logistic regression | 0.735 | 0.81 | **0.83** (0.78–0.88) | 0.90 | 0.81 | 0.85 |
| Random Forest classifier | 0.753 | **0.96** | 0.82 (0.76–0.87) | 0.87 | 0.92 | 0.90 |

Test population: 308 established customers at 30 Jun 2025, of whom 80.5% (248) did not return by December.

**Confusion matrices on the test set**, derived from the reported precision and recall:

| Model | Flagged and churned | Flagged but returned | Missed churners | Correctly not flagged |
|---|---:|---:|---:|---:|
| Recency rule | 165 | 12 | 83 | 48 |
| Logistic regression | 200 | 22 | 48 | 38 |
| Random Forest | 228 | 33 | 20 | 27 |

### Interpretation
- **Selection.** In cross-validation the three approaches were statistically tied: only 33 training customers
  returned. The one-standard-error rule therefore picked the simplest one, the recency rule.
- **Test.** Logistic regression ranked customers better. The paired bootstrap AUC difference was +0.037 (95% CI
  +0.002 to +0.073), small but just excluding zero.
- **Decision:**
  - The **rule stays the operational flag.** It was chosen before testing, a manager can explain it in one sentence,
    and 93% of the customers it flags really did not return.
  - Logistic regression is used as a **priority score** within the flagged list.
  - It should become the primary model if its advantage holds at the next review.
- **The Random Forest overfits.** Its AUC falls from 0.96 on train to 0.82 on test. Its high recall comes with the
  most wasted contacts (33 customers flagged who in fact returned).

### Drivers (logistic regression coefficients)
- **Raises risk:** days since last purchase (the strongest signal), being overdue relative to one's own buying rhythm,
  and a high average order value. Big-ticket occasional buyers return less often.
- **Lowers risk:** higher total spend, loyalty membership and longer tenure.

These are associations within the model. They do not show that, for example, loyalty membership *causes* retention.

### Current list (31 Dec 2025)
**249 of 419 established customers (59%)** are flagged, with KES 541,641 of lifetime spend. Nairobi CBD has the most
value at risk (64 customers, KES 160K). The list is in
[data/processed/customer_risk_scores.csv](../data/processed/customer_risk_scores.csv) and on dashboard page 3.

---

## Leakage and validity checks

| Risk | Control | Evidence |
|---|---|---|
| Future data in forecast features | Lags shifted; rolling windows end before the forecast month; store level recomputed at each origin | Unit test: multiplying all future revenue ×10 leaves the forecast unchanged |
| Tuning on the test period | Model and hyper-parameters frozen in `model_selection.json` before notebook 07 | File committed with Milestone 6 |
| Churn label in the features | Features use orders up to the snapshot only; label uses the 6 months after it | `tests/test_modeling.py` |
| Random splits on time data | Chronological and out-of-time splits only | Notebook 06 set-up |
| Class imbalance | AUC, precision and recall; balanced class weights | Metrics table above |

## Limitations
- **Few test points:** 6 forecast months and 308 churn customers. Differences of a few thousand shillings, or a few
  hundredths of AUC, are not conclusive.
- **No seasonal model.** Two years of data cannot validate one: a seasonal model needs at least two full years
  **before** the first forecast.
- **Censored gaps.** Purchase gaps longer than the data window cannot be observed, so the 180-day threshold is
  slightly strict.
- **Uncalibrated probabilities.** Churn probabilities are rankings, not calibrated probabilities.
- **Synthetic data.** Real data would contain noise sources (competitors, stock-outs, relocations) that are not
  modelled here.

## Monitoring plan
1. **Retrain monthly.** Re-fit the forecast as each month closes, and track the rolling MAE against the naive baseline.
2. **Re-score the at-risk list quarterly.** Measure what share of flagged customers return with and without
   contact, holding back a random 20% as a control group.
3. **Revisit the model choice after six more months.** Promote logistic regression if its AUC advantage persists.
   Add a seasonal model once there are three full years of history.
