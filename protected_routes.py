from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from supabase_client import supabase


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

    try:
        # Verify the JWT with Supabase Auth.
        response = supabase.auth.get_user(token)
        user = response.user

        if user is None:
            raise ValueError("No user returned by Supabase")

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or expired token"}
        )

    created_at = user.created_at

    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    return {
        "user_id": user.id,
        "email": user.email,
        "created_at": created_at
    }
