# The Polite Scraper — BE-05

A Python scraper that collects book information from the first three catalogue pages of Books to Scrape, extracts product details, normalizes prices, validates records, and saves clean JSON output.

## 1. Target classification

- **Target:** https://books.toscrape.com/
- **Classification:** Scraping practice sandbox.
- **Why:** Books to Scrape is a fictional bookstore provided for learning and testing web scraping.
- **Scope:** First three catalogue pages only.
- **Expected collection:** 60 books (20 per page).

### Robots.txt check

Requested https://books.toscrape.com/robots.txt once. The server returned **HTTP 404**; no robots.txt file was found. A missing robots.txt file is not permission to ignore applicable rules or terms.

## 2. Technology stack

- Python 3.10+
- Requests — HTTP requests
- Beautiful Soup 4 — HTML parsing
- Pydantic 2 — schema validation
- Built-in JSON module — input and output

Dependencies are pinned in `requirements.txt`.

## 3. Project structure

- `src/main.py` — catalogue extraction
- `src/details.py` — product detail extraction and run reporting
- `src/validate.py` — normalization and validation
- `output/catalogue.json` — catalogue entries
- `output/raw-books.json` — extracted raw details
- `output/books.json` — validated records
- `output/errors.json` — invalid records
- `output/run-report.json` — execution report
- `output/failure-test-report.json` — failure-handling test evidence
- `cache/` — locally cached HTML; excluded from Git
- `requirements.txt` — dependencies

## 4. Installation

Run from the repository root:

1. `python -m venv venv`
2. macOS/Linux: `source venv/bin/activate`
3. `python -m pip install -r scraper/requirements.txt`

## 5. Run the scraper

Run these commands from the repository root, in order:

1. `python scraper/src/main.py` — collects titles and unique product URLs from the first three catalogue pages, following each page's Next link.
2. `python scraper/src/details.py` — extracts product details, uses cached pages when available, runs validation, and writes the run report.
3. `python scraper/src/validate.py` — independently reruns normalization and validation.

## 6. Data collected

Each raw book record contains:

| Field | Description |
|---|---|
| `title` | Book title |
| `product_url` | Absolute product-page URL |
| `price_text` | Original displayed price |
| `availability_text` | Availability information |
| `rating_text` | Rating from One to Five |
| `description` | Description, or null |
| `source_page` | Catalogue page number |
| `fetched_at` | UTC timestamp |

### Price normalization

The original price is preserved in `price_text`. The validator converts it into numeric `price_gbp`.

Example: `£51.77` becomes `51.77`.

## 7. Validation and output

Pydantic validates required fields, non-empty titles, absolute HTTPS URLs, positive numeric prices, valid ratings, availability, source-page information, and timestamps. Unexpected extra fields are rejected.

Invalid records are written to `output/errors.json` with their validation reason. Valid normalized records are written to `output/books.json`.

## 8. Politeness and reliability

- Identifiable User-Agent containing the project and repository.
- 10-second HTTP timeout.
- At least 0.5 seconds between live requests.
- Local HTML caching to avoid unnecessary repeated requests.
- Pagination follows the site's own Next links.
- Product URLs are normalized to absolute URLs and deduplicated.
- Timeouts and HTTP 5xx responses are retried once.
- HTTP 403 and 404 responses are not retried.
- Individual product-page failures are recorded without stopping the remaining collection.
- Cached HTML is excluded from Git.

## 9. Execution evidence

Final cache-verification run on 19 November 2026:

`output/run-report.json` recorded:

- Catalogue books: 60
- Pages fetched live: 0
- Request attempts: 0
- Cache hits: 60
- Valid records: 60
- Invalid records: 0
- Failed pages: 0

Zero live requests means all 60 product pages were served from the existing local cache during this verification run.

### Failure-isolation test

A deliberately unavailable product URL was tested. The test retained 60 valid records, recorded one failed page, handled HTTP 404 without retry, and continued processing. The original 60-book catalogue was restored afterwards. See `output/failure-test-report.json`.

## 10. Why no browser automation?

The required catalogue and product information is available in server-rendered HTML. Requests and Beautiful Soup can retrieve and parse it directly, so browser automation is unnecessary for this assignment.

## 11. Ethical scraping policy

- Prefer an official API when one is available and appropriate.
- Check the target site's rules and terms before scraping.
- Never bypass authentication, paywalls, rate limits, or access restrictions.
- Collect only the information needed.
- Use identifiable requests, reasonable delays, and caching.
- Do not assume a missing robots.txt file grants permission.

I will not reuse this code on another site without checking its rules and terms first.

## 12. Limitations

- Only the first three catalogue pages are processed.
- The scraper is designed for the Books to Scrape HTML structure.
- Changes to the site's HTML may require parser updates.
- Cached pages may become outdated.
- This is an educational scraping exercise, not a general-purpose crawler.
