"""
App Setting model - global application settings.
"""
from typing import Optional
from sqlalchemy import String, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel


class AppSetting(BaseModel):
    """
    Global application settings for OrgSuite.

    These settings apply to the entire application and are managed
    by superadmin users. Examples:
    - app_name
    - primary_color
    - support_email
    - features (enable_governance, enable_membership, etc.)
    """
    __tablename__ = "app_settings"
    __table_args__ = (
        Index("ix_app_settings_key", "key", unique=True),
    )

    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<AppSetting {self.key}>"
