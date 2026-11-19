"""Fetch and cache the first Books to Scrape catalogue page."""

from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = BASE_DIR / "cache" / "catalogue-page-1.html"

TARGET_URL = "https://books.toscrape.com/"
TIMEOUT = 10

HEADERS = {
    "User-Agent": (
        "AayushKumarSingh-FlyRankInternship-BE05/1.0 "
        "(+https://github.com/Aayush9-spec/flyrank-task-api)"
    )
}


def main():
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")
        print("CACHE HIT")
        print(f"Response size: {CACHE_FILE.stat().st_size} bytes")
        return

    print("Fetching first catalogue page...")

    response = requests.get(
        TARGET_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP {response.status_code}"
        )

    html = response.text
    CACHE_FILE.write_text(html, encoding="utf-8")

    print("FETCH")
    print(f"HTTP status: {response.status_code}")
    print(f"Response size: {len(response.content)} bytes")
    print(f"Saved to: {CACHE_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
