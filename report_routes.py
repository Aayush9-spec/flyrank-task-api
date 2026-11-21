import sqlite3
import subprocess
import sys
import uuid
import shutil

from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/reports", tags=["PDF Reports"])

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "pdf-report-generator"
DB_PATH = REPORT_DIR / "report.db"
SCRIPT_PATH = REPORT_DIR / "generate_report.py"
OUTPUT_PATH = REPORT_DIR / "output" / "bookstore_report.pdf"
ARTIFACT_DIR = REPORT_DIR / "artifacts"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_report_registry():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS generated_reports (
                report_id TEXT PRIMARY KEY,
                generated_at TEXT NOT NULL,
                report_date TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL
            )
        """)


def serialize_report(row):
    return {
        "report_id": row["report_id"],
        "generated_at": row["generated_at"],
        "report_date": row["report_date"],
        "file_size": row["file_size"],
        "download_url": f"/reports/{row['report_id']}/download"
    }


@router.post("/generate")
def generate_report(force: bool = False):
    initialize_report_registry()
    today = date.today().isoformat()

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT * FROM generated_reports
            WHERE report_date = ?
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            (today,)
        ).fetchone()

    if existing and not force:
        return {
            "message": "A report has already been generated today.",
            "generated": False,
            "report": serialize_report(existing)
        }

    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {exc.stderr[-1000:]}"
        )

    if not OUTPUT_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="PDF generator did not create the expected file."
        )

    report_id = uuid.uuid4().hex
    generated_at = datetime.now().astimezone().isoformat()
    report_date = date.today().isoformat()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACT_DIR / f"{report_id}.pdf"
    shutil.copy2(OUTPUT_PATH, artifact_path)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO generated_reports
            (report_id, generated_at, report_date, file_path, file_size)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                report_id,
                generated_at,
                report_date,
                str(artifact_path),
                artifact_path.stat().st_size
            )
        )
        row = connection.execute(
            "SELECT * FROM generated_reports WHERE report_id = ?",
            (report_id,)
        ).fetchone()

    return {
        "message": "PDF report generated successfully.",
        "generated": True,
        "report": serialize_report(row)
    }


@router.get("/latest")
def get_latest_report():
    initialize_report_registry()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM generated_reports
            ORDER BY generated_at DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No report generated yet.")

    return serialize_report(row)


@router.get("/{report_id}/download")
def download_report(report_id: str):
    initialize_report_registry()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM generated_reports WHERE report_id = ?",
            (report_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    file_path = Path(row["file_path"])

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename="bookstore_report.pdf"
    )
