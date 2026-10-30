# Power BI Build Guide: Duka Bora Management Dashboard

Expected time: **2–3 hours**. Save often (**Ctrl+S**) as `milestone_7_dashboard/Duka_Bora_Dashboard.pbix`.

All data files are in `data/powerbi/`. If the data ever changes, regenerate them from the project root:

```powershell
python -m src.visualization.powerbi_export
```

---

## Step 1: Load the data (10 min)

1. Open Power BI Desktop and choose **Blank report**.
2. Click **Home → Get data → Text/CSV**. Browse to `data/powerbi/`, select `fact_sales.csv`, then click **Load**.
   (Text/CSV opens one file at a time.)
3. Repeat for the other files:
   - `dim_date.csv`
   - `dim_store.csv`
   - `dim_product.csv`
   - `dim_customer.csv`
   - `fact_forecast.csv`
   - `forecast_store_jan2026.csv`
   - `cohort_retention.csv`
   - `model_metrics.csv`
4. **Check the data types.** Click **Home → Transform data**, which opens Power Query, then check each column below.
   To fix a type, click the type icon on the left of the column header.

   | Table | Column | Set type to |
   |---|---|---|
   | fact_sales | `date` | Date |
   | fact_sales | `customer_id`, `promotion_id`, `order_id`, `transaction_id` | Text |
   | dim_date | `date`, `month_start` | Date |
   | dim_customer | `first_purchase`, `last_purchase`, `registration_date` | Date |
   | fact_forecast | `month` | Date |

5. Click **Close & Apply**.

## Step 2: Build the data model (10 min)

1. Open the **Model view** (third icon on the left).
2. Power BI may have created some relationships automatically. **Delete any that are not in this table**: select the line and press Delete.
3. Create the relationships below by dragging a column from the fact table onto the matching column in the dimension
   table. Each one should be **Many-to-one (\*:1)** with a **Single** cross-filter direction.

   | From (many) | To (one) |
   |---|---|
   | `fact_sales[date]` | `dim_date[date]` |
   | `fact_sales[store_id]` | `dim_store[store_id]` |
   | `fact_sales[product_id]` | `dim_product[product_id]` |
   | `fact_sales[customer_id]` | `dim_customer[customer_id]` |

4. Leave `fact_forecast`, `forecast_store_jan2026`, `cohort_retention` and `model_metrics` **unconnected**. They are
   pre-calculated summary tables.
5. **Mark the date table.** Select `dim_date`, then click **Table tools → Mark as date table**, choose `date` and click OK.
   Time-intelligence measures such as year-on-year need this.
6. **Sort month names correctly.**
   - Select `dim_date[month_name]`, click **Column tools → Sort by column**, and choose `month`.
   - Do the same for `month_short` (sort by `month`) and for `day_of_week` (sort by `day_of_week_num`).

**What you should see:** a star shape, with `fact_sales` in the middle and the four dimension tables around it.

## Step 3: Apply the theme and add the measures (20 min)

1. Click **View → Themes → Browse for themes** and select `milestone_7_dashboard/duka_bora_theme.json`.
2. Create a measures table: click **Home → Enter data**, name it `_Measures` and click **Load**.
3. Add every measure from [`dax_measures.md`](dax_measures.md):
   - Select `_Measures`, click **New measure**, paste the formula and press Enter.
   - Format money measures as whole numbers with a thousands separator, and percentage measures as Percentage with 1 decimal place.

## Step 4: Shared slicers (10 min)

Build these on **page 1** first. You will copy them to the other pages in step 9.

| Slicer | Field | Style |
|---|---|---|
| Date | `dim_date[date]` | Between (date range) |
| Store | `dim_store[town]` | Dropdown, multi-select |
| County | `dim_store[county]` | Dropdown |
| Product category | `dim_product[category]` | Dropdown |
| Payment method | `fact_sales[payment_method]` | Dropdown |

Place them in a single row across the top of the page, below the title.

---

## Page 1: Executive Overview

| Visual | Fields | Notes |
|---|---|---|
| Title (text box) | "Duka Bora — Executive Overview (2024–2025)" | |
| 6 KPI cards | Total Revenue, Total Profit, Gross Margin %, Total Orders, Total Customers, Average Order Value | Use the **Card (new)** visual and put all six in one row |
| Line chart: monthly revenue and profit | X-axis `dim_date[month_start]`; Y-axis Total Revenue, Total Profit | Turn off *Concatenate labels*; set the X-axis type to Continuous |
| Line chart: year on year | X-axis `dim_date[month_short]`; Y-axis Total Revenue; Legend `dim_date[year]` | Shows 2024 vs 2025 by month |
| Card | Revenue YoY % | |
| Text box: key insights | See "Management insights" below | |

## Page 2: Product Performance

| Visual | Fields | Notes |
|---|---|---|
| Bar chart: top 10 products by revenue | Y-axis `dim_product[product_name]`; X-axis Total Revenue | Filters pane → product_name → **Top N** = 10 by Total Revenue |
| Bar chart: top 10 products by profit | Same as above, using Total Profit | Shows that the profit leaders are all clothing |
| Clustered column chart: revenue and profit by category | X-axis `dim_product[category]`; Y-axis Total Revenue, Total Profit | |
| Bar chart: gross margin by category | Y-axis category; X-axis Gross Margin % | Turn on data labels |
| Scatter chart | X-axis Total Revenue; Y-axis Gross Margin %; Values `product_name`; Legend `category`; Size Units Sold | Revenue vs margin per product |
| Table | product_name, category, Units Sold, Total Revenue, Total Profit, Gross Margin %, Product Profit Rank | Sort by rank |

