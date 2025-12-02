"""
Authentication endpoints for OrgMeet.

Endpoints:
- POST /api/collections/users/records - Register new user
- POST /api/collections/users/auth-with-password - Login
- POST /api/collections/users/auth-refresh - Refresh token
- GET /api/collections/users/records/{user_id} - Get user profile
- PATCH /api/collections/users/records/{user_id} - Update user profile
- POST /api/collections/users/records/{user_id}/change-password - Change password

Note: Logout is handled client-side by clearing the JWT token from localStorage.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    UserUpdate, PasswordChange
)

router = APIRouter()


def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse schema."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        verified=user.verified,
        display_name=user.display_name,
        timezone=user.timezone,
        notify_meeting_invites=user.notify_meeting_invites,
        notify_meeting_reminders=user.notify_meeting_reminders,
        avatar=user.avatar,
        created=user.created,
        updated=user.updated,
    )


@router.post("/records", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Validate passwords match
    if user_data.password != user_data.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password": {"message": "Passwords do not match"}}
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"email": {"message": "Email already registered"}}
        )

    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
        verified=False,
    )

    db.add(user)
    await db.commit()  # Commit immediately so subsequent login can find the user
    await db.refresh(user)

    return user_to_response(user)


@router.post("/auth-with-password", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with email/password."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.identity))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password"
        )

    # Create access token
    token = create_access_token(subject=user.id)

    return TokenResponse(
        token=token,
        record=user_to_response(user)
    )


@router.post("/auth-refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """Refresh the current auth token."""
    # Create new access token
    token = create_access_token(subject=current_user.id)

    return TokenResponse(
        token=token,
        record=user_to_response(current_user)
    )


@router.get("/records/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user_to_response(user)


@router.patch("/records/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile."""
    # Users can only update themselves
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Update fields
    if user_data.name is not None:
        current_user.name = user_data.name
    if user_data.display_name is not None:
        current_user.display_name = user_data.display_name
    if user_data.timezone is not None:
        current_user.timezone = user_data.timezone
    if user_data.notify_meeting_invites is not None:
        current_user.notify_meeting_invites = user_data.notify_meeting_invites
    if user_data.notify_meeting_reminders is not None:
        current_user.notify_meeting_reminders = user_data.notify_meeting_reminders

    current_user.updated = datetime.now(timezone.utc)
    await db.flush()

    return user_to_response(current_user)


@router.post("/records/{user_id}/change-password")
async def change_password(
    user_id: str,
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change user password.
    """
    # Users can only change their own password
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Verify old password
    if not verify_password(password_data.oldPassword, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new passwords match
    if password_data.password != password_data.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )

    # Update password
    current_user.password_hash = get_password_hash(password_data.password)
    current_user.updated = datetime.now(timezone.utc)
    await db.flush()

    return {"message": "Password changed successfully"}
