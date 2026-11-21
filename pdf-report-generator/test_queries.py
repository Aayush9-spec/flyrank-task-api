import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "report.db"
SQL = (BASE / "queries.sql").read_text(encoding="utf-8")

# Remove SQL comment lines
clean_sql = "\n".join(
    line for line in SQL.splitlines()
    if not line.strip().startswith("--")
)

queries = [q.strip() for q in clean_sql.split(";") if q.strip()]

with sqlite3.connect(DB) as conn:
    for index, query in enumerate(queries, start=1):
        print(f"\n--- Query {index} ---")
        cursor = conn.execute(query)
        print([column[0] for column in cursor.description])
        for row in cursor.fetchall():
            print(row)
