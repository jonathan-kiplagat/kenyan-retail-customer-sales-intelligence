# Progress Checklist

Legend: ✅ done and verified · 🔄 in progress · ⏳ pending · 🙋 needs the project owner's input

| Phase / Milestone | Status | Evidence |
|---|---|---|
| Phase 1: plan and dataset design | ✅ Approved 2026-10-30 | Plan in project conversation |
| Phase 2: generate data, validate 3,000 rows | ✅ | `data/raw/`, `tests/` (28/28 pass) |
| **M1** Problem framing and data acquisition | ✅ | `milestone_1_problem_framing/README.md`, notebooks 01–02 |
| **M2** Data cleaning and preparation | ✅ | `milestone_2_data_cleaning/README.md`, notebook 03, `data/cleaned/`, audit: all 126 issues detected |
| **M3** Exploratory data analysis | ✅ | `milestone_3_eda/README.md`, notebook 04 (18 charts), `src/analysis/eda.py` |
| **M4** SQL analytics (PostgreSQL + DBeaver) | ✅ | `milestone_4_sql/README.md`, `sql/01-07`, `milestone_4_sql/outputs/`, 6 DBeaver screenshots |
| **M5** Statistical analysis | ✅ | `milestone_5_statistics/README.md`, notebook 05, `reports/hypothesis_test_results.csv` |
| **M6** Predictive modelling | ✅ | `milestone_6_predictive_modeling/README.md`, notebooks 06–07, forecast + at-risk outputs in `data/processed/` |
| **M7** Power BI dashboard | ⏳ 🙋 | The owner builds the `.pbix` from the provided guide, then takes screenshots |
| **M8** Documentation and presentation | ⏳ | |

## Scope changes
- 2026-10-30: KNBS CPI/inflation and census population data removed at the owner's request. Public holidays remain as the public context data.
