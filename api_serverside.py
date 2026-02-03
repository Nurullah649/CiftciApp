import os
import mysql.connector
import jwt
import datetime
import requests
import json
import re
import folium
from folium.plugins import MiniMap
from geopy.geocoders import Nominatim
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from apscheduler.schedulers.background import BackgroundScheduler
from exponent_server_sdk import PushClient, PushMessage

# --- AYARLAR ---
PERSIST_DIRECTORY = "./tarim_veritabani"

# --- ORTAM DEĞİŞKENLERİ ---
SECRET_KEY = os.getenv("SECRET_KEY", "gizli_anahtar_buraya_yazin")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "tarim_db")

# API Anahtarları
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WAPI_KEY = os.getenv("WEATHER_API_KEY")
# DÜZELTME 1: os.getent -> os.getenv yapıldı
OW_KEY = os.getenv("OW_KEY")
GEO_KEY = os.getenv("GEOCODING_API_KEY")

# Harici API URL'leri
WAPI_URL = "https://api.weatherapi.com/v1"
GEO_URL = "https://api.opencagedata.com/geocode/v1"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

DB_CONFIG = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME
}

app = FastAPI(title="NPC-AI Çiftçi Asistanı (Dinamik Harita)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- RAG MODELLERİ ---
try:
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embedding_model)
except Exception:
    vector_db = None


# --- MODELLER ---
class UserRegister(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    location: str


class QueryRequest(BaseModel):
    question: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class MapRequest(BaseModel):
    city: str


class TaskUpdate(BaseModel):
    status: str


class PushTokenRequest(BaseModel):
    token: str


# --- YARDIMCI FONKSİYONLAR ---
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise HTTPException(status_code=401)
        return {"email": email}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token")


def get_user_id_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def fetch_weather(lat, lon):
    if not WAPI_KEY: return None
    try:
        url = f"{WAPI_URL}/current.json"
        params = {"key": WAPI_KEY, "q": f"{lat},{lon}", "lang": "tr"}
        r = requests.get(url, params=params, timeout=5)
        data = r.json().get("current", {})
        return {
            "temp": data.get("temp_c"),
            "humidity": data.get("humidity"),
            "condition": data.get("condition", {}).get("text"),
        }
    except:
        return None


def fetch_location_name(lat, lon):
    if not GEO_KEY: return "Konum"
    try:
        url = f"{GEO_URL}/json"
        params = {"q": f"{lat}+{lon}", "key": GEO_KEY, "language": "tr", "no_annotations": 1}
        r = requests.get(url, params=params, timeout=5)
        data = r.json()

        if data['results']:
            comps = data['results'][0]['components']
            # Sırasıyla hangisi varsa onu al: Şehir > İlçe > Kasaba > İl
            loc_name = comps.get('city') or comps.get('town') or comps.get('county') or comps.get(
                'province') or comps.get('state') or "Bilinmiyor"
            return loc_name
        else:
            return "Bilinmiyor"
    except Exception as e:
        print(f"Konum Hatası: {e}")  # Konsola hata basarak sorunu görebilirsin
        return "Bilinmiyor"

# --- HAFIZA YÖNETİMİ ---
def get_structured_chat_history(user_id, limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "SELECT role, message FROM chat_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()

        messages = []
        for role, msg in reversed(rows):
            # Veritabanında 'ai' -> API'de 'assistant'
            api_role = "assistant" if role == "ai" else "user"
            messages.append({"role": api_role, "content": msg})

        return messages
    finally:
        if conn.is_connected(): cursor.close(); conn.close()


# --- YAPAY ZEKA ÇAĞRISI ---
def ask_deepseek(system_prompt, user_question, history_messages=[]):
    if not DEEPSEEK_API_KEY: return "HATA: API Key yok."

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}

    # 1. Sistem Mesajı
    messages = [{"role": "system", "content": system_prompt}]

    # 2. Geçmiş Konuşmalar
    messages.extend(history_messages)

    # 3. Son Soru
    messages.append({"role": "user", "content": user_question})

    payload = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7}

    try:
        r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=45)
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI Hatası: {str(e)}"


