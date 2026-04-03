"""
Chat Router: AI asistan ile sohbet, geçmiş yönetimi.
3 endpoint: ask (LLM inference + streaming), chat/history, chat/clear
"""

import re
import asyncio
import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.models.task import Task
from app.models.chat import ChatHistory
from app.schemas.chat import QueryRequest
from app.schemas.auth import MessageResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.weather_service import (
    fetch_weather_and_location,
    get_random_urfa_location,
)

router = APIRouter(tags=["Chat"])


async def _get_user(email: str, db: AsyncSession) -> User:
    """Email'den User nesnesini döndürür."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user


async def _get_chat_history(user_id: int, db: AsyncSession, limit: int = 2) -> str:
    """ChatML formatında sohbet geçmişi oluşturur."""
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    if not rows:
        return ""

    # Ters sırala (kronolojik)
    rows = list(reversed(rows))
    history = ""
    for row in rows:
        role = "user" if row.role == "user" else "assistant"
        history += f"<|im_start|>{role}\n{row.message}<|im_end|>\n"
    return history


@router.post("/ask", response_class=PlainTextResponse)
async def ask_ai(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ana AI endpoint'i.
    1. Konum + hava durumunu çeker
    2. RAG context oluşturur
    3. LLM ile yanıt üretir (thread pool'da)
    4. Görev ayrıştırma yapar
    5. Chat geçmişine kaydeder
    """
    if not llm_service.model_loaded:
        raise HTTPException(status_code=500, detail="Sunucuda AI modeli yüklü değil.")

    user = await _get_user(current_user["email"], db)

    # --- 1. KONUM VE HAVA DURUMU ---
    if settings.SIMULATION_MODE:
        lat, lon = get_random_urfa_location()
        logger.info("📍 MOD: Simülasyon (Urfa)")
    elif request.lat and request.lon:
        lat, lon = request.lat, request.lon
        logger.info(f"📍 MOD: Gerçek GPS ({lat}, {lon})")
    else:
        lat, lon = get_random_urfa_location()
        logger.info("📍 MOD: Veri Yok → Simülasyon")

    weather, loc_name = await fetch_weather_and_location(lat, lon)

    weather_str = "Bilinmiyor"
    if weather:
        weather_str = f"{weather['condition']}, Sıcaklık {weather['temp']}°C, Nem %{weather['humidity']}"

    # --- 2. RAG CONTEXT (Thread Pool) ---
    rag_query_input = f"Soru: {request.question} | Konum: {loc_name} | Hava Durumu: {weather_str}"
    
    loop = asyncio.get_event_loop()
    rag_context = await loop.run_in_executor(None, rag_service.get_context, rag_query_input)

    # --- 3. CHAT GEÇMİŞİ ---
    history_str = await _get_chat_history(user.id, db)

    # --- 4. PROMPT OLUŞTURMA ---
    current_date_obj = datetime.datetime.now()
    current_date_str = current_date_obj.strftime("%Y-%m-%d %H:%M")

    context_data = f"""
    [SİSTEM TARİHİ]: {current_date_str}
    [SEÇİLEN KONUM]: {loc_name}
    [ANLIK HAVA DURUMU]: {weather_str}
    [VERİTABANI BİLGİSİ (RAG)]:
    {rag_context}
    """

    full_prompt = llm_service.build_prompt(
        question=request.question,
        context_data=context_data,
        history_str=history_str,
        current_date_str=current_date_str,
    )

    # --- 5. LLM INFERENCE & STREAMING ---
    from starlette.concurrency import iterate_in_threadpool

    async def response_generator():
        full_response = ""
        logger.info("🌊 Chat stream başlatılıyor...")
        
        # Senkron generator'ı thread pool'da çalıştırarak async hale getir
        stream_iterator = llm_service.stream_generate(full_prompt)
        
        token_count = 0
        async for token in iterate_in_threadpool(stream_iterator):
            if token_count == 0:
                logger.info("🌊 İlk token üretildi!")
            token_count += 1
            full_response += token
            yield token
        
        logger.info(f"🌊 Stream tamamlandı. Toplam token: {token_count}")

        # --- 6. GÖREV AYIKLAMA (Stream bittikten sonra) ---
        task_pattern = r"\[GÖREV:\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\]"
        tasks_found = re.findall(task_pattern, full_response)

        if tasks_found:
            for title, description, date_text in tasks_found:
                final_date = date_text.strip()
                try:
                    task_dt = datetime.datetime.strptime(final_date, "%Y-%m-%d %H:%M")
                    if task_dt < current_date_obj:
                        corrected_dt = current_date_obj + datetime.timedelta(days=1)
                        corrected_dt = corrected_dt.replace(
                            hour=task_dt.hour, minute=task_dt.minute
                        )
                        final_date = corrected_dt.strftime("%Y-%m-%d %H:%M")
                        logger.warning(f"Geçmiş tarih düzeltildi: {date_text} → {final_date}")
                except ValueError:
                    pass

                new_task = Task(
                    user_id=user.id,
                    title=f"{title.strip()} - {description.strip()}",
                    date_text=final_date,
                    status="pending",
                )
                db.add(new_task)
            
            # Görev kodunu kullanıcıdan gizle (UI tarafında stream edildiği için burada replace işe yaramaz,
            # ama veritabanına temiz halini kaydedebiliriz)
            clean_response = re.sub(task_pattern, "", full_response).strip()
            # Kullanıcıya "öneri takvime işlendi" bilgisini yapıştır (stream bittiği için eklenemez, 
            # ama bir sonraki chunk olarak gönderebiliriz mi? Hayır, stream bitti.)
            # Pratik çözüm: Stream sırasında bu metin kullanıcıya gitti. 
            # Veritabanına temiz halini kaydedelim.
            full_response_db = clean_response + "\n\n🚜 (Bu işlemler öneri takviminize işlendi.)"
        else:
            full_response_db = full_response

        # --- 7. CHAT GEÇMİŞİNE KAYDET ---
        db.add(ChatHistory(user_id=user.id, role="user", message=request.question))
        db.add(ChatHistory(user_id=user.id, role="ai", message=full_response_db))
        await db.commit()

    return StreamingResponse(response_generator(), media_type="text/plain")


@router.get("/chat/history")
async def chat_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 50,
):
    """Sohbet geçmişini sayfalı olarak döndürür (en yeni en üstte)."""
    user = await _get_user(current_user["email"], db)

    limit = min(limit, 100)
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    return [
        {
            "id": row.id,
            "role": row.role,
            "message": row.message,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.delete("/chat/history", response_model=MessageResponse)
async def clear_chat_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcının tüm sohbet geçmişini temizler."""
    user = await _get_user(current_user["email"], db)

    await db.execute(
        delete(ChatHistory).where(ChatHistory.user_id == user.id)
    )
    await db.commit()

    logger.info(f"Chat geçmişi temizlendi: {current_user['email']}")
    return MessageResponse(message="Sohbet geçmişi temizlendi")
