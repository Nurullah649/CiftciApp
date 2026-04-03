"""
Tasks Router: Görev yönetimi (CRUD).
3 endpoint: get_tasks, update_task, delete_task
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.logging import logger
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskUpdate, TaskResponse
from app.schemas.auth import MessageResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def _get_user_id(email: str, db: AsyncSession) -> int:
    """Email'den kullanıcı ID'sini çeker."""
    result = await db.execute(select(User.id).where(User.email == email))
    user_id = result.scalar_one_or_none()
    if not user_id:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user_id


@router.get("", response_model=list[TaskResponse])
async def get_tasks(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcının tüm görevlerini listeler."""
    user_id = await _get_user_id(current_user["email"], db)

    result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.put("/{task_id}", response_model=MessageResponse)
async def update_task(
    task_id: int,
    update: TaskUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Görev durumunu günceller (pending/approved/completed)."""
    user_id = await _get_user_id(current_user["email"], db)

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")

    task.status = update.status
    await db.commit()

    logger.info(f"Görev güncellendi: #{task_id} → {update.status}")
    return MessageResponse(message="Görev güncellendi")


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Görevi siler."""
    user_id = await _get_user_id(current_user["email"], db)

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")

    await db.delete(task)
    await db.commit()

    logger.info(f"Görev silindi: #{task_id}")
    return MessageResponse(message="Görev silindi")
