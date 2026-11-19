"""Normalize and validate scraped book records."""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "output" / "raw-books.json"
OUTPUT_FILE = BASE_DIR / "output" / "books.json"
ERROR_FILE = BASE_DIR / "output" / "errors.json"


class BookRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    product_url: str
    price_text: str
    price_gbp: float = Field(gt=0)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(pattern=r"^(One|Two|Three|Four|Five)$")
    description: str | None = None
    source_page: str = Field(min_length=1)
    fetched_at: datetime

    @field_validator("product_url")
    @classmethod
    def validate_product_url(cls, value):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Product URL must be an absolute HTTPS URL")
        return value


def normalize_price(price_text):
    match = re.fullmatch(r"\s*£\s*(\d+(?:\.\d{1,2})?)\s*", price_text)
    if not match:
        raise ValueError(f"Invalid GBP price: {price_text!r}")
    return float(match.group(1))


def main():
    raw_records = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    valid_records = []
    invalid_records = []

    for index, raw in enumerate(raw_records, start=1):
        try:
            normalized = {
                **raw,
                "price_gbp": normalize_price(raw["price_text"]),
            }
            book = BookRecord.model_validate(normalized)
            valid_records.append(
                book.model_dump(mode="json")
            )
        except Exception as exc:
            invalid_records.append({
                "record_number": index,
                "title": raw.get("title"),
                "product_url": raw.get("product_url"),
                "reason": str(exc),
            })

    OUTPUT_FILE.write_text(
        json.dumps(valid_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    ERROR_FILE.write_text(
        json.dumps(invalid_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Normalization and validation complete")
    print(f"Input records: {len(raw_records)}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Invalid records: {len(invalid_records)}")
    print(f"Valid output: {OUTPUT_FILE.relative_to(BASE_DIR)}")
    print(f"Error output: {ERROR_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
