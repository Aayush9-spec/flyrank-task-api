from dataclasses import dataclass
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from supabase_client import SUPABASE_URL, SUPABASE_KEY


bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class AuthContext:
    user: Any
    access_token: str
    auth_client: Client


def get_current_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> AuthContext:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
    ):
        raise AuthenticationError("Access token required")

    token = credentials.credentials
    auth_client = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        response = auth_client.auth.get_user(token)
        user = response.user

        if user is None:
            raise ValueError("No user returned by Supabase")

    except Exception as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    return AuthContext(
        user=user,
        access_token=token,
        auth_client=auth_client
    )
