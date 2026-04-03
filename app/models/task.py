"""
SQLAlchemy ORM modeli: Tasks tablosu.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    date_text = Column(String(50), nullable=True)
    status = Column(String(20), default="pending")  # pending, approved, completed
    is_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # İlişki
    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"
