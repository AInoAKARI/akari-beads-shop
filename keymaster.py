"""Shared Keymaster helpers."""

import os
from typing import Any

import httpx
from fastapi import HTTPException

KEYMASTER_URL = os.environ.get("AKARI_KEYMASTER_URL", "")
KEYMASTER_TOKEN = os.environ.get("AKARI_KEYMASTER_TOKEN", "")


async def get_key(service: str, key_name: str = "api_key") -> str:
    """Fetch a secret from Keymaster."""
    if not KEYMASTER_URL or not KEYMASTER_TOKEN:
        raise HTTPException(status_code=500, detail="Keymaster not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{KEYMASTER_URL}/vault/api-key",
            params={
                "api_name": service,
                "service": service,
                "key_name": key_name,
            },
            headers={"Authorization": f"Bearer {KEYMASTER_TOKEN}"},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch Keymaster secret: {service}/{key_name}",
        )

    data: dict[str, Any] = resp.json()
    value = data.get("api_key") or data.get("key") or data.get("value") or ""
    if not value:
        raise HTTPException(
            status_code=502,
            detail=f"Empty Keymaster secret: {service}/{key_name}",
        )
    return value
