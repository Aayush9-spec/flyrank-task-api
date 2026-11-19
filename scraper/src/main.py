"""Collect book titles and product URLs from the first three catalogue pages."""

import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_FILE = BASE_DIR / "output" / "catalogue.json"

START_URL = "https://books.toscrape.com/"
TIMEOUT = 10
PAGE_LIMIT = 3
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": (
        "AayushKumarSingh-FlyRankInternship-BE05/1.0 "
        "(+https://github.com/Aayush9-spec/flyrank-task-api)"
    )
}


def get_page(url, page_number, previous_live_request):
    cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

    if cache_file.exists():
        print(f"Page {page_number}: CACHE HIT")
        return cache_file.read_bytes(), False

    if previous_live_request:
        time.sleep(REQUEST_DELAY)

    print(f"Page {page_number}: FETCH {url}")
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(
            f"Page {page_number} failed: HTTP {response.status_code}"
        )

    cache_file.write_bytes(response.content)
    print(f"Page {page_number}: saved to {cache_file.name}")

    return response.content, True


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    page_url = START_URL
    books_by_url = {}
    live_request_made = False

    for page_number in range(1, PAGE_LIMIT + 1):
        html, was_fetched = get_page(
            page_url,
            page_number,
            live_request_made,
        )

        if was_fetched:
            live_request_made = True

        soup = BeautifulSoup(html, "html.parser")
        book_cards = soup.select("article.product_pod")

        print(f"Page {page_number}: {len(book_cards)} books found")

        for card in book_cards:
            link = card.select_one("h3 a")

            if link is None:
                continue

            title = link.get("title") or link.get_text(strip=True)
            product_url = urljoin(page_url, link.get("href", ""))

            if title and product_url:
                books_by_url[product_url] = {
                    "title": title,
                    "product_url": product_url,
                }

        if page_number < PAGE_LIMIT:
            next_link = soup.select_one("li.next a")

            if next_link is None:
                raise RuntimeError(
                    f"Next link missing on catalogue page {page_number}"
                )

            page_url = urljoin(page_url, next_link.get("href"))

    records = list(books_by_url.values())

    OUTPUT_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nCatalogue extraction complete")
    print(f"Catalogue pages processed: {PAGE_LIMIT}")
    print(f"Unique books collected: {len(records)}")
    print(f"Output: {OUTPUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
