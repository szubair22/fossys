"""
Authentication and user schemas.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    passwordConfirm: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=200)


class UserLogin(BaseModel):
    """User login request - matches PocketBase auth-with-password."""
    identity: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response - matches PocketBase user record format."""
    id: str
    email: str
    name: str
    verified: bool = False
    display_name: Optional[str] = None
    timezone: Optional[str] = None
    notify_meeting_invites: bool = True
    notify_meeting_reminders: bool = True
    avatar: Optional[str] = None
    created: datetime
    updated: datetime
    collectionId: str = "users"
    collectionName: str = "users"

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Auth token response - matches PocketBase auth response format."""
    token: str
    record: UserResponse


class UserUpdate(BaseModel):
    """User profile update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    display_name: Optional[str] = Field(None, max_length=200)
    timezone: Optional[str] = Field(None, max_length=100)
    notify_meeting_invites: Optional[bool] = None
    notify_meeting_reminders: Optional[bool] = None


class PasswordChange(BaseModel):
    """Password change request."""
    oldPassword: str
    password: str = Field(..., min_length=8)
    passwordConfirm: str = Field(..., min_length=8)
