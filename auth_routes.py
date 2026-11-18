from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client

from supabase_client import SUPABASE_URL, SUPABASE_KEY


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class AuthCredentials(BaseModel):
    email: str
    password: str


def get_auth_client():
    # A separate client prevents one user's session from
    # being shared with another authentication request.
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@router.post("/signup", status_code=201)
def signup(credentials: AuthCredentials):
    email = credentials.email.strip()
    password = credentials.password

    if not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Email and password are required"
        )

    try:
        response = get_auth_client().auth.sign_up({
            "email": email,
            "password": password
        })
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Signup failed. Check the email, password, and Auth settings."
        ) from exc

    if response.user is None:
        raise HTTPException(
            status_code=400,
            detail="Signup failed"
        )

    return {
        "message": "User registered successfully",
        "user": {
            "id": response.user.id,
            "email": response.user.email
        }
    }


@router.post("/login")
def login(credentials: AuthCredentials):
    email = credentials.email.strip()
    password = credentials.password

    if not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Email and password are required"
        )

    try:
        response = get_auth_client().auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        ) from exc

    if response.session is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "token_type": "bearer"
    }
