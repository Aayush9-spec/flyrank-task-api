
import json
import logging
import os
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

from openai import APIStatusError, APITimeoutError

from src.triage.job_store import (
    claim_job,
    complete_job,
    fail_job,
    recover_stale_jobs,
    retry_job,
)
from src.triage.service import process_triage


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("triage-worker")

POLL_INTERVAL = float(os.getenv("WORKER_POLL_INTERVAL", "2"))
LEASE_SECONDS = int(os.getenv("WORKER_LEASE_SECONDS", "120"))


def is_retryable(error: Exception) -> bool:
    """Identify temporary provider failures."""

    if isinstance(error, APITimeoutError):
        return True

    if isinstance(error, APIStatusError):
        return error.status_code == 429 or error.status_code >= 500

    return False


def send_failure_alert(job_id: str, error: str, attempts: int):
    """Log a failure alert and optionally notify a webhook."""

    message = {
        "event": "triage_job_failed",
        "job_id": str(job_id),
        "attempts": attempts,
        "error": error[:1000],
    }

    logger.error("TRIAGE FAILURE ALERT: %s", json.dumps(message))

    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if not webhook_url:
        return

    request = Request(
        webhook_url,
        data=json.dumps(message).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=5) as response:
            logger.info("Failure webhook delivered: HTTP %s", response.status)
    except (URLError, TimeoutError, ValueError) as webhook_error:
        logger.error("Failure webhook delivery failed: %s", webhook_error)


def process_one_job():
    """Claim and process one job. Returns True if a job was found."""

    job = claim_job()

    if job is None:
        return False

    job_id = str(job["id"])
    attempts = job["attempts"]
    max_attempts = job["max_attempts"]

    logger.info(
        "Processing job %s (attempt %s/%s)",
        job_id,
        attempts,
        max_attempts,
    )

    try:
        result = process_triage(job["input_text"])

        complete_job(
            job_id,
            result.model_dump(mode="json"),
        )

        logger.info("Job %s completed successfully", job_id)

    except Exception as error:
        error_message = f"{type(error).__name__}: {error}"[:1000]

        if is_retryable(error) and attempts < max_attempts:
            delay = min(2 ** attempts, 60)

            retry_job(
                job_id,
                error_message,
                delay,
            )

            logger.warning(
                "Job %s will retry in %s seconds",
                job_id,
                delay,
            )

        else:
            fail_job(job_id, error_message)
            send_failure_alert(job_id, error_message, attempts)

    return True


def run_worker():
    """Continuously poll PostgreSQL for available jobs."""

    logger.info("Triage worker started")

    while True:
        try:
            recovery = recover_stale_jobs(LEASE_SECONDS)

            if recovery["requeued"]:
                logger.warning(
                    "Recovered stale jobs: %s",
                    recovery["requeued"],
                )

            for job_id in recovery["failed"]:
                send_failure_alert(
                    job_id,
                    "Worker lease expired; maximum attempts reached.",
                    0,
                )

            found_job = process_one_job()

            if not found_job:
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Triage worker shutting down")
            break

        except Exception:
            logger.exception("Unexpected worker error")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_worker()
