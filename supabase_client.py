import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be configured in .env"
    )

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


from urllib.request import Request, urlopen


def check_supabase_connection():
    request = Request(
        f"{SUPABASE_URL.rstrip('/')}/auth/v1/settings",
        headers={"apikey": SUPABASE_KEY},
        method="GET"
    )

    try:
        with urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Supabase returned HTTP {response.status}"
                )
    except Exception as exc:
        raise RuntimeError(
            "Supabase Auth connection failed. Check environment configuration."
        ) from exc