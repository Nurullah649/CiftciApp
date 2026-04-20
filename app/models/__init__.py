"""
Tüm SQLAlchemy modelleri burada re-export edilir.
Böylece Base.metadata tüm tabloları tanır.
"""

from app.models.user import User
from app.models.task import Task
from app.models.chat import ChatHistory

__all__ = ["User", "Task", "ChatHistory"]
