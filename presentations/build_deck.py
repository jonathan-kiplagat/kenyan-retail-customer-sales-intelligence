"""Build the Milestone 8 defence deck with python-pptx.

Run from the project root:
    python presentations/build_deck.py

Writes presentations/Duka_Bora_Capstone_Defence.pptx (17 slides with speaker notes and native charts).
"""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION, XL_MARKER_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
OUT = ROOT / "presentations" / "Duka_Bora_Capstone_Defence.pptx"

# Palette: deep green dominates (fresh-produce retail), orange accent and blue data series match the dashboard.
GREEN = "12372A"
GREEN_2 = "1F5A45"
TINT = "EDF3EF"
ORANGE = "EB6834"
BLUE = "2A78D6"
INK = "1B1B1B"
MUTED = "5F6B66"
WHITE = "FFFFFF"
GRID = "D9DFDB"
RED = "C0392B"
OK = "1E8449"
HEAD = "Cambria"
BODY = "Calibri"


def rgb(h):
    return RGBColor.from_string(h)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, paras, size=16, color=INK, font=BODY, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None, space_after=6, margin=0.05):
    """paras: str or list of str / list of runs [(text, {opts})]; a str starting with '• ' becomes a bullet."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(margin))
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        runs = p if isinstance(p, list) else [(p, {})]
        bullet = isinstance(p, str) and p.startswith("• ")
        if bullet:
            runs = [(p[2:], {})]
            _bullet(para)
        for t, o in runs:
            r = para.add_run()
            r.text = t
            f = r.font
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.name = o.get("font", font)
            f.color.rgb = rgb(o.get("color", color))
    return tb


def _bullet(para):
    from pptx.oxml.ns import qn
    pPr = para._p.get_or_add_pPr()
    pPr.set("marL", str(Inches(0.25)))
    pPr.set("indent", str(-Inches(0.2)))
    bu = pPr.makeelement(qn("a:buChar"), {"char": "•"})
    pPr.append(bu)


def box(slide, x, y, w, h, fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line=None, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def circle_num(slide, x, y, d, label, fill=ORANGE, color=WHITE, size=16):
    c = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", 0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size, r.font.bold, r.font.name = Pt(size), True, BODY
    r.font.color.rgb = rgb(color)
    return c


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = rgb(color)


PAGE = [0]


def content_slide(title, notes):
    s = prs.slides.add_slide(BLANK)
    PAGE[0] += 1
    bg(s, WHITE)
    text(s, 0.6, 0.4, 12.1, 0.9, title, size=30, font=HEAD, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE,
         name="Title")
    text(s, 9.7, 6.95, 3.0, 0.35, f"Duka Bora capstone  |  {PAGE[0]}", size=10, color=MUTED, align=PP_ALIGN.RIGHT,
         name="Footer")
    s.notes_slide.notes_text_frame.text = notes
    return s


def stat(slide, x, y, w, h, big, label, big_color=GREEN, fill=TINT, big_size=36):
    box(slide, x, y, w, h, fill=fill)
    text(slide, x + 0.2, y + 0.1, w - 0.4, 0.68, big, size=big_size, font=HEAD, bold=True, color=big_color,
         anchor=MSO_ANCHOR.MIDDLE)
    text(slide, x + 0.2, y + 0.8, w - 0.4, h - 0.9, label, size=14, color=INK)


def style_chart(chart, legend=True, size=12):
    chart.font.size = Pt(size)
    chart.font.name = BODY
    chart.font.color.rgb = rgb(MUTED)
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)
    va = chart.value_axis
    va.major_gridlines.format.line.color.rgb = rgb(GRID)
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(size)
    ca = chart.category_axis
    ca.format.line.color.rgb = rgb(GRID)
    ca.tick_labels.font.size = Pt(size)
    ca.has_major_gridlines = False


# ---------------------------------------------------------------------------------------------------------------
# 1. Title
s = prs.slides.add_slide(BLANK)
PAGE[0] += 1
bg(s, GREEN)
text(s, 0.8, 1.6, 11.5, 0.5, "LUXDEVHQ DATA SCIENCE AND ANALYTICS CAPSTONE", size=16, bold=True, color="9FD3B8")
text(s, 0.8, 2.2, 11.5, 1.9, "Customer and Sales Intelligence for a Kenyan Retailer", size=44, font=HEAD,
     bold=True, color=WHITE)
text(s, 0.8, 4.2, 11.5, 0.6, "Evidence for stock, promotion and retention decisions at Duka Bora Supermarkets",
     size=20, color="DCEBE3")
text(s, 0.8, 5.6, 11.5, 0.9, ["Jonathan Kiplagat", "Final defence  |  Data: 2024–2025, 6 stores, KES"], size=16,
     color=WHITE, space_after=2)
s.notes_slide.notes_text_frame.text = (
    "Good morning. My capstone answers four management questions for Duka Bora, a six-store Kenyan supermarket "
    "chain, using two years of sales data. The data is synthetic by design, which I will explain, and the only "
    "real external data is the Kenyan public-holiday calendar. I'll take about 15 minutes, then questions.")

# 2. The problem
s = content_slide("Duka Bora records every sale but decides on intuition", (
    "Management records every sale but makes stock, promotion and retention decisions on intuition. They asked "
    "four questions, and every milestone of the project feeds at least one of them. Success meant answering each "
    "with evidence, checked in more than one tool."))
qs = [("1", "What drives revenue and profit?", "Products, categories, prices and promotions"),
      ("2", "Who buys, where and when?", "Customers, stores, seasons and the daily rhythm"),
      ("3", "Which customers are drifting away?", "Valuable customers who have gone quiet"),
      ("4", "What demand should we expect?", "Next month's revenue, with a realistic range")]
for i, (n, q, sub) in enumerate(qs):
    x, y = 0.6 + (i % 2) * 6.15, 1.7 + (i // 2) * 2.45
    box(s, x, y, 5.95, 2.2)
    circle_num(s, x + 0.35, y + 0.4, 0.7, n, size=20)
    text(s, x + 1.3, y + 0.3, 4.4, 1.0, q, size=22, font=HEAD, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 1.3, y + 1.35, 4.4, 0.7, sub, size=16, color=INK)

# 3. Answers at a glance
s = content_slide("The answers at a glance", (
    "Here are the four answers up front. Revenue is 2.18 million shillings at a 24.7% margin, but growth was price-"
    "led: units fell. 249 established customers have gone quiet. And January should be planned at 75 to 85 thousand, "
    "below the model's underlying level, because January is reliably weak. The rest of the talk shows the evidence."))
cards = [("KES 2.18M", "Revenue at a 24.7% margin. Clothing earns 46% of profit", GREEN),
         ("−4.7%", "Units sold in 2025, while revenue grew 8.8%: growth is price-led", ORANGE),
         ("249", "Established customers silent for over 180 days (KES 542K lifetime spend)", GREEN),
         ("KES 75–85K", "Planning figure for January 2026 (model level KES 99K)", GREEN)]
for i, (big, lab, col) in enumerate(cards):
    stat(s, 0.6 + i * 3.075, 1.8, 2.9, 2.0, big, lab, big_color=col, big_size=30)
text(s, 0.6, 4.3, 12.1, 1.8, [
    [("Top three actions: ", {"bold": True, "color": GREEN}),
     ("protect clothing margins, cap promotion discounts below category margin, and run a measured win-back "
      "campaign for the 249 at-risk customers.", {})]], size=20)

# 4. Approach
s = content_slide("Eight milestones, one reproducible pipeline", (
    "The work follows CRISP-DM. Synthetic data is generated from documented, seeded rules, then cleaned, explored, "
    "loaded into PostgreSQL, tested statistically, modelled and put into Power BI. All logic lives in a src package, "
    "the notebooks are executed, and 28 automated tests guard the data, the statistics functions and model leakage."))
steps = ["Frame", "Generate", "Clean", "Explore", "SQL", "Test", "Model", "Dashboard"]
tools = ["M1", "M1", "M2 pandas", "M3 Seaborn", "M4 PostgreSQL", "M5 SciPy", "M6 scikit-learn", "M7 Power BI"]
for i, (st, tl) in enumerate(zip(steps, tools)):
    x = 0.6 + i * 1.53
    circle_num(s, x + 0.36, 1.85, 0.75, str(i + 1), fill=GREEN if i % 2 == 0 else GREEN_2, size=20)
    text(s, x, 2.75, 1.47, 0.45, st, size=16, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    text(s, x, 3.15, 1.47, 0.45, tl, size=12, color=MUTED, align=PP_ALIGN.CENTER)
facts = [("3,000", "raw sales rows"), ("2,650", "receipts"), ("1,800", "customers"), ("40", "products, 6 categories"),
         ("6", "stores"), ("28", "real public holidays")]
for i, (big, lab) in enumerate(facts):
    x = 0.6 + i * 2.05
    box(s, x, 4.2, 1.9, 1.5)
    text(s, x + 0.1, 4.3, 1.7, 0.7, big, size=28, font=HEAD, bold=True, color=GREEN, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.1, 5.0, 1.7, 0.6, lab, size=14, align=PP_ALIGN.CENTER)
text(s, 0.6, 6.0, 12.1, 0.7, "Synthetic by design: shareable without privacy risk, and every pattern has a known "
     "cause that the analysis can be checked against.", size=16, color=MUTED)

# 5. Data quality
s = content_slide("Cleaning found all 126 injected data-quality issues", (
    "During generation I injected 126 realistic issues and logged each one. Cleaning was then audited against that "
    "log and against the true data: all 126 were found. The rule was evidence before assumption. The biggest catch: "
    "four quantity-999 entry errors would have added 1.44 million shillings of phantom revenue, almost doubling the "
    "chain's real revenue. The 28 values with no evidence were labelled, not guessed."))
stat(s, 0.6, 1.7, 3.6, 2.3, "126 / 126", "logged issues detected, checked cell by cell against the true data",
     big_size=34)
stat(s, 0.6, 4.2, 3.6, 2.3, "KES 1.44M", "phantom revenue avoided by correcting four quantity-999 errors",
     big_color=ORANGE, big_size=34)
rows = [("Issue", "Rows", "Decision"),
        ("Exact duplicates", "12", "Removed"),
        ("Payment label variants", "30", "Mapped to 4 standard labels"),
        ("Dates in DD/MM/YYYY", "15", "Parsed with an explicit format"),
        ("Missing payment method", "10", "3 recovered from receipt, 7 'Unknown'"),
        ("Missing customer ID", "25", "4 recovered, 21 flagged walk-in"),
        ("Quantity 999", "4", "Restored from the receipt total"),
        ("Bulk buys, big electronics", "2 + 356", "Kept: they reconcile")]
tbl = s.shapes.add_table(len(rows), 3, Inches(4.6), Inches(1.7), Inches(8.1), Inches(4.8)).table
for c, wd in enumerate([3.0, 0.9, 4.2]):
    tbl.columns[c].width = Inches(wd)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(GREEN if r == 0 else (TINT if r % 2 == 0 else WHITE))
        cell.margin_left = cell.margin_right = Inches(0.1)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.paragraphs[0].text = ""
        run = tf.paragraphs[0].add_run()
        run.text = val
        run.font.size, run.font.name = Pt(15), BODY
        run.font.bold = r == 0
        run.font.color.rgb = rgb(WHITE if r == 0 else INK)
        if c == 1:
            tf.paragraphs[0].alignment = PP_ALIGN.RIGHT

# 6. Growth is price-led
s = content_slide("Revenue grew 8.8%, but units fell 4.7%", (
    "The two lines are 2024 and 2025 by month. December is the peak and January the trough in both years. Revenue "
    "grew 8.8% and profit 10.7%, but units fell 4.7% and orders grew under 4%. The 4% price review in January 2025 "
    "and a richer basket mix explain the gap. If prices stop rising, revenue stalls, so units belong on the "
    "management dashboard next to revenue."))
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
rev = [64546, 73164, 106284, 106347, 93058, 76564, 67534, 72570, 104450, 60595, 99185, 119317,
       70471, 86167, 84030, 91047, 98379, 111928, 109353, 78915, 78927, 96734, 88843, 140808]
cd = CategoryChartData()
cd.categories = months
cd.add_series("2024", [v / 1000 for v in rev[:12]])
cd.add_series("2025", [v / 1000 for v in rev[12:]])
ch = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.6), Inches(1.6), Inches(8.2), Inches(5.0), cd).chart
style_chart(ch)
ch.has_title = True
ch.chart_title.text_frame.text = "Monthly net revenue (KES thousands)"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
ch.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(INK)
for ser, col in zip(ch.plots[0].series, [BLUE, ORANGE]):
    ser.smooth = False
    ser.format.line.color.rgb = rgb(col)
    ser.format.line.width = Pt(2.25)
    ser.marker.style = XL_MARKER_STYLE.CIRCLE
    ser.marker.size = 7
    ser.marker.format.fill.solid()
    ser.marker.format.fill.fore_color.rgb = rgb(col)
    ser.marker.format.line.color.rgb = rgb(WHITE)
ch.value_axis.tick_labels.number_format = '#,##0"K"'
ch.value_axis.tick_labels.number_format_is_linked = False
stat(s, 9.2, 1.6, 3.5, 1.55, "+8.8%", "revenue, 2025 vs 2024", big_size=32)
stat(s, 9.2, 3.3, 3.5, 1.55, "−4.7%", "units sold, 2025 vs 2024", big_color=ORANGE, big_size=32)
stat(s, 9.2, 5.0, 3.5, 1.55, "Dec ×2", "December revenue is about twice January's", big_size=32)

# 7. Clothing
s = content_slide("Clothing earns 46% of profit on 27% of revenue", (
    "Revenue share against profit share by category. Clothing is the profit engine at a 42% margin, and the top five "
    "profit products are all clothing, led by school uniforms. Groceries are the opposite: a quarter of revenue but "
    "only 12% of profit, so they build traffic, not profit. Some grocery and electronics promotions discounted more "
    "than the margin and kept only 1 to 3%."))
cats = ["Clothing", "Electronics", "Food and Groceries", "Personal Care", "Household", "Beverages"]
cd = CategoryChartData()
cd.categories = cats
cd.add_series("Share of revenue %", [27.3, 18.8, 25.4, 8.6, 9.2, 10.7])
cd.add_series("Share of profit %", [46.3, 14.0, 12.0, 9.9, 8.9, 8.8])
ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.6), Inches(8.2), Inches(5.0),
                        cd).chart
style_chart(ch)
plot = ch.plots[0]
plot.gap_width, plot.overlap = 60, -10
for ser, col in zip(plot.series, [BLUE, ORANGE]):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(col)
plot.has_data_labels = True
plot.data_labels.number_format = '0"%"'
plot.data_labels.number_format_is_linked = False
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
plot.data_labels.font.size = Pt(11)
plot.data_labels.font.color.rgb = rgb(INK)
ch.value_axis.visible = False
ch.value_axis.has_major_gridlines = False
box(s, 9.2, 1.6, 3.5, 5.0)
text(s, 9.45, 1.8, 3.0, 4.7, [
    [("Clothing", {"bold": True, "color": GREEN, "size": 18})],
    "42% margin. The top 5 profit products are all clothing; school uniforms lead (KES 60.9K profit).",
    [("Groceries", {"bold": True, "color": GREEN, "size": 18})],
    "25% of revenue, 12% of profit (11.7% margin). Traffic builders.",
    [("Promotions", {"bold": True, "color": ORANGE, "size": 18})],
    "10% off groceries and 20% off electronics left 1–3% margin."], size=15, space_after=8)

# 8. Customers
s = content_slide("A few customers carry the revenue, and many are drifting", (
    "The top 20% of customers produce 61% of revenue, yet only 23% of customers ever come back. RFM segmentation, "
    "built identically in SQL, Python and Power BI, finds 68 Champions producing 14.7% of revenue. The worrying "
    "groups are 'Cannot Lose Them' and 'At Risk': 55 formerly frequent customers who have gone quiet."))
segs = [("Champions", 68), ("Loyal Customers", 35), ("Potential Loyalists", 67), ("New / Recent One-off", 361),
        ("Cannot Lose Them", 31), ("At Risk", 24), ("Needs Attention", 394), ("Hibernating", 413), ("Lost", 395)]
cd = CategoryChartData()
cd.categories = [n for n, _ in reversed(segs)]
cd.add_series("Customers", [v for _, v in reversed(segs)])
ch = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.6), Inches(7.4), Inches(5.0), cd).chart
style_chart(ch, legend=False)
ch.has_title = True
ch.chart_title.text_frame.text = "Customers by RFM segment (31 Dec 2025)"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
ch.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(INK)
plot = ch.plots[0]
plot.gap_width = 45
ser = plot.series[0]
ser.format.fill.solid()
ser.format.fill.fore_color.rgb = rgb(GRID)
highlight = {"Champions": GREEN, "Cannot Lose Them": ORANGE, "At Risk": ORANGE}
for idx, (n, _) in enumerate(reversed(segs)):
    if n in highlight:
        pt = ser.points[idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(highlight[n])
plot.has_data_labels = True
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
plot.data_labels.font.size = Pt(11)
plot.data_labels.font.color.rgb = rgb(INK)
ch.value_axis.visible = False
ch.value_axis.has_major_gridlines = False
stat(s, 8.4, 1.6, 4.3, 1.55, "61%", "of revenue comes from the top 20% of customers", big_size=32)
stat(s, 8.4, 3.3, 4.3, 1.55, "23.4%", "of customers ever return for a second order", big_color=ORANGE, big_size=32)
stat(s, 8.4, 5.0, 4.3, 1.55, "42% vs 15%", "repeat rate, loyalty members vs non-members", big_size=32)

# 9. Stores
s = content_slide("Thika is the most efficient store but is shrinking", (
    "Nairobi CBD and Westlands generate 44% of revenue. Growth figures need care: single electronics sales swing "
    "small stores, so I also checked growth without electronics. Kisumu's 38% shrinks to 3.5%, but Thika's decline "
    "deepens to minus 19%, even though Thika earns the most per square metre. Mombasa has the smallest baskets."))
rows = [("Store", "Revenue (KES)", "Margin", "Avg order", "2025 growth", "Revenue / m²"),
        ("Nairobi CBD", "525,975", "24.3%", "818", "+16.9%", "219"),
        ("Westlands", "433,184", "26.0%", "899", "+8.7%", "206"),
        ("Nakuru Town", "335,755", "25.5%", "905", "−8.6%", "240"),
        ("Kisumu Town", "317,705", "22.5%", "892", "+38.2%", "244"),
        ("Mombasa Town", "309,861", "25.5%", "677", "+11.5%", "194"),
        ("Thika", "256,735", "24.2%", "755", "−14.2%", "285")]
tbl = s.shapes.add_table(len(rows), 6, Inches(0.6), Inches(1.7), Inches(8.3), Inches(4.2)).table
for c, wd in enumerate([1.75, 1.55, 1.0, 1.1, 1.35, 1.55]):
    tbl.columns[c].width = Inches(wd)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.fill.solid()
        is_thika = row[0] == "Thika"
        cell.fill.fore_color.rgb = rgb(GREEN if r == 0 else ("FCE9E1" if is_thika else (TINT if r % 2 == 0 else WHITE)))
        cell.margin_left = cell.margin_right = Inches(0.1)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = ""
        run = p.add_run()
        run.text = val
        run.font.size, run.font.name = Pt(15), BODY
        run.font.bold = r == 0 or (c == 5 and is_thika)
        col = WHITE if r == 0 else INK
        if c == 4 and r > 0:
            col = RED if val.startswith("−") else OK
        run.font.color.rgb = rgb(col)
        if c > 0:
            p.alignment = PP_ALIGN.RIGHT
text(s, 0.6, 6.1, 8.3, 0.6, "Growth is red when negative and green when positive.", size=12, color=MUTED)
box(s, 9.3, 1.7, 3.4, 4.9)
text(s, 9.55, 1.9, 2.9, 4.6, [
    [("44%", {"bold": True, "color": GREEN, "size": 26, "font": HEAD})],
    "of revenue from Nairobi CBD and Westlands.",
    [("−19%", {"bold": True, "color": ORANGE, "size": 26, "font": HEAD})],
    "Thika's change excluding electronics, despite the best revenue per m².",
    [("KES 677", {"bold": True, "color": GREEN, "size": 26, "font": HEAD})],
    "Mombasa's average basket, vs 822 chain-wide."], size=15, space_after=4)

# 10. SQL
s = content_slide("A normalized PostgreSQL database reconciles to the cent", (
    "The cleaned data is loaded into a third-normal-form PostgreSQL database. Receipt-level facts are stored once in "
    "the orders table, and money columns are generated by the database so they cannot disagree with quantity and "
    "price. Seven scripts answer the business questions with joins, CTEs and window functions. The data-quality "
    "script proves the database revenue matches Python on all 2,988 lines."))
img = ROOT / "milestone_4_sql" / "screenshots" / "02_er_diagram.png"
pic = s.shapes.add_picture(str(img), Inches(0.6), Inches(1.6))
max_w, max_h = Inches(7.2), Inches(5.0)
ratio = min(max_w / pic.width, max_h / pic.height)
pic.width, pic.height = int(pic.width * ratio), int(pic.height * ratio)
pic.name = "ER diagram"
text(s, 0.6, 1.6 + pic.height / 914400 + 0.05, 7.2, 0.35, "DBeaver ER diagram of the retail schema", size=11,
     color=MUTED)
box(s, 8.2, 1.6, 4.5, 3.25)
text(s, 8.45, 1.75, 4.0, 3.0, [
    [("Design", {"bold": True, "color": GREEN, "size": 18})],
    "• 7 tables in 3NF: 2,650 orders, 2,988 lines",
    "• Generated money columns",
    "• CHECK rules from the cleaning stage",
    "• Staging load inside one transaction"], size=15, space_after=4)
box(s, 8.2, 5.0, 4.5, 1.6)
text(s, 8.45, 5.1, 4.0, 1.4, [
    [("KES 2,179,214.72", {"bold": True, "color": GREEN, "size": 22, "font": HEAD})],
    "database revenue = Python revenue, 0 mismatches on 2,988 lines"], size=14, space_after=2)

# 11. Statistics
s = content_slide("Significant is not the same as important", (
    "Each test was chosen after checking assumptions. The data is skewed, so the main tests are non-parametric, with "
    "effect sizes and confidence intervals. Promotions do lift units, by about half a unit per line, in all six "
    "categories, but not enough to pay for discounts above the margin. Stores differ significantly in order value, "
    "but the store explains just 0.3% of the variation: real, but not worth a store-specific strategy."))
rows = [("Question", "Test", "Result", "Effect size", "Meaning"),
        ("Promotions lift units?", "Mann-Whitney, Holm", "p < 0.001, 6 of 6 categories", "+0.49 units (CI 0.21–0.93)",
         "Small real uplift"),
        ("Order value by store?", "Kruskal-Wallis", "p = 0.017", "ε² = 0.003", "Real but tiny"),
        ("Units by category?", "Kruskal-Wallis", "p ≈ 10⁻⁵²", "ε² = 0.083", "Multi-buys fit staples"),
        ("Payment by category?", "Chi-square", "Holm p = 0.043", "V = 0.056", "Cards for electronics"),
        ("Time of day by category?", "Chi-square", "p = 0.33", "V = 0.043", "One staffing plan")]
tbl = s.shapes.add_table(len(rows), 5, Inches(0.6), Inches(1.7), Inches(12.1), Inches(4.0)).table
for c, wd in enumerate([2.6, 2.2, 2.7, 2.6, 2.0]):
    tbl.columns[c].width = Inches(wd)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(GREEN if r == 0 else (TINT if r % 2 == 0 else WHITE))
        cell.margin_left = cell.margin_right = Inches(0.1)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = ""
        run = p.add_run()
        run.text = val
        run.font.size, run.font.name = Pt(14), BODY
        run.font.bold = r == 0
        run.font.color.rgb = rgb(WHITE if r == 0 else INK)
text(s, 0.6, 5.95, 12.1, 0.8, [[("No causal claims: ", {"bold": True, "color": ORANGE}),
                                ("promotions were not randomly assigned, so the next step is a controlled "
                                 "store-level trial.", {})]], size=16)

# 12. Forecast
s = content_slide("The forecast is honest about its uncertainty", (
    "One-month-ahead forecasts, walk-forward, so each month uses only the past. Damped Holt had the lowest validation "
    "error and also ranked first on the untouched test months, with an MAE of 17,500 shillings, 16.5%. But it beats "
    "the naive baseline by only 5%, which is not conclusive on six months, and most of its test error is the December "
    "peak, because two years of data cannot support a validated seasonal model. For January 2026 it gives 98,800 "
    "with an 80% range of 82 to 121 thousand. Both previous Januaries were 65 to 70 thousand, so I recommend "
    "planning for 75 to 85 thousand."))
labels = [f"{m} {y}" for y in ("24", "25") for m in months] + ["Jan 26"]
holt = [None] * 12 + [91428, 87242, 87076, 86406, 87358, 89285, 93062, 95899, 93876, 92172, 93013, 92765, 98788]
cd = CategoryChartData()
cd.categories = labels
cd.add_series("Actual", [v / 1000 for v in rev] + [None])
cd.add_series("Holt forecast (selected)", [None if v is None else v / 1000 for v in holt])
cd.add_series("80% range, Jan 2026", [None] * 24 + [82.007])
cd.add_series("80% range high", [None] * 24 + [120.796])
ch = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.6), Inches(1.6), Inches(8.2), Inches(5.0), cd).chart
style_chart(ch, size=11)
ch.has_title = True
ch.chart_title.text_frame.text = "Monthly revenue: actual vs one-month-ahead forecast (KES thousands)"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
ch.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(INK)
ch.value_axis.tick_labels.number_format = '#,##0"K"'
ch.value_axis.tick_labels.number_format_is_linked = False
for i, ser in enumerate(ch.plots[0].series):
    ser.smooth = False
    col = [INK, BLUE, MUTED, MUTED][i]
    ser.marker.style = XL_MARKER_STYLE.CIRCLE if i < 2 else XL_MARKER_STYLE.DASH
    ser.marker.size = 6 if i < 2 else 14
    ser.marker.format.fill.solid()
    ser.marker.format.fill.fore_color.rgb = rgb(col)
    ser.marker.format.line.color.rgb = rgb(col)
    if i < 2:
        ser.format.line.color.rgb = rgb(col)
        ser.format.line.width = Pt(2.25 if i == 0 else 2)
    else:
        ser.format.line.fill.background()
# Hide the duplicate legend entry for the high end of the range.
from pptx.oxml.ns import qn
leg = ch.legend._element
le = leg.makeelement(qn("c:legendEntry"), {})
idx = le.makeelement(qn("c:idx"), {"val": "3"})
dl = le.makeelement(qn("c:delete"), {"val": "1"})
le.append(idx)
le.append(dl)
leg.insert(1, le)
stat(s, 9.2, 1.6, 3.5, 1.55, "KES 98.8K", "Jan 2026 point forecast (80% range 82–121K)", big_size=30)
stat(s, 9.2, 3.3, 3.5, 1.55, "KES 17.5K", "test MAE (16.5%); naive baseline 18.4K", big_size=30)
stat(s, 9.2, 5.0, 3.5, 1.55, "KES 75–85K", "recommended January plan: Januaries ran 65–70K", big_color=ORANGE,
     big_size=30)

# 13. Churn
s = content_slide("A simple rule finds non-returners with 93% precision", (
    "For churn, established customers are scored at a snapshot and labelled by whether they bought in the next six "
    "months. The 180-day threshold comes from the data: 90% of repeat-purchase gaps are 173 days or shorter. In "
    "cross-validation all three models tied, so the one-standard-error rule chose the simplest: silent for more than "
    "180 days. On a later, out-of-time test it reached AUC 0.80 with 93% precision. Logistic regression ranked "
    "slightly better, so it becomes the priority score. The Random Forest overfit. Today 249 customers are flagged."))
cd = CategoryChartData()
cd.categories = ["Recency rule (selected)", "Logistic regression", "Random Forest"]
cd.add_series("Train AUC", [0.75, 0.81, 0.96])
cd.add_series("Test AUC (later period)", [0.80, 0.83, 0.82])
ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.6), Inches(7.4), Inches(5.0),
                        cd).chart
style_chart(ch)
plot = ch.plots[0]
plot.gap_width, plot.overlap = 70, -10
for ser, col in zip(plot.series, [GRID, GREEN]):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(col)
plot.has_data_labels = True
plot.data_labels.number_format = "0.00"
plot.data_labels.number_format_is_linked = False
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
plot.data_labels.font.size = Pt(12)
plot.data_labels.font.color.rgb = rgb(INK)
ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = 0.5, 1.0
ch.value_axis.visible = False
ch.value_axis.has_major_gridlines = False
stat(s, 8.4, 1.6, 4.3, 1.55, "93%", "of customers the rule flagged really did not return", big_size=32)
stat(s, 8.4, 3.3, 4.3, 1.55, "249", "established customers flagged today, of 419", big_color=ORANGE, big_size=32)
stat(s, 8.4, 5.0, 4.3, 1.55, "KES 541,641", "lifetime spend of the flagged customers", big_size=32)

# 14. Dashboard
s = content_slide("A five-page Power BI dashboard for managers", (
    "The dashboard runs on a star schema exported from the project, with DAX measures that have written definitions. "
    "The five pages follow the management questions: overview, products, customers, stores and forecasting. Synced "
    "slicers and cross-filtering let a manager click a product or store and see everything update. Every headline "
    "number matches the Python and SQL results."))
shots = ["01_executive_overview", "03_customer_intelligence", "04_store_performance", "05_demand_forecasting"]
names = ["Executive Overview", "Customer Intelligence", "Store Performance", "Demand Forecasting"]
for i, (f, n) in enumerate(zip(shots, names)):
    x, y = 0.6 + (i % 2) * 6.15, 1.5 + (i // 2) * 2.75
    p = s.shapes.add_picture(str(ROOT / "milestone_7_dashboard" / "screenshots" / f"{f}.png"), Inches(x), Inches(y),
                             height=Inches(2.35))
    if p.width > Inches(5.95):
        r = Inches(5.95) / p.width
        p.width, p.height = int(p.width * r), int(p.height * r)
    p.left = Inches(x) + (Inches(5.95) - p.width) // 2
    x = p.left / 914400
    p.line.color.rgb = rgb(GRID)
    p.line.width = Pt(1)
    p.name = n
    text(s, x, y + p.height / 914400 + 0.03, p.width / 914400, 0.35, n, size=12, bold=True, color=GREEN, margin=0)

# 15. Recommendations
s = content_slide("Six recommendations, each with a measure of success", (
    "Six actions, each tied to evidence and a KPI. If management could do only one, it should be the win-back "
    "campaign: it targets 542 thousand shillings of past spend with a list that proved 93% precise, and the control "
    "group means its value can be measured rather than assumed."))
recs = [("Protect clothing margins", "Keep uniforms stocked before each term; no clothing discounts.",
         "KPI: clothing margin"),
        ("Cap promotion discounts", "Keep every discount below the category margin.", "KPI: margin per campaign"),
        ("Win back 249 customers", "Highest value first, with a random 20% control group.",
         "KPI: return rate vs control"),
        ("Investigate Thika", "Check competition and range before cutting stock.", "KPI: revenue excl. electronics"),
        ("Bundles in Mombasa", "Add-on displays to grow the smallest baskets.", "KPI: average order value"),
        ("Plan January at 75–85K", "Build stock from November for the December peak.", "KPI: forecast vs plan")]
for i, (h, b, k) in enumerate(recs):
    x, y = 0.6 + (i % 3) * 4.1, 1.65 + (i // 3) * 2.55
    box(s, x, y, 3.9, 2.35)
    circle_num(s, x + 0.25, y + 0.3, 0.6, str(i + 1), size=18)
    text(s, x + 1.0, y + 0.25, 2.75, 0.7, h, size=18, font=HEAD, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.25, y + 1.05, 3.45, 0.8, b, size=15)
    text(s, x + 0.25, y + 1.85, 3.45, 0.4, k, size=13, bold=True, color=ORANGE)

# 16. Limitations
s = content_slide("Limitations and next steps", (
    "The main limitation is that the data is synthetic: the methods transfer to real data, the figures do not. Two "
    "years is too short for a validated seasonal model, and promotion and loyalty effects are associations. The next "
    "steps follow directly: a seasonal model with more history, randomized trials for causal effects, basket "
    "analysis for the Mombasa bundles, and an automated refresh pipeline."))
box(s, 0.6, 1.7, 5.95, 4.9)
text(s, 0.9, 1.9, 5.4, 4.6, [
    [("Limitations", {"bold": True, "color": GREEN, "size": 22, "font": HEAD})],
    "• Synthetic data: methods transfer, figures do not",
    "• Two years: no validated seasonal model; 6 test months",
    "• Observational: promotion and loyalty effects are associations",
    "• Small churn samples; probabilities are rankings, not calibrated",
    "• No data on competitors, stock-outs or the economy"], size=16, space_after=10)
box(s, 6.75, 1.7, 5.95, 4.9)
text(s, 7.05, 1.9, 5.4, 4.6, [
    [("Next steps", {"bold": True, "color": GREEN, "size": 22, "font": HEAD})],
    "• Seasonal forecast (Holt-Winters or SARIMA) with 3+ years of data",
    "• Randomized promotion and win-back trials",
    "• Basket analysis to design the Mombasa bundles",
    "• Customer lifetime value to prioritize retention spend",
    "• Automated refresh from PostgreSQL to Power BI"], size=16, space_after=10)

# 17. Close
s = prs.slides.add_slide(BLANK)
PAGE[0] += 1
bg(s, GREEN)
text(s, 0.8, 2.0, 11.5, 1.2, "Thank you. Questions?", size=48, font=HEAD, bold=True, color=WHITE)
text(s, 0.8, 3.4, 11.5, 1.6, [
    "Clothing earns the profit, prices drive the growth, and 249 valuable customers are waiting to be won back.",
], size=22, color="DCEBE3")
text(s, 0.8, 5.5, 11.5, 0.9, ["github.com/jonathan-kiplagat/kenyan-retail-customer-sales-intelligence",
                              "Full report, methodology, SQL documentation and model evaluation in the repository"],
     size=16, color=WHITE, space_after=2)
s.notes_slide.notes_text_frame.text = (
    "To close: clothing earns the profit, prices drive the growth, and 249 valuable customers are waiting to be won "
    "back. Everything is reproducible from the repository. Thank you, I'm happy to take questions. "
    "(Prepared answers: milestone_8_documentation/defence_qa.md.)")

prs.core_properties.title = "Customer and Sales Intelligence for a Kenyan Retailer"
prs.core_properties.author = "Jonathan Kiplagat"
OUT.parent.mkdir(exist_ok=True)
prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
