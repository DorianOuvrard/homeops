"""Dependency injection for HODOOR FastAPI routes."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from bot.api.auth import decode_access_token
from bot.api.models import UserResponse
from bot.db import get_user_by_id

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()

# These are set during app startup so all routes can access them.
_jwt_secret: str = ""
_shared_deps: dict = {}


def set_jwt_secret(secret: str) -> None:
    global _jwt_secret
    _jwt_secret = secret


def set_shared_deps(deps: dict) -> None:
    global _shared_deps
    _shared_deps = deps


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> UserResponse:
    token = credentials.credentials
    try:
        user_id = decode_access_token(token, _jwt_secret)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return UserResponse(id=user["id"], email=user["email"])


CurrentUser = Annotated[UserResponse, Depends(get_current_user)]


def get_deps() -> dict:
    return _shared_deps
