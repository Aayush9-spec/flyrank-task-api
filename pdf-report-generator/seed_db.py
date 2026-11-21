import json
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR.parent / "scraper" / "output" / "books.json"
DB_FILE = BASE_DIR / "report.db"

RATINGS = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}

def main():
    books = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                price REAL NOT NULL CHECK(price >= 0),
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                url TEXT NOT NULL
            )
        """)

        rows = []
        for book in books:
            url = book["product_url"]
            match = re.search(r"\]\((https?://[^)]+)\)", url)
            if match:
                url = match.group(1)

            rows.append((
                book["title"],
                float(book["price_gbp"]),
                RATINGS[book["rating_text"]],
                url,
            ))

        conn.executemany("""
            INSERT INTO books (title, price, rating, url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                price = excluded.price,
                rating = excluded.rating,
                url = excluded.url
        """, rows)

        total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        print(f"Database: {DB_FILE}")
        print(f"Source records: {len(books)}")
        print(f"Books stored: {total}")
        print("Rating counts:")
        for rating, count in conn.execute(
            "SELECT rating, COUNT(*) FROM books GROUP BY rating ORDER BY rating"
        ):
            print(f"  {rating} star(s): {count}")

if __name__ == "__main__":
    main()