## Page 3: Customer Intelligence

| Visual | Fields | Notes |
|---|---|---|
| Cards | Total Customers, Repeat Customer Rate, At-Risk Customers, Value at Risk | |
| Bar chart: RFM segments | Y-axis `dim_customer[rfm_segment]`; X-axis Customers in Segment | Add a second bar chart with **Segment Revenue** |
| Donut chart: customer status | Legend `dim_customer[customer_status]`; Values Customers in Segment | |
| Matrix: cohort retention | Rows `cohort_retention[cohort]`; Columns `quarters_since_first`; Values `retention_pct` (Max) | Format → Cell elements → **Background colour** (gradient). Filter out `quarters_since_first` = 0 |
| Table: top 10 customers | `dim_customer[customer_id]`, `preferred_store`, `orders`, `lifetime_spend_kes`, `rfm_segment`, `recency_days` | Filters pane → Top N 10 by lifetime_spend_kes |
| Table: at-risk win-back list | Same columns plus `model_churn_probability` | Filter `at_risk_rule` = 1; sort by lifetime_spend_kes descending |
| Slicer | `dim_customer[preferred_store]` | Customer visuals filter by **preferred store** (see the note below) |

> **Note:** the `dim_customer` visuals summarize each customer's whole 2024–2025 history at 31 Dec 2025, so the
> **date slicer does not change them**. That is intentional: RFM and at-risk status are measured at one point in time.
> Use the `preferred_store` slicer on this page instead.

## Page 4: Store Performance

| Visual | Fields | Notes |
|---|---|---|
| Clustered bar chart: revenue and profit by store | Y-axis `dim_store[town]`; X-axis Total Revenue, Total Profit | |
| Bar chart: revenue by county | Y-axis `dim_store[county]`; X-axis Total Revenue | |
| Bar chart: revenue per m² | Y-axis town; X-axis Revenue per m2 | Thika leads, which is the space-efficiency insight |
| Table: store ranking | town, county, store_format, Store Revenue Rank, Total Revenue, Total Profit, Gross Margin %, Average Order Value, Revenue YoY % | Sort by rank. Add **conditional formatting** to Revenue YoY % (red for negative, green for positive) |
| Matrix: category mix | Rows town; Columns category; Values Total Revenue | Show values as **Percent of row total** |
| Optional: map | Location `dim_store[town]` (category: City) + county | Needs an internet connection; skip it if the map does not load |

## Page 5: Demand Forecasting

This page uses `fact_forecast` and `model_metrics`, so the shared slicers do not apply to it.

| Visual | Fields | Notes |
|---|---|---|
| Line chart: actual vs forecast | X-axis `fact_forecast[month]`; Y-axis `actual`, `Holt exponential smoothing`, `Random Forest (store panel)` (all Sum) | Shows actual vs predicted |
| Same line chart: uncertainty | Add `lower_80` and `upper_80` as two more lines | Format them as dashed grey lines. Alternatively use **Analytics → Error bars** on the Holt line if your version has it |
| Cards | Jan 2026 Forecast, Forecast Range 80%, Seasonal Scenario, Test MAE (Holt) | |
| Table: model accuracy | `model_metrics`: model, validation_MAE, test_MAE, test_MAPE_% | Filter model_type = "forecast (chain)" |
| Bar chart: store split | `forecast_store_jan2026`: town, forecast_kes | Label it "Rough allocation guide" |
| Text box | Forecast interpretation (see below) | |

---

## Step 9: Finishing touches (20 min)

1. **Sync the slicers.**
   - Select a slicer and click **View → Sync slicers**.
   - Tick pages 1, 2 and 4 under both *Sync* and *Visible*.
   - On page 3, tick only the Store and Date slicers, so they apply to the `fact_sales` visuals there.
2. **Navigation buttons (optional).** Click **Insert → Buttons → Navigator → Page navigator** and place it at the top of each page.
3. **Check every visual has a clear title.** Rename the default "Sum of …" titles.
4. **Check the numbers against the analysis** with all slicers cleared:
   - Total Revenue **2,179,215**
   - Total Profit **538,802**
   - Total Orders **2,650**
   - Average Order Value **822**
   - At-Risk Customers **249**
   - Champions **68**
5. **Take screenshots.** Save one PNG of each page in `milestone_7_dashboard/screenshots/`, named `01_executive_overview.png` to `05_demand_forecasting.png`. Type the names **without** `.png`, because Snipping Tool adds the extension itself.

---

## Management insights (paste into the text boxes)

**Executive Overview:**
- Revenue grew 8.8% in 2025, but units sold fell 4.7%. Growth came from prices and basket size, not volume.
- December is the peak and January the trough in both years. Build stock from November.

**Product Performance:**
- Clothing earns 46% of profit on 27% of revenue (42% margin). School uniforms are the top profit product.
- Groceries are 25% of revenue but only 12% of profit. Keep prices competitive and avoid deep discounts.

**Customer Intelligence:**
- The top 20% of customers produce 61% of revenue. Only 23% of customers ever return.
- 249 established customers (KES 542K of lifetime spend) have been silent for more than 180 days. Start a win-back
  campaign with the highest-value customers first.

**Store Performance:**
- Nairobi CBD and Westlands generate 44% of revenue.
- Thika earns the most per m² but is shrinking (−19% excluding electronics). Mombasa has the smallest baskets.

**Demand Forecasting:**
- The model expects an underlying level of about KES 99K for January 2026 (80% range KES 82–121K).
- January is seasonally weak (previous Januaries were KES 65–70K), so plan for about KES 75–85K.
