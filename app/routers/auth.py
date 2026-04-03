"""
Auth Router: Kullanıcı kayıt, giriş, profil yönetimi.
6 endpoint: register, login, save-push-token, get/update/delete profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.core.logging import logger
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserProfileUpdate,
    PushTokenRequest,
    TokenResponse,
    UserProfileResponse,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=MessageResponse)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    """Yeni kullanıcı kaydı."""
    # E-posta kontrolü
    result = await db.execute(select(User).where(User.email == user.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta zaten kayıtlı.",
        )

    # Kullanıcı oluştur
    new_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
    )
    db.add(new_user)
    await db.commit()

    logger.info(f"Yeni kullanıcı kaydı: {user.email}")
    return MessageResponse(message="Kayıt başarılı")


@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    """Kullanıcı girişi, JWT token döndürür."""
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )

    token = create_access_token(data={"sub": db_user.email})
    logger.info(f"Kullanıcı giriş yaptı: {user.email}")
    return TokenResponse(access_token=token)


@router.post("/save-push-token", response_model=MessageResponse)
async def save_push_token(
    req: PushTokenRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Expo push notification token'ını kaydeder."""
    result = await db.execute(select(User).where(User.email == current_user["email"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    user.push_token = req.token
    await db.commit()

    logger.debug(f"Push token kaydedildi: {current_user['email']}")
    return MessageResponse(message="Token kaydedildi")


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcı profil bilgilerini döndürür."""
    result = await db.execute(select(User).where(User.email == current_user["email"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    return UserProfileResponse(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        location=user.location,
    )


@router.put("/me", response_model=MessageResponse)
async def update_profile(
    p: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Profil bilgilerini günceller."""
    result = await db.execute(select(User).where(User.email == current_user["email"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    user.first_name = p.first_name
    user.last_name = p.last_name
    user.location = p.location
    await db.commit()

    logger.info(f"Profil güncellendi: {current_user['email']}")
    return MessageResponse(message="Profil güncellendi")


@router.delete("/me", response_model=MessageResponse)
async def delete_my_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcı hesabını ve ilişkili tüm verileri siler (cascade)."""
    result = await db.execute(select(User).where(User.email == current_user["email"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    await db.delete(user)
    await db.commit()

    logger.info(f"Hesap silindi: {current_user['email']}")
    return MessageResponse(message="Hesap silindi")
