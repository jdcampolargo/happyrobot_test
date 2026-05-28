import hmac
import os
from typing import Optional

from fastapi import HTTPException, Request, status


def _configured_api_key() -> str:
    return os.getenv("API_KEY", "local-dev-key")


def _extract_bearer(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


async def require_api_key(request: Request) -> str:
    """Accept X-API-Key, Authorization: Bearer, or api_key query param for browser dashboard access."""
    expected = _configured_api_key()
    provided = (
        request.headers.get("X-API-Key")
        or _extract_bearer(request.headers.get("Authorization"))
        or request.query_params.get("api_key")
    )
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Provide X-API-Key or Authorization: Bearer <key>.",
        )
    return provided
