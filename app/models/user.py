"""
SQLAlchemy ORM modeli: Users tablosu.
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)
    push_token = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # İlişkiler (cascade ile hesap silinince veriler de silinir)
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