# --- BİLDİRİM SERVİSİ ---
def send_push_notification(token, title, body):
    try:
        response = PushClient().publish(PushMessage(to=token, title=title, body=body, sound="default"))
    except Exception as e:
        print(f"Bildirim hatası: {e}")


def check_and_send_notifications():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sql = """SELECT t.id, t.title, t.date_text, u.push_token \
                 FROM tasks t \
                          JOIN users u ON t.user_id = u.id \
                 WHERE t.status = 'approved' \
                   AND t.is_notified = 0 \
                   AND t.date_text <= %s \
                   AND u.push_token IS NOT NULL"""
        cursor.execute(sql, (current_time,))
        tasks_to_notify = cursor.fetchall()
        for task in tasks_to_notify:
            send_push_notification(task['push_token'], "Hatırlatma 🚜", f"Görev Zamanı: {task['title']}")
            update_sql = "UPDATE tasks SET is_notified = 1 WHERE id = %s"
            cursor.execute(update_sql, (task['id'],))
            conn.commit()
    except Exception as e:
        print(f"Scheduler Hatası: {e}")
    finally:
        conn.close()


scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_notifications, 'interval', minutes=1)
scheduler.start()


# --- AUTH ENDPOINTS ---
@app.post("/auth/register", status_code=201)
def register(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı.")

        hashed_pw = get_password_hash(user.password)
        sql = "INSERT INTO users (email, password_hash, first_name, last_name) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (user.email, hashed_pw, user.first_name or "", user.last_name or ""))
        conn.commit()
        return {"message": "Kayıt başarılı"}
    finally:
        conn.close()


@app.post("/auth/login")
def login(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()
        if not db_user or not verify_password(user.password, db_user['password_hash']):
            raise HTTPException(status_code=401, detail="Hatalı giriş")
        return {"access_token": create_access_token({"sub": user.email})}
    finally:
        conn.close()


@app.post("/auth/save-push-token")
def save_push_token(req: PushTokenRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "UPDATE users SET push_token = %s WHERE email = %s"
        cursor.execute(sql, (req.token, current_user['email']))
        conn.commit()
        return {"message": "Token kaydedildi"}
    finally:
        conn.close()


@app.delete("/auth/me")
def delete_my_account(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "DELETE FROM users WHERE email = %s"
        cursor.execute(sql, (current_user['email'],))
        conn.commit()
        return {"message": "Hesap silindi."}
    finally:
        conn.close()


@app.get("/auth/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT email, first_name, last_name, location FROM users WHERE email=%s", (current_user['email'],))
    res = cursor.fetchone()
    conn.close()
    return res


@app.put("/auth/profile")
def update_profile(p: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "UPDATE users SET first_name=%s, last_name=%s, location=%s WHERE email=%s"
    cursor.execute(sql, (p.first_name, p.last_name, p.location, current_user['email']))
    conn.commit()
    conn.close()
    return {"message": "Profil güncellendi"}


# --- HARİTA ENDPOINT (DİNAMİK) ---
@app.post("/tools/generate-map", response_class=HTMLResponse)
def generate_map_html(req: MapRequest):
    """
    Şehri bulur ve Google Uydu katmanlı, tamamen gezilebilir
    bir HTML harita döndürür.
    """
    city = req.city
    geolocator = Nominatim(user_agent="agrollm_dynamic_map")

    # DÜZELTME 2: Timeout parametresi ve Hata Yakalama eklendi
    try:
        # Nominatim bazen yavaş yanıt verir, timeout'u artırdık (10 sn)
        location = geolocator.geocode(city, timeout=10)
    except Exception as e:
        # Geopy servisi yanıt vermezse veya başka bir hata olursa
        print(f"Geocoding hatası: {e}")
        raise HTTPException(status_code=503, detail="Harita servisi şu anda yoğun, lütfen tekrar deneyin.")

    if not location:
        raise HTTPException(status_code=404, detail="Konum bulunamadı.")

    lat, lon = location.latitude, location.longitude

    # Hava durumu verisi (Popup için)
    weather_info = "Veri Yok"
    try:
        w_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OW_KEY}&units=metric&lang=tr"
        w_res = requests.get(w_url, timeout=3).json()
        if w_res.get("weather"):
            weather_info = f"{w_res['weather'][0]['description'].capitalize()}, {w_res['main']['temp']}°C"
    except:
        pass

    # 1. Haritayı Oluştur (Daha yakın zoom ile başla)
    m = folium.Map(
        location=[lat, lon],
        zoom_start=18,
        control_scale=True,
        tiles=None  # Varsayılan haritayı kapatıyoruz, aşağıda Google ekleyeceğiz
    )

    # 2. Google Hybrid (Uydu + Yol İsimleri) Katmanını Ekle
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Uydu',
        overlay=False,
        control=True
    ).add_to(m)

    # 3. İşaretçi (Marker) Ekle
    popup_html = f"""
    <div style="width: 200px; font-family: sans-serif;">
        <h4 style="margin: 0 0 5px 0;">📍 {city}</h4>
        <p style="font-size: 14px;">{weather_info}</p>
        <p style="font-size: 11px; color: gray;">Haritada gezinebilirsiniz.</p>
    </div>
    """

    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup_html, max_width=250),
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    # 4. Mini Harita ve Katman Kontrolü
    MiniMap(toggle_display=True).add_to(m)
    folium.LayerControl().add_to(m)

    # HTML çıktısı
    return m.get_root().render()


# --- GÖREVLER (TASKS) ---
@app.get("/tasks")
def get_tasks(current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (uid,))
    res = cursor.fetchall()
    conn.close()
    return res


@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate, current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "UPDATE tasks SET status = %s WHERE id = %s AND user_id = %s"
    cursor.execute(sql, (update.status, task_id, uid))
    conn.commit()
    conn.close()
    return {"message": "Durum güncellendi"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (task_id, uid))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Görev bulunamadı")
        return {"message": "Görev silindi"}
    finally:
        conn.close()


# --- CHAT VE AI ---
@app.get("/chat/history")
def chat_history(current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, role, message, created_at FROM chat_history WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
        (uid,))
    res = cursor.fetchall()
    conn.close()
    return res


@app.delete("/chat/history")
def clear_chat_history(current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "DELETE FROM chat_history WHERE user_id = %s"
        cursor.execute(sql, (uid,))
        conn.commit()
        return {"message": "Sohbet geçmişi temizlendi"}
    finally:
        conn.close()


@app.post("/ask", response_class=PlainTextResponse)
def ask_ai(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        user_id = get_user_id_by_email(current_user['email'])
        lat = request.lat if request.lat else 37.87
        lon = request.lon if request.lon else 32.48
        weather = fetch_weather(lat, lon)
        loc_name = fetch_location_name(lat, lon)
        history = get_structured_chat_history(user_id, limit=10)

        realtime_info = f"Konum: {loc_name}. "
        if weather:
            realtime_info += f"Hava: {weather['condition']}, {weather['temp']}C, Nem %{weather['humidity']}."

        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        system_prompt = f"""
        ### 1. KİMLİK VE ROL (PERSONA) ###
        Sen 'Çiftçi AI'sın. 30 yıllık deneyime sahip Kıdemli Ziraat Mühendisi ve Veri Analistisin. Bilimsel verileri, çiftçinin anlayacağı pratik, uygulanabilir ve net dille aktarırsın. Amacın sadece bilgi vermek değil, ürün verimliliğini ve sürdürülebilirliği artırmaktır.

        ### 2. BAĞLAM VERİLERİ (CONTEXT) ###
        [ANLIK METEOROLOJİK VE TOPRAK VERİSİ]: {realtime_info}
        [SİSTEM TARİHİ]: {current_date}

        ### 3. KESİN SINIRLAR VE YASAKLAR (HARD CONSTRAINTS) ###
        Model olarak aşağıdaki kurallara **istisnasız** uymalısın:
           - **Konu Sınırlaması:** Sadece bitkisel üretim, toprak sağlığı, sulama, gübreleme ve zirai mücadele konularında cevap ver.
             - *YASAK:* Yemek tarifleri (ör: "Domates nasıl pişirilir?"), arazi hukuku/miras davaları, genel finansal yatırım tavsiyeleri, hayvancılık (veterinerlik konuları) veya tıbbi sağlık tavsiyeleri (ör: "Bu bitkiyi yersem baş ağrım geçer mi?").
             - *CEVAP KALIBI:* Konu dışı sorularda: "Ben uzman bir ziraat asistanıyım. Sadece tarımsal yetiştiricilik ve bitki sağlığı konularında size yardımcı olabilirim." cevabını ver.
           - **Gereksiz Planlama:** Kullanıcı açıkça "plan", "takvim" veya "program" istemedikçe uzun listeler oluşturma. Doğrudan soruya odaklan.
           - **Kimyasal Güvenliği:** Eğer bir zirai ilaç (fungisit, insektisit vb.) öneriyorsan, cevabın içine mutlaka **kalın harflerle** koruyucu ekipman (maske, eldiven) uyarısı ve hasat öncesi bekleme süresi uyarısını ekle.

        ### 4. CEVAPLAMA METODOLOJİSİ (INSTRUCTION TUNING) ###
        Cevaplarını oluştururken şu düşünce zincirini (Chain of Thought) izle:

           **A. PLAN/TAKVİM İSTENİRSE:**
              Kullanıcı bir üretim planı istediğinde cevabı şu başlıklarla yapılandır:
              - **1. Toprak ve Ön Hazırlık:** (pH dengesi, taban gübresi önerisi)
              - **2. Ekim/Dikim Stratejisi:** (Sıra arası mesafe, derinlik, ideal tarih)
              - **3. Bakım ve Besleme:** (Kritik sulama dönemleri, üst gübreleme zamanları)
              - **4. Hasat Kriterleri:** (Olgunluk belirtileri)

           **B. GENEL TAVSİYELER:**
              - Birim kullan (ör: Dekara 15kg, Ağaç başına 20 litre).
              - [ANLIK DURUM] verisine bak. Eğer yağmur görünüyorsa sulama önerisini buna göre güncelle (Ör: "Yarın yağmur bekleniyor, sulamayı erteleyin").

        ### 5. ÇIKTI FORMATI VE GİZLİ TETİKLEYİCİLER ###
        Cevabın akıcı bir Türkçe ile, Markdown formatında (önemli yerler **kalın**) olmalıdır.
        Eğer kullanıcıya spesifik bir **EYLEM** (Sulama, İlaçlama, Gübreleme, Hasat, Budama) öneriyorsan, cevabın en son satırına sistemin takvime işleyebileceği şu gizli kodu ekle:

        [GÖREV: <Eylem Tipi> | <Kısa Açıklama> | YYYY-MM-DD HH:MM]

        *Tarih Kuralı:* Tarihi [SİSTEM TARİHİ] ve hava durumu verisine göre en uygun zamana (sabah erken veya akşam serinliği) hesapla.

        Örnek Senaryo:
        Kullanıcı: "Domateslerde yaprak biti var, ne yapayım?"
        Cevap: ... (İlaçlama tavsiyesi ve güvenlik uyarısı içeriği) ...
        [GÖREV: İlaçlama | Domates yaprak biti mücadelesi | 2025-05-12 18:30]
        """
        ai_response = ask_deepseek(system_prompt, request.question, history)

        task_pattern = r"\[GÖREV:\s*(.*?)\s*\|\s*(.*?)\]"
        tasks_found = re.findall(task_pattern, ai_response)

        if tasks_found:
            for title, date_text in tasks_found:
                sql_task = "INSERT INTO tasks (user_id, title, date_text, status) VALUES (%s, %s, %s, 'pending')"
                cursor.execute(sql_task, (user_id, title.strip(), date_text.strip()))
                conn.commit()
            ai_response = re.sub(task_pattern, "", ai_response).strip()
            ai_response += "\n\n✅ (Planlar eklendi.)"

        cursor.execute("INSERT INTO chat_history (user_id, role, message) VALUES (%s, 'user', %s)",
                       (user_id, request.question))
        cursor.execute("INSERT INTO chat_history (user_id, role, message) VALUES (%s, 'ai', %s)",
                       (user_id, ai_response))
        conn.commit()
        return ai_response
    except Exception as e:
        print(f"Chat Hatası: {e}")
        return "Bir hata oluştu."
    finally:
        conn.close()


@app.get("/weather")
def weather_endpoint(lat: float, lon: float):
    w = fetch_weather(lat, lon)
    l = fetch_location_name(lat, lon)
    if w: return {**w, "location": l}
    return {"error": "Veri yok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)