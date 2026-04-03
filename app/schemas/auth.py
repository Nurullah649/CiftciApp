"""
Auth ile ilgili Pydantic şemaları (request/response modelleri).
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    """Kullanıcı kayıt isteği."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)


class UserLogin(BaseModel):
    """Kullanıcı giriş isteği."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserProfileUpdate(BaseModel):
    """Profil güncelleme isteği."""
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    location: str = Field(max_length=100)


class UserProfileResponse(BaseModel):
    """Profil bilgisi yanıtı."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    location: Optional[str] = None


class PushTokenRequest(BaseModel):
    """Push notification token kayıt isteği."""
    token: str = Field(max_length=500)


class TokenResponse(BaseModel):
    """Login yanıtı."""
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Genel mesaj yanıtı."""
    message: str
