
import json
import logging
import os
import random
import re
import time
import uuid

from fastapi import Header

from src.triage.job_store import create_job, get_job, IdempotencyConflict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import APIStatusError, APITimeoutError, OpenAI
from pydantic import BaseModel, Field, ValidationError


load_dotenv()

router = APIRouter()
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

ROOT_DIR = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT_DIR / "prompts" / "triage-v2.md"
QUARANTINE_PATH = ROOT_DIR / "logs" / "quarantine.jsonl"
PROMPT_VERSION = "triage-v2"

RETRY_DELAYS = (1, 2, 4)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    feature = "feature"
    other = "other"


class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class TriageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TriageResponse(BaseModel):
    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


def extract_json(text: str) -> str:
    """Extract a JSON object from plain text or a Markdown code fence."""
    cleaned = text.strip()
    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response.")

    return cleaned[start:end + 1]


def parse_and_validate(raw_output: str) -> TriageResponse:
    """Parse model output and validate it against the response schema."""
    parsed = json.loads(extract_json(raw_output))
    return TriageResponse.model_validate(parsed)


def quarantine(ticket_text: str, raw_output: str, error: str) -> None:
    """Store failed model output for later inspection."""
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": ticket_text,
        "raw_output": raw_output,
        "error": error,
    }

    with QUARANTINE_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_retry_after(exc: APIStatusError):
    """Read Retry-After as seconds or an HTTP date."""
    headers = getattr(exc.response, "headers", {}) or {}
    value = headers.get("retry-after")

    if not value:
        return None

    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            retry_date = parsedate_to_datetime(value)
            if retry_date.tzinfo is None:
                retry_date = retry_date.replace(tzinfo=timezone.utc)
            return max(
                0.0,
                (retry_date - datetime.now(timezone.utc)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None


def call_model_with_retry(client, model, messages, temperature):
    """Retry only timeouts, HTTP 429, and HTTP 5xx responses."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )

        except (APITimeoutError, APIStatusError) as exc:
            if isinstance(exc, APIStatusError):
                status_code = exc.status_code
                retryable = status_code == 429 or 500 <= status_code <= 599

                if not retryable:
                    raise

                retry_after = get_retry_after(exc)
            else:
                retry_after = None

            if attempt >= len(RETRY_DELAYS):
                raise

            delay = RETRY_DELAYS[attempt] * random.uniform(0.5, 1.5)

            if retry_after is not None:
                delay = max(delay, retry_after)

            logger.warning(
                json.dumps({
                    "event": "llm_retry",
                    "attempt": attempt + 1,
                    "next_delay_seconds": round(delay, 2),
                    "error_type": type(exc).__name__,
                })
            )

            time.sleep(delay)

    raise RuntimeError("AI retry attempts exhausted.")


def add_usage(response, metrics):
    """Accumulate token usage when the provider supplies it."""
    usage = getattr(response, "usage", None)

    if usage:
        metrics["input_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
        metrics["output_tokens"] += getattr(usage, "completion_tokens", 0) or 0


def log_call(model, metrics, start_time, status):
    """Write one structured log record for each triage request."""
    record = {
        "event": "triage_call",
        "status": status,
        "prompt_version": PROMPT_VERSION,
        "model": model or "not_configured",
        "input_tokens": metrics["input_tokens"],
        "output_tokens": metrics["output_tokens"],
        "duration_ms": round((time.monotonic() - start_time) * 1000, 2),
        "repair_count": metrics["repair_count"],
    }

    logger.info(json.dumps(record))


@router.post("/triage", response_model=TriageResponse)
def triage_ticket(payload: TriageRequest):
    start_time = time.monotonic()
    model = os.getenv("LLM_MODEL")
    metrics = {
        "input_tokens": 0,
        "output_tokens": 0,
        "repair_count": 0,
    }
    status = "success"

    try:
        if os.getenv("LLM_ENABLED", "true").lower() == "false":
            return TriageResponse(
                category=Category.other,
                urgency=Urgency.normal,
                confidence=0.0,
                reason="AI triage is disabled; manual review is required.",
            )

        if os.getenv("LLM_STUB") == "1":
            return TriageResponse(
                category=Category.other,
                urgency=Urgency.normal,
                confidence=0.75,
                reason="Stub response for endpoint validation.",
            )

        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")

        if not all([base_url, api_key, model]):
            raise HTTPException(
                status_code=503,
                detail="AI provider configuration is incomplete.",
            )

        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=30.0,
            max_retries=0,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload.text},
        ]

        response = call_model_with_retry(
            client, model, messages, temperature=0.1
        )
        add_usage(response, metrics)

        raw_output = response.choices[0].message.content or ""

        try:
            return parse_and_validate(raw_output)

        except (ValueError, json.JSONDecodeError, ValidationError) as first_error:
            metrics["repair_count"] = 1
            validation_error = str(first_error)

            repair_messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Your previous response was invalid.\n"
                        "Return exactly one corrected JSON object matching "
                        "the required schema. Do not add explanations.\n\n"
                        f"Original ticket:\n{payload.text}\n\n"
                        f"Invalid response:\n{raw_output}\n\n"
                        f"Validation error:\n{validation_error}"
                    ),
                },
            ]

            repair_response = call_model_with_retry(
                client, model, repair_messages, temperature=0.0
            )
            add_usage(repair_response, metrics)

            repaired_output = (
                repair_response.choices[0].message.content or ""
            )

            try:
                return parse_and_validate(repaired_output)

            except (ValueError, json.JSONDecodeError, ValidationError) as second_error:
                quarantine(
                    ticket_text=payload.text,
                    raw_output=(
                        "FIRST RESPONSE:\n"
                        f"{raw_output}\n\n"
                        "REPAIR RESPONSE:\n"
                        f"{repaired_output}"
                    ),
                    error=str(second_error),
                )

                raise HTTPException(
                    status_code=422,
                    detail="The AI could not produce a valid triage response.",
                ) from second_error

    except HTTPException:
        status = "error"
        raise

    except Exception as exc:
        status = "error"
        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed.",
        ) from exc

    finally:
        log_call(model, metrics, start_time, status)



@router.post("/triage/jobs", status_code=202)
def submit_triage_job(
    payload: TriageRequest,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    """Submit a ticket for asynchronous triage."""

    key = idempotency_key or str(uuid.uuid4())
    key = key.strip()

    if not key or len(key) > 255:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key must contain 1 to 255 characters.",
        )

    try:
        job = create_job(payload.text, key)
    except IdempotencyConflict as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    job_id = str(job["id"])

    return {
        "job_id": job_id,
        "status": job["status"],
        "status_url": f"/triage/jobs/{job_id}",
    }


@router.get("/triage/jobs/{job_id}")
def get_triage_job(job_id: uuid.UUID):
    """Retrieve asynchronous triage job status and result."""

    job = get_job(str(job_id))

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Triage job not found.",
        )

    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "result": job["result"],
        "error": job["error"],
        "attempts": job["attempts"],
        "max_attempts": job["max_attempts"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "completed_at": job["completed_at"],
    }
