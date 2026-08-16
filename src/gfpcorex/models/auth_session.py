"""
AuthSession model for GFP CoreX.
Represents user authentication sessions and tokens.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.database import Base

if TYPE_CHECKING:
    # Imported only for typing the relationship; avoids a runtime circular import.
    from .user import User


class AuthSession(Base):
    """AuthSession model for storing user authentication sessions."""
    
    __tablename__ = "auth_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="auth_sessions")
    
    def __repr__(self) -> str:
        return f"<AuthSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.expires_at is None:
            return False  # Perpetual token
        # Backends such as SQLite return naive datetimes even for tz-aware columns;
        # treat those as UTC so the comparison is always aware-vs-aware.
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return datetime.now(UTC) > expires_at
    
    @property
    def is_perpetual(self) -> bool:
        """Check if session is perpetual (no expiration)."""
        return self.expires_at is None 