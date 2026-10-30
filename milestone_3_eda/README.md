# Milestone 3: Exploratory Data Analysis

Exploratory analysis of the cleaned Duka Bora data (2,988 sales lines, 2,650 orders, 2024–2025) using pandas, NumPy, Matplotlib and Seaborn. Every chart in the notebook has a written interpretation and a business implication.

## Deliverables

| Deliverable | Location |
|---|---|
| EDA notebook (executed, 18 charts) | [notebooks/04_exploratory_data_analysis.ipynb](../notebooks/04_exploratory_data_analysis.ipynb) |
| Reusable summary functions | [src/analysis/eda.py](../src/analysis/eda.py) |
| Chart style (consistent colours per category and store) | [src/visualization/style.py](../src/visualization/style.py) |
| Charts (PNG) | `reports/figures/m3_*.png` |

**Chart types used:** line, bar (grouped and horizontal), histogram, boxplot, heatmap and scatter.

## Headline KPIs (2024–2025)

| KPI | Value |
|---|---:|
| Net revenue | KES 2,179,215 |
| Gross profit | KES 538,802 (24.7% margin) |
| Orders / units | 2,650 / 4,779 |
| Identified customers | 1,788 |
| Average order value / median order value | KES 822 / KES 450 |
| Discounts given | KES 43,142 (2% of revenue) |

## Key findings

| # | Finding | Evidence | Recommendation |
|---|---|---|---|
| 1 | Growth came from price and basket size, not volume | Revenue +8.8%, profit +10.7%, but units −4.7% in 2025 | Track units and orders alongside revenue |
| 2 | Strong seasonality | December is the best month in both years, January the weakest; holiday eves average 5.2 orders/day vs 3.2 on ordinary weekdays | Stock and staff up from November; react quickly to gazetted holidays |
| 3 | Clear daily rhythm | Peaks 17:00–19:59 and at lunchtime; Saturday and Friday busiest, Monday slowest | Staff to peaks; deliveries on Monday and Tuesday mornings |
| 4 | Clothing is the profit engine | 27% of revenue, **46% of profit**, 42% margin; the top 5 profit products are all clothing | Protect the clothing range, especially school uniforms |
| 5 | Groceries build traffic, not profit | 25% of revenue, 12% of profit; staples lead on units | Competitive pricing; avoid deep discounts |
| 6 | Revenue is concentrated | Top 20% of customers produce 61% of revenue; repeat buyers (23%) produce 48% | Retention and second-visit offers |
| 7 | Valuable customers are drifting | 55 of 158 customers with 3+ orders (35%) inactive for over 180 days (KES 230K past spend) | Win-back campaign (formal model in Milestone 6) |
| 8 | Mombasa: high footfall, small baskets | Lowest order value (KES 677) and lowest revenue per m² | Bundles and add-on displays; layout review |
| 9 | Thika: efficient but shrinking | Highest revenue per m² (KES 285) but −19% excluding electronics | Investigate competition; local retention |
| 10 | Some promotions give away the margin | Grocery campaigns (10% off a 12.6% margin) and Black Friday electronics (20% off a 19% margin) earn 1–3%; 16 promotion lines sold at a loss | Cap discounts well below category margin; move or drop the January clothing campaign (no lift) |

## Analytical decisions to be able to defend
- **Average order value is calculated per order (receipt), not per line.** Calculating it per line would split multi-item baskets into artificially small "orders".
- **Calendar effects use orders per calendar day, including zero-order days.** This avoids the bias of comparing 28 holiday days with 700 ordinary days on raw counts.
- **Store growth is shown with and without electronics.** A single TV (KES 22K) is about 17% of Thika's annual revenue. Kisumu's +38% shrinks to +3.5% without electronics, and Nakuru's −9% becomes +11%.
- **Log scales are used for customer spend.** The distribution is strongly right-skewed (mean KES 1,211 vs median KES 564).
- **Promotion lift is compared with a two-sided baseline** of the same category within 28 days before and after, excluding other promotion days. It is described as an association, not causation, because campaigns coincide with seasonal peaks.
- **Customer analysis excludes the 21 walk-in lines** that have no customer ID.
