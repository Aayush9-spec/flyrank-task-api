"""Extract product details while handling individual page failures."""

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

CATALOGUE_FILE = BASE_DIR / "output" / "catalogue.json"
OUTPUT_FILE = BASE_DIR / "output" / "raw-books.json"
REPORT_FILE = BASE_DIR / "output" / "run-report.json"
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

    title = product.select_one("h1")
    price = product.select_one(".price_color")
    availability = product.select_one(".availability")
    rating = product.select_one(".star-rating")

    if not all((title, price, availability, rating)):
        raise ValueError("One or more required product fields are missing")

    description = soup.select_one("#product_description + p")
    rating_classes = rating.get("class", [])
    rating_text = next(
        (item for item in rating_classes if item != "star-rating"),
        None,
    )

    return {
        "title": title.get_text(strip=True),
        "product_url": book["product_url"],
        "price_text": price.get_text(strip=True),
        "availability_text": availability.get_text(" ", strip=True),
        "rating_text": rating_text,
        "description": (
            description.get_text(" ", strip=True) if description else None
        ),
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def fetch_product(url, previous_live_request, stats):
    """Fetch a page, retrying once only for timeouts and HTTP 5xx."""
    for attempt in range(2):
        if previous_live_request or attempt > 0:
            time.sleep(REQUEST_DELAY)

        try:
            stats["request_attempts"] += 1
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
            )

            if 500 <= response.status_code <= 599:
                if attempt == 0:
                    print(f"HTTP {response.status_code}; retrying once...")
                    continue

                response.raise_for_status()

            response.raise_for_status()
            return response.content

        except requests.exceptions.Timeout:
            if attempt == 0:
                print("Request timed out; retrying once...")
                continue
            raise

    raise RuntimeError("Request failed after retry")


def main():
    start_time = datetime.now(timezone.utc)
    start_clock = time.monotonic()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    books = json.loads(CATALOGUE_FILE.read_text(encoding="utf-8"))

    records = []
    failed_pages = []
    cache_hits = 0
    pages_fetched = 0
    request_attempts = 0
    previous_live_request = False

    for index, book in enumerate(books, start=1):
        product_url = book["product_url"]
        cache_key = hashlib.sha256(
            product_url.encode("utf-8")
        ).hexdigest()

        html_file = CACHE_DIR / f"{cache_key}.html"
        timestamp_file = CACHE_DIR / f"{cache_key}.txt"

        try:
            if html_file.exists() and timestamp_file.exists():
                html = html_file.read_bytes()
                fetched_at = timestamp_file.read_text(
                    encoding="utf-8"
                ).strip()
                cache_hits += 1
                print(f"[{index}/{len(books)}] CACHE HIT: {book['title']}")

            else:
                print(f"[{index}/{len(books)}] FETCH: {book['title']}")

                previous_live_request = True
                stats = {"request_attempts": request_attempts}
                html = fetch_product(
                    product_url,
                    previous_live_request,
                    stats,
                )
                request_attempts = stats["request_attempts"]
                pages_fetched += 1

                fetched_at = datetime.now(timezone.utc).isoformat()

                html_file.write_bytes(html)
                timestamp_file.write_text(
                    fetched_at,
                    encoding="utf-8",
                )

            soup = BeautifulSoup(html, "html.parser")

            record = extract_details(
                soup,
                book,
                source_page=f"catalogue/page-{(index - 1) // 20 + 1}.html",
                fetched_at=fetched_at,
            )
            records.append(record)

        except Exception as exc:
            if "stats" in locals():
                request_attempts = stats["request_attempts"]

            failure = {
                "title": book.get("title"),
                "product_url": product_url,
                "reason": f"{type(exc).__name__}: {exc}",
            }
            failed_pages.append(failure)
            print(f"[{index}/{len(books)}] FAILED: {failure['reason']}")
            continue

    OUTPUT_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Validate successful extractions and create books.json/errors.json.
    validator = SRC_DIR / "validate.py"
    subprocess.run(
        [sys.executable, str(validator)],
        check=True,
    )

    errors_file = BASE_DIR / "output" / "errors.json"
    validation_errors = json.loads(
        errors_file.read_text(encoding="utf-8")
    )

    report = {
        "started_at": start_time.isoformat(),
        "duration_seconds": round(time.monotonic() - start_clock, 2),
        "catalogue_books": len(books),
        "pages_fetched": pages_fetched,
        "request_attempts": request_attempts,
        "cache_hits": cache_hits,
        "valid_records": len(records) - len(validation_errors),
        "invalid_records": len(validation_errors) + len(failed_pages),
        "failed_pages": failed_pages,
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nScraper run complete")
    print(f"Pages fetched: {pages_fetched}")
    print(f"Cache hits: {cache_hits}")
    print(f"Valid records: {report['valid_records']}")
    print(f"Invalid records: {report['invalid_records']}")
    print(f"Failed pages: {len(failed_pages)}")
    print(f"Report: {REPORT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
