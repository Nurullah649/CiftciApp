import os
import mysql.connector
import jwt
import datetime
import requests
import json
import re
import folium
import ollama
import random
from qdrant_client import QdrantClient
from folium.plugins import MiniMap
from geopy.geocoders import Nominatim
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from apscheduler.schedulers.background import BackgroundScheduler
from exponent_server_sdk import PushClient, PushMessage

# --- AYARLAR ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_EMBED_MODEL = "embeddinggemma" 
QDRANT_COLLECTION = "tarim_bilgi_bankasi"

# --- ORTAM DEĞİŞKENLERİ ---
SECRET_KEY = os.getenv("SECRET_KEY", "gizli_anahtar_buraya_yazin")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "tarim_db")

# API Anahtarları
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WAPI_KEY = os.getenv("WEATHER_API_KEY")
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

app = FastAPI(title="NPC-AI Çiftçi Asistanı (Şanlıurfa Simülasyonu)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- RAG BAĞLANTISI ---
try:
    qdrant_client = QdrantClient(url=QDRANT_URL)
    print(f"✅ Qdrant bağlantısı başarılı: {QDRANT_URL}")
except Exception as e:
    print(f"❌ Qdrant bağlantı hatası: {e}")
    qdrant_client = None


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

# --- KONUM VE HAVA DURUMU ---
def get_random_urfa_location():
    """
    Şanlıurfa sınırları içinden rastgele bir koordinat.
    """
    lat = random.uniform(36.90, 37.60)
    lon = random.uniform(38.00, 39.80)
    return lat, lon

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
    if not GEO_KEY: return "Şanlıurfa (Simülasyon)"
    try:
        url = f"{GEO_URL}/json"
        params = {"q": f"{lat}+{lon}", "key": GEO_KEY, "language": "tr", "no_annotations": 1}
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data['results']:
            comps = data['results'][0]['components']
            loc_name = comps.get('suburb') or comps.get('village') or comps.get('town') or comps.get('county') or "Şanlıurfa Kırsalı"
            return f"{loc_name}, Şanlıurfa"
        else:
            return "Şanlıurfa Bölgesi"
    except Exception as e:
        print(f"Konum Hatası: {e}")
        return "Şanlıurfa"

# --- RAG SORGULAMA ---
def get_rag_context(enriched_query):
    if not qdrant_client:
        return "Veritabanı bağlantısı yok."
    try:
        vec_response = ollama.embeddings(model=OLLAMA_EMBED_MODEL, prompt=enriched_query)
        vec = vec_response.get("embedding")
        if not vec: return "Embedding oluşturulamadı."

        results = qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=vec,
            limit=3
        )
        hits = results.points
        context_text = ""
        for hit in hits:
            kaynak = hit.payload.get('kaynak', 'Genel Bilgi')
            metin = hit.payload.get('tam_metin', '')
            score = hit.score
            if score > 0.4:
                context_text += f"- [{kaynak}]: {metin}\n"
        
        if not context_text:
            return "Veritabanında bu bağlama uygun spesifik bilgi bulunamadı." 
        return context_text
    except Exception as e:
        print(f"RAG Hatası: {e}")
        return "Veritabanı sorgusunda hata oluştu."

# --- YAPAY ZEKA ÇAĞRISI ---
def ask_deepseek(system_prompt, user_question, history_messages=[]):
    if not DEEPSEEK_API_KEY: return "HATA: API Key yok."
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_question})
    payload = {"model": "deepseek-chat", "messages": messages, "temperature": 0.5} 

    try:
        r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=45)
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI Hatası: {str(e)}"

# --- BİLDİRİM VE SCHEDULER ---
def send_push_notification(token, title, body):
    try:
        PushClient().publish(PushMessage(to=token, title=title, body=body, sound="default"))
    except: pass

def check_and_send_notifications():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sql = """SELECT t.id, t.title, t.date_text, u.push_token FROM tasks t 
                 JOIN users u ON t.user_id = u.id 
                 WHERE t.status = 'approved' AND t.is_notified = 0 AND t.date_text <= %s"""
        cursor.execute(sql, (current_time,))
        tasks = cursor.fetchall()
        for task in tasks:
            if task['push_token']:
                send_push_notification(task['push_token'], "Çiftçi Asistanı", task['title'])
            cursor.execute("UPDATE tasks SET is_notified = 1 WHERE id = %s", (task['id'],))
            conn.commit()
    except: pass
    finally: conn.close()

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
    finally: conn.close()

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
    finally: conn.close()

