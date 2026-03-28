"""Pydantic request/response schemas for the HODOOR API."""

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1)


class ChatMessageResponse(BaseModel):
    reply: str
    timestamp: str


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ApplianceResponse(BaseModel):
    id: int
    name: str
    category: str | None = None
    create_date: str | None = None
    maintenance_requests: list[dict] = []
