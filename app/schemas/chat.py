"""
Chat ile ilgili Pydantic şemaları.
"""

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """AI'a soru sorma isteği."""
    question: str = Field(min_length=1, max_length=2000)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)


class MapRequest(BaseModel):
    """Harita oluşturma isteği."""
    city: str = Field(min_length=1, max_length=100)
