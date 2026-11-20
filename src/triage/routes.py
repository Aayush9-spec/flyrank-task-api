import json
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError


load_dotenv()

router = APIRouter()

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "triage-v1.md"


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


@router.post("/triage", response_model=TriageResponse)
def triage_ticket(payload: TriageRequest):
    if os.getenv("LLM_STUB") == "1":
        return TriageResponse(
            category=Category.other,
            urgency=Urgency.normal,
            confidence=0.75,
            reason="Stub response for endpoint validation."
        )

    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not all([base_url, api_key, model]):
        raise HTTPException(
            status_code=503,
            detail="AI provider configuration is incomplete."
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

        content = response.choices[0].message.content

        if not content:
            raise ValueError("The AI provider returned an empty response.")

        result = json.loads(content)
        return TriageResponse.model_validate(result)

    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI provider returned an invalid triage response."
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed."
        ) from exc