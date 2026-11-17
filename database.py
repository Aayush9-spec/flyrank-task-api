
import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)


def get_all_tasks():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, done FROM tasks ORDER BY id"
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "done": row["done"]
            }
            for row in rows
        ]


def get_task_by_id(task_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = %s",
            (task_id,)
        ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "title": row["title"],
            "done": row["done"]
        }


def create_task(title: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO tasks (title, done)
            VALUES (%s, FALSE)
            RETURNING id, title, done
            """,
            (title,)
        ).fetchone()

        return {
            "id": row["id"],
            "title": row["title"],
            "done": row["done"]
        }


def update_task(task_id: int, updates: dict):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = %s",
            (task_id,)
        ).fetchone()

        if row is None:
            return None

        new_title = updates.get("title", row["title"])
        new_done = updates.get("done", row["done"])

        updated = conn.execute(
            """
            UPDATE tasks
            SET title = %s, done = %s
            WHERE id = %s
            RETURNING id, title, done
            """,
            (new_title, new_done, task_id)
        ).fetchone()

        return {
            "id": updated["id"],
            "title": updated["title"],
            "done": updated["done"]
        }


def delete_task(task_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = %s",
            (task_id,)
        )

        return cursor.rowcount > 0
