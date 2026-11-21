import html
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "report.db"
SQL_PATH = BASE_DIR / "queries.sql"
OUTPUT_DIR = BASE_DIR / "output"


def load_queries():
    content = SQL_PATH.read_text(encoding="utf-8")
    content = re.sub(r"(?m)^\s*--.*$", "", content)
    return [query.strip() for query in content.split(";") if query.strip()]


def fetch_report_data():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        results = []

        for query in load_queries():
            cursor = connection.execute(query)
            results.append([dict(row) for row in cursor.fetchall()])

        if len(results) != 4:
            raise ValueError("Expected exactly four SQL report queries.")

        return results


def clean_url(value):
    match = re.search(r"\]\((https?://[^)]+)\)", value or "")
    if match:
        return match.group(1)
    return value or "#"


def money(value):
    return f"£{value:,.2f}"


def build_html(summary, ratings, top_books, price_bands):
    total, average, minimum, maximum, avg_rating = (
        summary[0][key]
        for key in (
            "total_books",
            "average_price",
            "minimum_price",
            "maximum_price",
            "average_rating",
        )
    )

    rating_rows = ""
    for row in ratings:
        rating = int(row["rating"])
        count = int(row["book_count"])
        percentage = float(row["percentage"])
        rating_rows += f"""
        <div class="bar-row">
            <span class="bar-label">{rating} star</span>
            <div class="bar-track">
                <div class="bar-fill" style="width:{percentage}%"></div>
            </div>
            <span class="bar-value">{count} ({percentage:.1f}%)</span>
        </div>
        """

    price_rows = ""
    for row in price_bands:
        price_rows += f"""
        <tr>
            <td>{html.escape(str(row['price_band']))}</td>
            <td>{row['book_count']}</td>
            <td>{money(row['average_price'])}</td>
        </tr>
        """

    book_rows = ""
    for index, book in enumerate(top_books, start=1):
        title = html.escape(str(book["title"]))
        url = html.escape(clean_url(book["url"]), quote=True)
        book_rows += f"""
        <tr>
            <td>{index}</td>
            <td class="book-title">{title}</td>
            <td>{money(book['price'])}</td>
            <td>{book['rating']}/5</td>
            <td><a href="{url}">View book</a></td>
        </tr>
        """

    generated_at = datetime.now().strftime("%d %B %Y, %I:%M %p")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bookstore Analytics Report</title>
<style>
    @page {{
        size: A4;
        margin: 16mm 15mm;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #1e293b;
        font-size: 10pt;
        line-height: 1.45;
        margin: 0;
    }}
    .header {{
        background: #14213d;
        color: white;
        padding: 25px 28px;
        border-radius: 10px;
        margin-bottom: 22px;
    }}
    .eyebrow {{
        color: #a5c8ff;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-size: 8pt;
        font-weight: 700;
    }}
    h1 {{ font-size: 25pt; margin: 7px 0; }}
    .subtitle {{ color: #dbeafe; font-size: 10pt; }}
    h2 {{
        font-size: 15pt;
        margin: 22px 0 12px;
        color: #14213d;
    }}
    .generated {{ color: #64748b; font-size: 8pt; margin-top: 12px; }}
    .kpis {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }}
    .kpi {{
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 13px;
    }}
    .kpi-label {{
        color: #64748b;
        font-size: 8pt;
        text-transform: uppercase;
    }}
    .kpi-value {{
        color: #14213d;
        font-size: 18pt;
        font-weight: 750;
        margin-top: 5px;
    }}
    .section {{
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px 17px;
        margin-bottom: 15px;
    }}
    .bar-row {{
        display: grid;
        grid-template-columns: 55px 1fr 85px;
        gap: 10px;
        align-items: center;
        margin: 10px 0;
        font-size: 9pt;
    }}
    .bar-track {{
        height: 11px;
        background: #e2e8f0;
        border-radius: 20px;
        overflow: hidden;
    }}
    .bar-fill {{
        height: 100%;
        background: #2878d0;
        border-radius: 20px;
    }}
    .bar-value {{ text-align: right; color: #475569; }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 9pt;
    }}
    th {{
        background: #14213d;
        color: white;
        text-align: left;
        padding: 10px 8px;
    }}
    td {{
        padding: 9px 8px;
        border-bottom: 1px solid #e2e8f0;
    }}
    tr:nth-child(even) td {{ background: #f8fafc; }}
    .page-break {{ page-break-before: always; }}
    .book-title {{ width: 48%; }}
    a {{ color: #1769aa; text-decoration: none; }}

    /* Compact layout to keep the summary on one A4 page */
    .header {{ padding: 18px 24px; }}
    h2 {{ margin: 14px 0 8px; }}
    .kpis {{ gap: 7px; margin-bottom: 12px; }}
    .kpi {{ padding: 9px; }}
    .kpi-value {{ font-size: 16pt; margin-top: 3px; }}
    .section {{ padding: 10px 13px; margin-bottom: 10px; }}
    .bar-row {{ margin: 7px 0; }}
    td {{ padding: 7px 8px; }}

    .footer {{
        margin-top: 20px;
        color: #64748b;
        font-size: 8pt;
        border-top: 1px solid #e2e8f0;
        padding-top: 9px;
    }}
</style>
</head>
<body>
    <div class="header">
        <div class="eyebrow">Data Analytics • PDF Report</div>
        <h1>Bookstore Insights</h1>
        <div class="subtitle">Pricing, customer ratings and catalogue overview</div>
        <div class="generated">Generated: {generated_at}</div>
    </div>

    <h2>Executive Summary</h2>
    <div class="kpis">
        <div class="kpi">
            <div class="kpi-label">Total books</div>
            <div class="kpi-value">{total}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Average price</div>
            <div class="kpi-value">{money(average)}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Average rating</div>
            <div class="kpi-value">{avg_rating:.2f}/5</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Lowest price</div>
            <div class="kpi-value">{money(minimum)}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Highest price</div>
            <div class="kpi-value">{money(maximum)}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Five-star books</div>
            <div class="kpi-value">{next((r['book_count'] for r in ratings if r['rating'] == 5), 0)}</div>
        </div>
    </div>

    <h2>Rating Distribution</h2>
    <div class="section">
        {rating_rows}
    </div>

    <h2>Price Band Analysis</h2>
    <div class="section">
        <table>
            <thead>
                <tr>
                    <th>Price range</th>
                    <th>Books</th>
                    <th>Average price</th>
                </tr>
            </thead>
            <tbody>{price_rows}</tbody>
        </table>
    </div>

    <div class="footer">
        Source: Scraped bookstore catalogue dataset • Total records: {total}
    </div>

    <div class="page-break">
        <div class="header">
            <div class="eyebrow">Catalogue Analysis</div>
            <h1>Top 10 Most Expensive Books</h1>
            <div class="subtitle">Ranked by listed price</div>
        </div>
        <div class="section">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Book title</th>
                        <th>Price</th>
                        <th>Rating</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>{book_rows}</tbody>
            </table>
        </div>
        <div class="footer">
            Bookstore Insights • Generated {generated_at}
        </div>
    </div>
</body>
</html>"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary, ratings, top_books, price_bands = fetch_report_data()
    document = build_html(summary, ratings, top_books, price_bands)

    html_path = OUTPUT_DIR / "report.html"
    pdf_path = OUTPUT_DIR / "bookstore_report.pdf"
    html_path.write_text(document, encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(document, wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
        )
        browser.close()

    print(f"HTML report: {html_path}")
    print(f"PDF report:  {pdf_path}")
    print(f"PDF size:    {pdf_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
