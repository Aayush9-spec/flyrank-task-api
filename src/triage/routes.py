
import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError


load_dotenv()

router = APIRouter()

ROOT_DIR = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT_DIR / "prompts" / "triage-v1.md"
QUARANTINE_PATH = ROOT_DIR / "logs" / "quarantine.jsonl"
PROMPT_VERSION = "triage-v1"


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
    json_text = extract_json(raw_output)
    parsed = json.loads(json_text)
    return TriageResponse.model_validate(parsed)


def quarantine(
    ticket_text: str,
    raw_output: str,
    error: str,
) -> None:
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


def get_validation_error(raw_output: str) -> str:
    """Return a readable parsing or schema-validation error."""
    try:
        parse_and_validate(raw_output)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        return str(exc)

    return "Unknown validation error."


@router.post("/triage", response_model=TriageResponse)
def triage_ticket(payload: TriageRequest):
    if os.getenv("LLM_STUB") == "1":
        return TriageResponse(
            category=Category.other,
            urgency=Urgency.normal,
            confidence=0.75,
            reason="Stub response for endpoint validation.",
        )

    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not all([base_url, api_key, model]):
        raise HTTPException(
            status_code=503,
            detail="AI provider configuration is incomplete.",
        )

    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=30.0,
            max_retries=0,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.text},
            ],
            temperature=0.1,
        )

        raw_output = response.choices[0].message.content or ""

        try:
            return parse_and_validate(raw_output)

        except (ValueError, json.JSONDecodeError, ValidationError) as first_error:
            validation_error = str(first_error)

            repair_response = client.chat.completions.create(
                model=model,
                messages=[
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
                ],
                temperature=0.0,
            )

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
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed.",
        ) from exc
