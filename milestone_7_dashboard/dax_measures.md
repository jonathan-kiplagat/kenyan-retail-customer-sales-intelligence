# DAX Measures and KPI Definitions

**How to add a measure:**
1. In the **Data** pane, right-click the table named under each heading below (usually **fact_sales**) and choose **New measure**.
2. Paste one measure into the formula bar and press Enter.
3. Set the format in **Measure tools** (KES = *Currency* or *Whole number*; % = *Percentage*).

> **Tip:** create a dedicated folder for measures first. Choose **Home → Enter data**, name the table `_Measures`, then load it. Put every measure in that table so they are easy to find.

---

## 1. Core sales KPIs (Executive Overview)

```DAX
Total Revenue = SUM ( fact_sales[net_revenue] )
```
**Definition:** net revenue in KES after promotional discounts. Format: whole number.

```DAX
Total Profit = SUM ( fact_sales[profit] )
```
**Definition:** gross profit = net revenue − cost of goods sold.

```DAX
Gross Margin % = DIVIDE ( [Total Profit], [Total Revenue] )
```
**Definition:** profit as a share of revenue. Format: percentage, 1 decimal place.

```DAX
Total Orders = DISTINCTCOUNT ( fact_sales[order_id] )
```
**Definition:** number of receipts (baskets), not product lines.

```DAX
Total Customers =
CALCULATE (
    DISTINCTCOUNT ( fact_sales[customer_id] ),
    NOT ISBLANK ( fact_sales[customer_id] )
)
```
**Definition:** identified customers who bought in the selected period. Walk-in sales without a customer ID are excluded.

```DAX
Average Order Value = DIVIDE ( [Total Revenue], [Total Orders] )
```
**Definition:** revenue per receipt. Calculated per order, not per line.

```DAX
Units Sold = SUM ( fact_sales[quantity] )
```

```DAX
Discounts Given = SUM ( fact_sales[discount_amount] )
```

## 2. Time intelligence (requires dim_date marked as the date table)

```DAX
Revenue Previous Year =
CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )
```

```DAX
Revenue YoY % =
DIVIDE ( [Total Revenue] - [Revenue Previous Year], [Revenue Previous Year] )
```
**Definition:** growth against the same period one year earlier. It is blank for 2024, because there is no 2023 data.

```DAX
Revenue 3M Rolling Avg =
VAR LastDate = MAX ( dim_date[date] )
RETURN
    DIVIDE (
        CALCULATE ( [Total Revenue], DATESINPERIOD ( dim_date[date], LastDate, -3, MONTH ) ),
        3
    )
```
**Definition:** average monthly revenue over the last 3 months. It smooths out the swings caused by single electronics sales.

## 3. Product and promotion measures

```DAX
Promotion Line Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_sales ), fact_sales[is_promo] = TRUE () ),
    COUNTROWS ( fact_sales )
)
```

```DAX
Product Profit Rank =
RANKX ( ALL ( dim_product[product_name] ), [Total Profit], , DESC, DENSE )
```

## 4. Store measures

```DAX
Store Revenue Rank =
RANKX ( ALL ( dim_store[town] ), [Total Revenue], , DESC, DENSE )
```

```DAX
Revenue per m2 =
DIVIDE ( [Total Revenue], SUM ( dim_store[floor_area_sqm] ) )
```
**Definition:** space efficiency, meaning revenue earned per square metre of selling floor.

## 5. Customer measures (table: dim_customer)

```DAX
Customers in Segment = COUNTROWS ( dim_customer )
```

```DAX
Repeat Customer Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[orders] >= 2 ),
    CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[orders] >= 1 )
)
```
**Definition:** share of identified customers with two or more orders (2024–2025).

```DAX
At-Risk Customers =
CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[at_risk_rule] = 1 )
```
**Definition:** established customers (2+ orders) with no purchase for **more than 180 days** at 31 Dec 2025. The threshold comes from Milestone 6: 90% of repeat-purchase gaps are 173 days or shorter.

```DAX
Value at Risk =
CALCULATE ( SUM ( dim_customer[lifetime_spend_kes] ), dim_customer[at_risk_rule] = 1 )
```
**Definition:** the lifetime spend of at-risk customers, which shows how much customer value is drifting away.

```DAX
Segment Revenue = SUM ( dim_customer[lifetime_spend_kes] )
```

## 6. Forecast measures (table: fact_forecast)

```DAX
Jan 2026 Forecast =
CALCULATE ( MAX ( fact_forecast[Holt exponential smoothing] ), fact_forecast[split] = "forecast" )
```

```DAX
Forecast Range 80% =
VAR Lo = CALCULATE ( MAX ( fact_forecast[lower_80] ), fact_forecast[split] = "forecast" )
VAR Hi = CALCULATE ( MAX ( fact_forecast[upper_80] ), fact_forecast[split] = "forecast" )
RETURN "KES " & FORMAT ( Lo, "#,0" ) & " – " & FORMAT ( Hi, "#,0" )
```

```DAX
Seasonal Scenario =
CALCULATE ( MAX ( fact_forecast[seasonal_scenario] ), fact_forecast[split] = "forecast" )
```

```DAX
Test MAE (Holt) =
CALCULATE (
    MAX ( model_metrics[test_MAE] ),
    model_metrics[model] = "Holt exponential smoothing",
    model_metrics[model_type] = "forecast (chain)"
)
```

---

## KPI definition table (for the documentation)

| KPI | Formula | Meaning for management |
|---|---|---|
| Total Revenue | Σ net revenue | Money taken after discounts |
| Total Profit | Σ (net revenue − cost) | What the sales actually earned |
| Gross Margin % | Profit ÷ Revenue | How much of each shilling is profit |
| Total Orders | Distinct receipts | Customer visits that resulted in a purchase |
| Total Customers | Distinct identified customers | Reach of the loyalty base |
| Average Order Value | Revenue ÷ Orders | Typical basket (the median is about KES 450; the mean is skewed upwards) |
| Revenue YoY % | (This year − last year) ÷ last year | Growth (driven by price in 2025; units fell) |
| Revenue per m² | Revenue ÷ floor area | Store space efficiency |
| Repeat Customer Rate | Customers with 2+ orders ÷ customers | Loyalty (23% in this data) |
| At-Risk Customers | Established and silent > 180 days | Win-back target list |
| Value at Risk | Lifetime spend of at-risk customers | Size of the retention opportunity |
| Jan 2026 Forecast | Holt exponential smoothing | Expected underlying level; plan around the range and the seasonal scenario |
