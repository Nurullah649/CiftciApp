"""
Task ile ilgili Pydantic şemaları.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TaskUpdate(BaseModel):
    """Görev durumu güncelleme isteği."""
    status: str = Field(..., pattern="^(pending|approved|completed)$")


class TaskResponse(BaseModel):
    """Görev bilgisi yanıtı."""
    id: int
    title: str
    date_text: Optional[str] = None
    status: str
    is_notified: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
