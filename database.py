import sqlite3
from pathlib import Path

# Store the database beside this Python file
DB_PATH = Path(__file__).resolve().parent / "tasks.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)

    try:
        # Create the tasks table if it does not exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
        """)

        # Insert sample tasks only when the table is empty
        count = conn.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0]

        if count == 0:
            sample_tasks = [
                ("Learn Python", 1),
                ("Learn FastAPI", 0),
                ("Build CRUD API", 0)
            ]

            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                sample_tasks
            )

        conn.commit()

    finally:
        conn.close()


def get_all_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            "SELECT * FROM tasks"
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "done": bool(row["done"])
            }
            for row in rows
        ]

    finally:
        conn.close()


def get_task_by_id(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"])
        }

    finally:
        conn.close()


def create_task(title: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (title, 0)
        )
        conn.commit()

        task_id = cursor.lastrowid

        return {
            "id": task_id,
            "title": title,
            "done": False
        }
    finally:
        conn.close()
