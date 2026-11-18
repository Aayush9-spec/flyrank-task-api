from fastapi import APIRouter, Depends

from auth_dependency import AuthContext, get_current_auth


router = APIRouter(tags=["Access Control"])


@router.get("/public/info")
def public_info():
    return {
        "message": "This is a public endpoint",
        "access": "public"
    }


@router.get("/protected/profile")
def protected_profile(
    auth: AuthContext = Depends(get_current_auth)
):
    user = auth.user
    created_at = user.created_at

    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    return {
        "user_id": user.id,
        "email": user.email,
        "created_at": created_at
    }


@router.get("/protected/dashboard")
def protected_dashboard(
    auth: AuthContext = Depends(get_current_auth)
):
    return {
        "message": "Welcome to the protected dashboard",
        "user_id": auth.user.id,
        "email": auth.user.email
    }