@app.post("/auth/save-push-token")
def save_push_token(req: PushTokenRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "UPDATE users SET push_token = %s WHERE email = %s"
        cursor.execute(sql, (req.token, current_user['email']))
        conn.commit()
        return {"message": "Token kaydedildi"}
    finally: conn.close()

@app.delete("/auth/me")
def delete_my_account(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "DELETE FROM users WHERE email = %s"
        cursor.execute(sql, (current_user['email'],))
        conn.commit()
        return {"message": "Hesap silindi."}
    finally: conn.close()

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

# --- HAVA DURUMU ENDPOINT (DÜZELTİLDİ) ---
@app.get("/weather")
def weather_endpoint(lat: float, lon: float):
    w = fetch_weather(lat, lon)
    l = fetch_location_name(lat, lon)
    if w: return {**w, "location": l}
    raise HTTPException(status_code=404, detail="Veri yok")

# --- HARİTA ---
@app.post("/tools/generate-map", response_class=HTMLResponse)
def generate_map_html(req: MapRequest):
    city = req.city
    geolocator = Nominatim(user_agent="agrollm_dynamic_map")
    try:
        location = geolocator.geocode(city, timeout=10)
    except:
        raise HTTPException(status_code=503, detail="Harita servisi meşgul.")
    if not location: raise HTTPException(status_code=404, detail="Konum bulunamadı.")
    
    lat, lon = location.latitude, location.longitude
    m = folium.Map(location=[lat, lon], zoom_start=18, control_scale=True, tiles=None)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Uydu', overlay=False).add_to(m)
    folium.Marker([lat, lon], popup=city, icon=folium.Icon(color="red")).add_to(m)
    MiniMap(toggle_display=True).add_to(m)
    return m.get_root().render()

# --- GÖREVLER ---
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
    cursor.execute("UPDATE tasks SET status = %s WHERE id = %s AND user_id = %s", (update.status, task_id, uid))
    conn.commit()
    conn.close()
    return {"message": "Durum güncellendi"}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, uid))
    conn.commit()
    conn.close()
    return {"message": "Görev silindi"}

# --- CHAT GEÇMİŞİ ---
@app.get("/chat/history")
def chat_history(current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, role, message, created_at FROM chat_history WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (uid,))
    res = cursor.fetchall()
    conn.close()
    return res

