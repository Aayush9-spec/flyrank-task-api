# The Polite Scraper — BE-05

## Target classification

- **Target:** https://books.toscrape.com/
- **Classification:** Scraping practice sandbox.
- **Why this target:** The official toscrape.com website describes Books to Scrape as a fictional bookstore intended for learning and testing web scraping.
- **Scope:** Only the first three catalogue pages, targeting 60 books.
- **Robots.txt check:** Requested https://books.toscrape.com/robots.txt. The server returned HTTP 404 — no robots file found.

A missing robots.txt file is not permission to ignore applicable rules or terms.

## Planned data collection

The scraper will collect book information from the first three catalogue pages and their product detail pages. It will normalize and validate the collected records before saving valid JSON output.

## Scraping policy

I will not reuse this code on another site without checking its rules and terms first.
