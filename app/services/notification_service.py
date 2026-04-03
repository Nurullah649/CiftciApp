"""
Bildirim Servisi: Push notification gönderimi ve zamanlayıcı.
Senkron MySQL bağlantısı kullanır (APScheduler arka plan thread'i için).
"""

import datetime
from typing import Optional

import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from exponent_server_sdk import PushClient, PushMessage

from app.core.config import settings
from app.core.logging import logger


class NotificationService:
    """Push notification ve zamanlanmış görev bildirimleri."""

    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None

    def start_scheduler(self):
        """APScheduler'ı başlatır."""
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self._check_and_send,
            "interval",
            minutes=1,
        )
        self.scheduler.start()
        logger.info("✅ Bildirim zamanlayıcısı başlatıldı (1 dk aralık)")

    def stop_scheduler(self):
        """APScheduler'ı durdurur."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("🛑 Bildirim zamanlayıcısı durduruldu")

    @staticmethod
    def send_push_notification(token: str, title: str, body: str):
        """Expo Push Notification gönderir."""
        try:
            PushClient().publish(
                PushMessage(to=token, title=title, body=body, sound="default")
            )
            logger.debug(f"📤 Bildirim gönderildi: {title}")
        except Exception as e:
            logger.error(f"Bildirim gönderilemedi: {e}")

    def _get_sync_connection(self):
        """APScheduler thread'i için senkron MySQL bağlantısı."""
        return mysql.connector.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )

    def _check_and_send(self):
        """Onaylanmış ve bildirilmemiş görevleri kontrol edip bildirim gönderir."""
        conn = None
        try:
            conn = self._get_sync_connection()
            cursor = conn.cursor()

            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            cursor.execute("""
                SELECT t.id, t.title, t.date_text, u.push_token 
                FROM tasks t 
                JOIN users u ON t.user_id = u.id
                WHERE t.status = 'approved' 
                AND t.is_notified = 0 
                AND t.date_text <= %s
            """, (current_time,))
            tasks = cursor.fetchall()

            for task_id, title, date_text, push_token in tasks:
                if push_token:
                    self.send_push_notification(
                        push_token, "Çiftçi Asistanı", title
                    )
                cursor.execute(
                    "UPDATE tasks SET is_notified = 1 WHERE id = %s",
                    (task_id,),
                )

            conn.commit()

            if tasks:
                logger.info(f"📬 {len(tasks)} bildirim gönderildi")

        except Exception as e:
            logger.error(f"Bildirim kontrol hatası: {e}")
        finally:
            if conn and conn.is_connected():
                conn.close()


# Singleton instance
notification_service = NotificationService()
