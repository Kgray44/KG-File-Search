"""Authentication and bind-safety helpers for the local KGFS API."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Header, HTTPException

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class APIAuthSettings:
    require_token: bool
    token_env: str


def is_local_host(host: str) -> bool:
    return host.strip().lower() in LOCAL_HOSTS


def validate_api_bind(host: str, *, allow_network: bool) -> None:
    if not is_local_host(host) and not allow_network:
        raise ValueError("KGFS API binds to 127.0.0.1 by default. Use --allow-network explicitly for non-local hosts.")


def token_from_env(token_env: str) -> str | None:
    return os.environ.get(token_env)


def require_api_token(settings: APIAuthSettings, authorization: str | None = Header(default=None)) -> None:
    if not settings.require_token:
        return
    expected = token_from_env(settings.token_env)
    if not expected:
        raise HTTPException(status_code=503, detail=f"API token is required but {settings.token_env} is not set.")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Missing or invalid KGFS API token.")
