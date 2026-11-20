import os
from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


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

    from fastapi import HTTPException

    raise HTTPException(
        status_code=503,
        detail="AI triage is not enabled yet."
    )
