
import uuid

from psycopg.types.json import Jsonb

from database import get_connection


class IdempotencyConflict(Exception):
    """Raised when a key is reused with different ticket content."""


def create_job(ticket_text: str, idempotency_key: str):
    """Create a job or return the existing job for the same key."""

    job_id = uuid.uuid4()

    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO triage_jobs (id, idempotency_key, input_text)
            VALUES (%s, %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id, status, created_at
            """,
            (job_id, idempotency_key, ticket_text),
        ).fetchone()

        if row:
            return dict(row)

        existing = conn.execute(
            """
            SELECT id, status, created_at, input_text
            FROM triage_jobs
            WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        ).fetchone()

        if existing is None:
            raise RuntimeError("Could not retrieve the existing job.")

        if existing["input_text"] != ticket_text:
            raise IdempotencyConflict(
                "This idempotency key was already used with different ticket content."
            )

        return {
            "id": existing["id"],
            "status": existing["status"],
            "created_at": existing["created_at"],
        }


def get_job(job_id: str):
    """Fetch job status without exposing internal input text."""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                id, status, result, error, attempts,
                max_attempts, created_at, updated_at, completed_at
            FROM triage_jobs
            WHERE id = %s
            """,
            (job_id,),
        ).fetchone()

        return dict(row) if row else None


def claim_job():
    """Atomically claim one available job."""

    with get_connection() as conn:
        row = conn.execute(
            """
            WITH candidate AS (
                SELECT id
                FROM triage_jobs
                WHERE status = 'pending'
                  AND available_at <= NOW()
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE triage_jobs AS job
            SET status = 'processing',
                attempts = job.attempts + 1,
                locked_at = NOW(),
                updated_at = NOW()
            FROM candidate
            WHERE job.id = candidate.id
            RETURNING
                job.id, job.input_text, job.attempts, job.max_attempts
            """
        ).fetchone()

        return dict(row) if row else None


def complete_job(job_id: str, result: dict):
    """Save a successful result."""

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE triage_jobs
            SET status = 'completed',
                result = %s,
                error = NULL,
                locked_at = NULL,
                updated_at = NOW(),
                completed_at = NOW()
            WHERE id = %s
              AND status = 'processing'
            """,
            (Jsonb(result), job_id),
        )


def retry_job(job_id: str, error: str, delay_seconds: int):
    """Schedule another attempt after a temporary failure."""

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE triage_jobs
            SET status = 'pending',
                error = %s,
                available_at = NOW() + (%s * INTERVAL '1 second'),
                locked_at = NULL,
                updated_at = NOW()
            WHERE id = %s
              AND status = 'processing'
            """,
            (error[:1000], delay_seconds, job_id),
        )


def fail_job(job_id: str, error: str):
    """Mark a job as permanently failed."""

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE triage_jobs
            SET status = 'failed',
                error = %s,
                locked_at = NULL,
                updated_at = NOW(),
                completed_at = NOW()
            WHERE id = %s
              AND status = 'processing'
            """,
            (error[:1000], job_id),
        )


def recover_stale_jobs(lease_seconds: int = 120):
    """Recover jobs abandoned by a worker that stopped unexpectedly."""

    with get_connection() as conn:
        requeued = conn.execute(
            """
            UPDATE triage_jobs
            SET status = 'pending',
                locked_at = NULL,
                available_at = NOW(),
                error = 'Worker lease expired; job will be retried.',
                updated_at = NOW()
            WHERE status = 'processing'
              AND locked_at < NOW() - make_interval(secs => %s)
              AND attempts < max_attempts
            RETURNING id
            """,
            (lease_seconds,),
        ).fetchall()

        failed = conn.execute(
            """
            UPDATE triage_jobs
            SET status = 'failed',
                locked_at = NULL,
                error = 'Worker lease expired; maximum attempts reached.',
                updated_at = NOW(),
                completed_at = NOW()
            WHERE status = 'processing'
              AND locked_at < NOW() - make_interval(secs => %s)
              AND attempts >= max_attempts
            RETURNING id
            """,
            (lease_seconds,),
        ).fetchall()

        return {
            "requeued": [str(row["id"]) for row in requeued],
            "failed": [str(row["id"]) for row in failed],
        }
