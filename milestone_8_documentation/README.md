# Milestone 8: Documentation and Presentation

The final documentation set and the defence presentation.

## Deliverables

| Deliverable | Location | Audience |
|---|---|---|
| **Final technical report** | [final_technical_report.md](final_technical_report.md) | Examiners and management: the full story, findings and recommendations |
| Methodology | [methodology.md](methodology.md) | Technical reviewers: how and why each method was used |
| SQL documentation | [sql_documentation.md](sql_documentation.md) | Database users: schema, constraints, load process, query catalogue |
| Model evaluation report | [model_evaluation_report.md](model_evaluation_report.md) | Technical reviewers: metrics, errors, leakage checks, monitoring |
| Dashboard documentation | [milestone_7_dashboard/README.md](../milestone_7_dashboard/README.md) | Dashboard users: pages, KPI definitions, verification |
| **Defence presentation (17 slides, speaker notes)** | [presentations/Duka_Bora_Capstone_Defence.pptx](../presentations/Duka_Bora_Capstone_Defence.pptx) | The defence panel |
| Likely questions and answers | [defence_qa.md](defence_qa.md) | Defence preparation |
| Deck source (rebuilds the PPTX) | [presentations/build_deck.py](../presentations/build_deck.py) | Reproducibility |

## Presentation outline (about 15 minutes)

| # | Slide | Message |
|---|---|---|
| 1 | Title | Customer and Sales Intelligence for a Kenyan Retailer |
| 2 | The problem | Duka Bora records every sale but decides on intuition |
| 3 | Answers at a glance | KES 2.18M revenue; price-led growth; 249 at risk; plan January at KES 75–85K |
| 4 | Approach | Eight milestones, one reproducible pipeline |
| 5 | Data quality | Cleaning found all 126 injected issues |
| 6 | Sales trend | Revenue grew 8.8%, but units fell 4.7% |
| 7 | Products | Clothing earns 46% of profit on 27% of revenue |
| 8 | Customers | A few customers carry the revenue, and many are drifting |
| 9 | Stores | Thika is the most efficient store but is shrinking |
| 10 | SQL | A normalized PostgreSQL database reconciles to the cent |
| 11 | Statistics | Significant is not the same as important |
| 12 | Forecast | The forecast is honest about its uncertainty |
| 13 | Churn | A simple rule finds non-returners with 93% precision |
| 14 | Dashboard | A five-page Power BI dashboard for managers |
| 15 | Recommendations | Six recommendations, each with a measure of success |
| 16 | Limitations | Limitations and next steps |
| 17 | Close | Questions |

The charts are native PowerPoint charts, so their numbers can be inspected and edited in PowerPoint. Speaker notes
on every slide carry the narration.

## Final reproducibility check (30 October 2026)

| Check | Result |
|---|---|
| All 7 notebooks re-executed in order with `jupyter nbconvert --execute` | Completed without errors (about 11 minutes) |
| Automated tests (`python -m pytest -q`) | **28 passed** |
| Raw, cleaned and analytical data after the re-run | **Byte-identical** to the committed files (seed 2024) |
| Forecast outputs after the re-run | Identical to 15 significant digits (floating-point summation order only) |
| Power BI export (`python -m src.visualization.powerbi_export`) | Same row counts for all 9 tables |
| PPTX file check (schema, relationships, charts) | Passed |

To repeat the check from the project root:

```powershell
foreach ($nb in Get-ChildItem notebooks\0*.ipynb) {
    jupyter nbconvert --to notebook --execute --inplace $nb.FullName
}
python -m pytest -q
python presentations/build_deck.py
```
