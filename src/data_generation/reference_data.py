"""Hand-designed reference tables: stores, products and promotion campaigns.

All store names, brands, prices and costs are FICTIONAL and illustrative. Prices
are plausible Kenyan supermarket shelf prices in KES, not verified market data.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Stores
# traffic_weight  -> share of customers who choose this store as "home" store
# basket_factor   -> multiplier on items per basket (affluent areas buy more)
# These two columns drive the simulation and are NOT exported to stores.csv.
# ---------------------------------------------------------------------------
STORES = pd.DataFrame(
    [
        ("S01", "Duka Bora Nairobi CBD", "Nairobi CBD", "Nairobi", "Flagship", "2016-03-01", 2400, 0.25, 1.00),
        ("S02", "Duka Bora Westlands", "Westlands", "Nairobi", "Flagship", "2018-08-15", 2100, 0.20, 1.35),
        ("S03", "Duka Bora Thika", "Thika", "Kiambu", "Compact", "2021-02-01", 900, 0.11, 0.85),
        ("S04", "Duka Bora Mombasa", "Mombasa Town", "Mombasa", "Standard", "2017-11-20", 1600, 0.17, 1.00),
        ("S05", "Duka Bora Kisumu", "Kisumu Town", "Kisumu", "Standard", "2019-06-10", 1300, 0.13, 0.90),
        ("S06", "Duka Bora Nakuru", "Nakuru Town", "Nakuru", "Standard", "2020-09-01", 1400, 0.14, 0.95),
    ],
    columns=[
        "store_id", "store_name", "town", "county", "store_format",
        "opening_date", "floor_area_sqm", "traffic_weight", "basket_factor",
    ],
)

# ---------------------------------------------------------------------------
# Products (40 across 6 categories)
# popularity     -> relative chance of being picked within its category
# mean_quantity  -> typical units per line (staples bought in multiples)
# Margins follow typical retail patterns: staples thin, clothing wide.
# ---------------------------------------------------------------------------
_PRODUCT_ROWS = [
    # product_id, name, category, brand, pack_size, price_kes, cost_kes, popularity, mean_qty
    ("P001", "Maize Flour", "Food and Groceries", "Shamba Gold", "2 kg", 185, 162, 10, 2.2),
    ("P002", "Wheat Flour", "Food and Groceries", "Shamba Gold", "2 kg", 195, 170, 6, 1.6),
    ("P003", "Long Grain Rice", "Food and Groceries", "Pwani Grains", "5 kg", 1050, 920, 5, 1.1),
    ("P004", "White Sugar", "Food and Groceries", "Sukari Bora", "2 kg", 330, 298, 8, 1.5),
    ("P005", "Vegetable Cooking Oil", "Food and Groceries", "Mafuta Safi", "3 L", 1120, 985, 6, 1.1),
    ("P006", "Fresh Milk", "Food and Groceries", "Maziwa Fresh", "500 ml", 65, 55, 10, 3.0),
    ("P007", "White Bread", "Food and Groceries", "Mkate Poa", "400 g", 70, 60, 9, 1.8),
    ("P008", "Eggs Tray", "Food and Groceries", "Kuku Farm", "30 pcs", 480, 420, 5, 1.1),
    ("P009", "Black Tea Leaves", "Food and Groceries", "Kericho Highlands", "500 g", 320, 265, 6, 1.2),
    ("P010", "Dry Beans", "Food and Groceries", "Shamba Gold", "1 kg", 210, 180, 5, 1.5),
    ("P011", "Bottled Water", "Beverages", "Aqua Mlima", "1.5 L", 80, 60, 10, 2.5),
    ("P012", "Cola Soda", "Beverages", "Fizzy Kola", "2 L", 210, 165, 9, 1.6),
    ("P013", "Mango Juice", "Beverages", "Tunda", "1 L", 250, 195, 6, 1.4),
    ("P014", "Instant Coffee", "Beverages", "Kahawa Gold", "100 g", 550, 430, 4, 1.1),
    ("P015", "Energy Drink", "Beverages", "Nguvu", "500 ml", 150, 115, 5, 1.8),
    ("P016", "Drinking Chocolate", "Beverages", "Cocoa Joy", "400 g", 480, 370, 3, 1.1),
    ("P017", "Natural Yoghurt", "Beverages", "Maziwa Fresh", "500 ml", 140, 108, 6, 1.6),
    ("P018", "Laundry Detergent", "Household Products", "Safi Wash", "1 kg", 380, 290, 9, 1.3),
    ("P019", "Bar Soap", "Household Products", "Safi Wash", "800 g", 230, 175, 8, 1.6),
    ("P020", "Dishwashing Liquid", "Household Products", "Ng'aa", "750 ml", 260, 195, 7, 1.2),
    ("P021", "Toilet Paper", "Household Products", "Soft Touch", "10 rolls", 450, 340, 8, 1.2),
    ("P022", "Bleach", "Household Products", "Ng'aa", "1 L", 180, 130, 5, 1.2),
    ("P023", "Insecticide Spray", "Household Products", "Kinga", "400 ml", 520, 385, 4, 1.0),
    ("P024", "Mop and Bucket Set", "Household Products", "Safi Home", "1 set", 1250, 880, 2, 1.0),
    ("P025", "Toothpaste", "Personal Care", "Tabasamu", "150 g", 220, 155, 9, 1.5),
    ("P026", "Body Lotion", "Personal Care", "Ngozi", "400 ml", 450, 310, 7, 1.1),
    ("P027", "Shampoo", "Personal Care", "Nywele", "400 ml", 520, 360, 5, 1.0),
    ("P028", "Sanitary Pads", "Personal Care", "Comfy", "10 pcs", 150, 105, 8, 1.6),
    ("P029", "Deodorant Spray", "Personal Care", "Fresh Day", "150 ml", 380, 260, 5, 1.0),
    ("P030", "Baby Diapers", "Personal Care", "Mtoto Care", "40 pcs", 1350, 1000, 4, 1.1),
    ("P031", "Men's Cotton T-Shirt", "Clothing", "Kitenge Wear", "1 pc", 850, 470, 7, 1.4),
    ("P032", "Women's Kitenge Dress", "Clothing", "Kitenge Wear", "1 pc", 2400, 1300, 4, 1.0),
    ("P033", "School Uniform Set", "Clothing", "Shule Smart", "1 set", 1800, 1050, 5, 1.3),
    ("P034", "Denim Jeans", "Clothing", "Urban Threads", "1 pc", 2200, 1200, 4, 1.0),
    ("P035", "Canvas Shoes", "Clothing", "Hatua", "1 pair", 1500, 850, 5, 1.1),
    ("P036", "Smartphone 64GB", "Electronics", "Simu X", "1 unit", 14999, 12600, 2, 1.0),
    ("P037", "32-inch LED TV", "Electronics", "Skyview", "1 unit", 21999, 18400, 1, 1.0),
    ("P038", "Bluetooth Earphones", "Electronics", "Sauti", "1 unit", 1800, 1350, 6, 1.0),
    ("P039", "Electric Kettle", "Electronics", "Jiko Smart", "1.7 L", 2500, 1950, 5, 1.0),
    ("P040", "Solar Lantern", "Electronics", "Mwangaza", "1 unit", 3200, 2600, 4, 1.0),
]

PRODUCTS = pd.DataFrame(
    _PRODUCT_ROWS,
    columns=[
        "product_id", "product_name", "category", "brand", "pack_size",
        "selling_price_kes", "unit_cost_kes", "popularity", "mean_quantity",
    ],
)

CATEGORIES = [
    "Food and Groceries", "Beverages", "Household Products",
    "Personal Care", "Clothing", "Electronics",
]

# Baseline share of basket lines by category (before seasonal/store tilts).
CATEGORY_BASE_WEIGHTS = {
    "Food and Groceries": 0.40,
    "Beverages": 0.20,
    "Household Products": 0.15,
    "Personal Care": 0.13,
    "Clothing": 0.08,
    "Electronics": 0.04,
}

# Annual shelf-price review on 1 January 2025: prices and costs rise 4%.
PRICE_REVIEW_DATE = "2025-01-01"
PRICE_REVIEW_UPLIFT = 0.04

# ---------------------------------------------------------------------------
# Promotion campaigns: each targets ONE category for a fixed window.
# ---------------------------------------------------------------------------
PROMOTIONS = pd.DataFrame(
    [
        ("PR01", "New Year Grocery Saver", "Seasonal", "2024-01-02", "2024-01-14", "Food and Groceries", 0.10),
        ("PR02", "Back-to-School January", "Back-to-school", "2024-01-02", "2024-01-21", "Clothing", 0.15),
        ("PR03", "Valentine's Self-Care Week", "Seasonal", "2024-02-07", "2024-02-14", "Personal Care", 0.12),
        ("PR04", "Easter Feast Deals", "Holiday", "2024-03-22", "2024-04-01", "Food and Groceries", 0.10),
        ("PR05", "Eid Celebration Drinks", "Holiday", "2024-04-03", "2024-04-12", "Beverages", 0.12),
        ("PR06", "Back-to-School May", "Back-to-school", "2024-04-25", "2024-05-05", "Clothing", 0.15),
        ("PR07", "Mid-Year Home Clean", "Category", "2024-06-20", "2024-07-07", "Household Products", 0.15),
        ("PR08", "Back-to-School September", "Back-to-school", "2024-08-25", "2024-09-05", "Clothing", 0.15),
        ("PR09", "Black Friday Electronics", "Seasonal", "2024-11-25", "2024-12-01", "Electronics", 0.20),
        ("PR10", "Festive Season Drinks", "Holiday", "2024-12-15", "2024-12-31", "Beverages", 0.15),
        ("PR11", "New Year Grocery Saver", "Seasonal", "2025-01-02", "2025-01-14", "Food and Groceries", 0.10),
        ("PR12", "Back-to-School January", "Back-to-school", "2025-01-02", "2025-01-19", "Clothing", 0.15),
        ("PR13", "Valentine's Self-Care Week", "Seasonal", "2025-02-07", "2025-02-14", "Personal Care", 0.12),
        ("PR14", "Eid Celebration Drinks", "Holiday", "2025-03-25", "2025-04-02", "Beverages", 0.12),
        ("PR15", "Easter Feast Deals", "Holiday", "2025-04-10", "2025-04-21", "Food and Groceries", 0.10),
        ("PR16", "Back-to-School May", "Back-to-school", "2025-04-24", "2025-05-04", "Clothing", 0.15),
        ("PR17", "Mid-Year Home Clean", "Category", "2025-06-19", "2025-07-06", "Household Products", 0.15),
        ("PR18", "Back-to-School September", "Back-to-school", "2025-08-24", "2025-09-04", "Clothing", 0.15),
        ("PR19", "Black Friday Electronics", "Seasonal", "2025-11-24", "2025-11-30", "Electronics", 0.20),
        ("PR20", "Festive Season Drinks", "Holiday", "2025-12-15", "2025-12-31", "Beverages", 0.15),
    ],
    columns=[
        "promotion_id", "promotion_name", "promotion_type",
        "start_date", "end_date", "target_category", "discount_percentage",
    ],
)

PAYMENT_METHODS = ["M-Pesa", "Cash", "Debit/Credit Card", "Bank Transfer"]
