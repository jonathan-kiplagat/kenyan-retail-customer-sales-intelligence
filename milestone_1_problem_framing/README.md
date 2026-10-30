# Milestone 1: Problem Framing and Data Acquisition

## Business problem
Duka Bora, a fictional six-store Kenyan supermarket chain, records every sale but makes stock, promotion and retention decisions on intuition. Management wants to know four things:
1. Who buys what, where and when.
2. Which products and stores drive revenue and profit.
3. Which customers are drifting away.
4. What demand to expect next month.

This project builds the evidence base to answer those questions.

## Deliverables

| Deliverable | Location |
|---|---|
| Problem statement, objectives, analytical questions, success indicators | [notebooks/01_problem_framing.ipynb](../notebooks/01_problem_framing.ipynb) (sections 1–5) |
| Data generation method and validation | [notebooks/02_data_generation.ipynb](../notebooks/02_data_generation.ipynb) |
| Generator code (seeded, reproducible) | [src/data_generation/](../src/data_generation/) |
| Raw CSV datasets (exactly 3,000 sales rows) | [data/raw/](../data/raw/) |
| Public context data: Kenyan public holidays, verified | [data/external/kenya_public_holidays_2024_2025.csv](../data/external/kenya_public_holidays_2024_2025.csv) |
| Data dictionary | [docs/data_dictionary.md](../docs/data_dictionary.md) |
| Data sources and provenance | [docs/data_sources.md](../docs/data_sources.md) |
| Injected data-quality issue log (for the Milestone 2 audit) | [docs/dq_injection_log.csv](../docs/dq_injection_log.csv) |
| Automated checks | [tests/test_raw_data.py](../tests/test_raw_data.py) (8 tests, all passing) |
| Figures | `reports/figures/m1_*.png` |

## Evidence of validation

| Check | Result |
|---|---|
| Rows in `data/raw/sales_transactions.csv` | **3,000** (2,988 genuine lines + 12 injected duplicates) |
| Customers / products / stores / categories / promotions | 1,800 / 40 / 6 / 6 / 20 |
| Period | 2024-01-01 to 2025-12-31 (731 calendar days) |
| Foreign keys that resolve (non-blank values) | 100% for store, product, customer and promotion |
| Reproducibility | Identical data fingerprint on repeated runs (seed 2024) |
| Logged data-quality issues | 126 changes touching 115 sales rows, plus 11 dimension-table label issues |

## Headline facts about the generated data (clean version)
- 2,650 orders, KES 2.18M net revenue, 24.7% gross margin.
- Average order value is KES 822, but the median is KES 450. Order values are right-skewed.
- Every December is a peak and every January a dip. Revenue grew 8.8% year on year, of which line volume was +3.7%; the rest is the 4% price review plus product mix.
- M-Pesa is used for 56% of orders. 77% of customers bought only once, and the top 10% of customers generate 43% of revenue.

## Key decisions to be able to defend
- **Why synthetic data?** It lets the whole project, including customer-level data, be published without privacy risk. The business rules are documented, so every pattern can be traced back to its cause.
- **Why are the segments hidden?** If a `segment` column were exported, RFM would simply re-read the answer. Hiding it makes the RFM analysis a real test.
- **Why exactly 3,000 raw rows including duplicates?** The assignment fixes the raw file at 3,000 rows. Duplicates are part of the raw reality that cleaning must remove.
- **Why only public holidays as external data?** KNBS CPI and census data were removed from scope at the project owner's request. The holiday dates are real, verified and cited per row.