@app.delete("/chat/history")
def clear_chat_history(current_user: dict = Depends(get_current_user)):
    uid = get_user_id_by_email(current_user['email'])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (uid,))
    conn.commit()
    conn.close()
    return {"message": "Sohbet temizlendi"}

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
            api_role = "assistant" if role == "ai" else "user"
            messages.append({"role": api_role, "content": msg})
        return messages
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# --- ANA ENDPOINT: SORU SORMA (ASK) ---
@app.post("/ask", response_class=PlainTextResponse)
def ask_ai(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        user_id = get_user_id_by_email(current_user['email'])
        
        # 1. KONUM (Urfa Simülasyonu: Rastgele Seçim)
        lat, lon = get_random_urfa_location()
        
        # 2. VERİLERİ ÇEK
        weather = fetch_weather(lat, lon)
        loc_name = fetch_location_name(lat, lon)
        
        weather_str = "Bilinmiyor"
        if weather:
            weather_str = f"{weather['condition']}, Sıcaklık {weather['temp']}°C, Nem %{weather['humidity']}"

        # 3. RAG SORGUSU
        rag_query_input = f"Soru: {request.question} | Konum: {loc_name} | Hava Durumu: {weather_str}"
        rag_context = get_rag_context(rag_query_input)

        # 4. GEÇMİŞİ AL
        history = get_structured_chat_history(user_id, limit=6)
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # 5. SYSTEM PROMPT İÇİN VERİ HAZIRLIĞI
        context_data = f"""
        [SİSTEM TARİHİ]: {current_date}
        [SEÇİLEN KONUM]: {loc_name} (Simülasyon Modu: Şanlıurfa)
        [ANLIK HAVA DURUMU]: {weather_str}
        
        [VERİTABANI BİLGİSİ (RAG)]:
        {rag_context}
        """

        # 6. YENİ SYSTEM PROMPT (KULLANICI TALEBİNE GÖRE)
        system_prompt = f"""
        ### 1. KİMLİK VE ROL (PERSONA) ###
        Sen 'Çiftçi AI'sın. 30 yıllık deneyime sahip Kıdemli Ziraat Mühendisi ve Veri Analistisin. Bilimsel verileri, çiftçinin anlayacağı pratik, uygulanabilir ve net dille aktarırsın. Amacın sadece bilgi vermek değil, ürün verimliliğini ve sürdürülebilirliği artırmaktır.

        ### 2. BAĞLAM VERİLERİ (CONTEXT) ###
        {context_data}

        ### 3. KESİN SINIRLAR VE YASAKLAR (HARD CONSTRAINTS) ###
        Model olarak aşağıdaki kurallara **istisnasız** uymalısın:
           - **Konu Sınırlaması:** Sadece bitkisel üretim, toprak sağlığı, sulama, gübreleme ve zirai mücadele konularında cevap ver.
             - *YASAK:* Yemek tarifleri, arazi hukuku, finansal yatırım, hayvancılık veya tıbbi sağlık.
             - *CEVAP KALIBI:* Konu dışı sorularda: "Ben uzman bir ziraat asistanıyım. Sadece tarımsal yetiştiricilik ve bitki sağlığı konularında size yardımcı olabilirim." cevabını ver.
           - **Gereksiz Planlama:** Kullanıcı açıkça "plan", "takvim" veya "program" istemedikçe uzun listeler oluşturma. Doğrudan soruya odaklan.
           - **Kimyasal Güvenliği:** Eğer bir zirai ilaç öneriyorsan, cevabın içine mutlaka **kalın harflerle** koruyucu ekipman (maske, eldiven) uyarısı ve hasat öncesi bekleme süresi uyarısını ekle.

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
              - [ANLIK DURUM] verisine bak. Eğer yağmur görünüyorsa sulama önerisini buna göre güncelle.

        ### 5. ÇIKTI FORMATI VE GİZLİ TETİKLEYİCİLER ###
        Cevabın akıcı bir Türkçe ile, Markdown formatında (önemli yerler **kalın**) olmalıdır.
        Eğer kullanıcıya spesifik bir **EYLEM** (Sulama, İlaçlama, Gübreleme, Hasat, Budama) öneriyorsan, cevabın en son satırına sistemin takvime işleyebileceği şu gizli kodu ekle:

        [GÖREV: <Eylem Tipi> | <Kısa Açıklama> | YYYY-MM-DD HH:MM]

        *Tarih Kuralı:* Tarihi verilen bağlamdaki tarihe ve hava durumu verisine göre en uygun zamana (sabah erken veya akşam serinliği) hesapla.
        """

        # 7. AI ÇAĞRISI
        ai_response = ask_deepseek(system_prompt, request.question, history)

        # 8. GÖREV İŞLEME
        task_pattern = r"\[GÖREV:\s*(.*?)\s*\|\s*(.*?)\]"
        tasks_found = re.findall(task_pattern, ai_response)

        if tasks_found:
            for title, date_text in tasks_found:
                sql_task = "INSERT INTO tasks (user_id, title, date_text, status) VALUES (%s, %s, %s, 'pending')"
                cursor.execute(sql_task, (user_id, title.strip(), date_text.strip()))
                conn.commit()
            ai_response = re.sub(task_pattern, "", ai_response).strip()
            ai_response += "\n\n🚜 (Öneri takviminize işlendi.)"

        cursor.execute("INSERT INTO chat_history (user_id, role, message) VALUES (%s, 'user', %s)", (user_id, request.question))
        cursor.execute("INSERT INTO chat_history (user_id, role, message) VALUES (%s, 'ai', %s)", (user_id, ai_response))
        conn.commit()

        return ai_response

    except Exception as e:
        print(f"Chat Hatası: {e}")
        return "Sistemde geçici bir hata oluştu."
    finally:
        if conn.is_connected(): conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
