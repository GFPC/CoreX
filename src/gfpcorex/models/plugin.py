"""
Plugin model for GFP CoreX.
Represents user-created plugins stored in database.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..core.database import Base


class Plugin(Base):
    """Plugin model for storing user-created plugin code."""
    
    __tablename__ = "plugins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    hashsum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Plugin(id={self.id}, name='{self.name}', active={self.is_active})>"
    
    @property
    def code_hash(self) -> str:
        """Calculate hash of current code."""
        import hashlib
        return hashlib.sha256(self.code.encode()).hexdigest()
    
    def is_code_changed(self) -> bool:
        """Check if code has been modified since last hash update."""
        return self.code_hash != self.hashsum 