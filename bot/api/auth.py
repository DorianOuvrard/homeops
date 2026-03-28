"""Authentication endpoints and JWT utilities for HODOOR."""

import logging
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import APIRouter, HTTPException, status
from jose import JWTError, jwt

from bot.api.models import LoginRequest, LoginResponse, SignupRequest, UserResponse
from bot.db import create_user, get_user_by_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_JWT_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24


def create_access_token(user_id: str, secret: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, secret: str) -> str:
    """Decode JWT and return user_id (sub). Raises JWTError on invalid token."""
    payload = jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])
    user_id: str = payload.get("sub", "")
    if not user_id:
        raise JWTError("Missing sub claim")
    return user_id


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _make_router(jwt_secret: str) -> APIRouter:
    """Return auth router with jwt_secret bound via closure."""

    @router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    async def signup(body: SignupRequest):
        password_hash = hash_password(body.password)
        user = await create_user(body.email, password_hash)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        logger.info("New user signed up: %s", body.email)
        return UserResponse(id=user["id"], email=user["email"])

    @router.post("/login", response_model=LoginResponse)
    async def login(body: LoginRequest):
        user = await get_user_by_email(body.email)
        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        token = create_access_token(user["id"], jwt_secret)
        return LoginResponse(access_token=token)

    return router


def build_auth_router(jwt_secret: str) -> APIRouter:
    return _make_router(jwt_secret)
