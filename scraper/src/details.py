"""Extract and cache details for books in the catalogue."""

import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
CATALOGUE_FILE = BASE_DIR / "output" / "catalogue.json"
OUTPUT_FILE = BASE_DIR / "output" / "raw-books.json"
CACHE_DIR = BASE_DIR / "cache" / "products"

TIMEOUT = 10
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": (
        "AayushKumarSingh-FlyRankInternship-BE05/1.0 "
        "(+https://github.com/Aayush9-spec/flyrank-task-api)"
    )
}


def extract_details(soup, book, source_page, fetched_at):
    product = soup.select_one(".product_main")

    if product is None:
        raise ValueError("Product details section not found")

    title_element = product.select_one("h1")
    price_element = product.select_one(".price_color")
    availability_element = product.select_one(".availability")
    rating_element = product.select_one(".star-rating")

    if not all((title_element, price_element, availability_element, rating_element)):
        raise ValueError("One or more required product fields are missing")

    description_element = soup.select_one("#product_description + p")

    rating_classes = rating_element.get("class", [])
    rating_text = next(
        (item for item in rating_classes if item != "star-rating"),
        None,
    )

    return {
        "title": title_element.get_text(strip=True),
        "product_url": book["product_url"],
        "price_text": price_element.get_text(strip=True),
        "availability_text": availability_element.get_text(" ", strip=True),
        "rating_text": rating_text,
        "description": (
            description_element.get_text(" ", strip=True)
            if description_element
            else None
        ),
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    books = json.loads(CATALOGUE_FILE.read_text(encoding="utf-8"))
    records = []
    live_requests = 0

    for index, book in enumerate(books, start=1):
        product_url = book["product_url"]
        cache_key = hashlib.sha256(product_url.encode("utf-8")).hexdigest()
        html_file = CACHE_DIR / f"{cache_key}.html"
        timestamp_file = CACHE_DIR / f"{cache_key}.txt"

        if html_file.exists() and timestamp_file.exists():
            html = html_file.read_bytes()
            fetched_at = timestamp_file.read_text(encoding="utf-8").strip()
            print(f"[{index}/{len(books)}] CACHE HIT: {book['title']}")
        else:
            if live_requests:
                time.sleep(REQUEST_DELAY)

            print(f"[{index}/{len(books)}] FETCH: {book['title']}")
            response = requests.get(
                product_url,
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            response.raise_for_status()

            html = response.content
            fetched_at = datetime.now(timezone.utc).isoformat()

            html_file.write_bytes(html)
            timestamp_file.write_text(fetched_at, encoding="utf-8")
            live_requests += 1

        soup = BeautifulSoup(html, "html.parser")
        record = extract_details(
            soup,
            book,
            source_page=(
                f"catalogue/page-{(index - 1) // 20 + 1}.html"
            ),
            fetched_at=fetched_at,
        )
        records.append(record)

    OUTPUT_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nProduct detail extraction complete")
    print(f"Books processed: {len(records)}")
    print(f"Live requests: {live_requests}")
    print(f"Output: {OUTPUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
