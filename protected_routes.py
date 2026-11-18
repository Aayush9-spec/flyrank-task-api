from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse


router = APIRouter(tags=["Access Control"])


def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


@router.get("/public/info")
def public_info():
    return {
        "message": "This is a public endpoint",
        "access": "public"
    }


@router.get("/protected/profile")
def protected_profile(
    authorization: str | None = Header(default=None)
):
    token = parse_bearer_token(authorization)

    if token is None:
        return JSONResponse(
            status_code=401,
            content={"error": "Access token required"}
        )

    # Stage 2 checks token presence only.
    # Supabase JWT verification will be added in Stage 3.
    return {
        "message": "Bearer token provided",
        "token_present": True,
        "verified": False
    }
