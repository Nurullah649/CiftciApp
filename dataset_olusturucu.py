import json
import random
import time
import datetime
import os
import sys
import re
import requests

# --- ZAI CLIENT ENTEGRASYONU ---
try:
    from zai import ZaiClient
except ImportError:
    print("UYARI: 'zai' kütüphanesi bulunamadı. Lütfen yüklü olduğundan emin olun.")


    class ZaiClient:
        def __init__(self, api_key): pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs): pass

# !!! API KEY BURAYA GİRİLECEK !!!
API_KEY = ""
client = ZaiClient(api_key=API_KEY)

# --- KÜTÜPHANE KONTROLLERİ ---
try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("HATA: Gerekli kütüphaneler eksik. 'pip install pandas numpy requests openpyxl xlrd' çalıştırın.")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- AYARLAR ---
CIKTI_DOSYASI = os.path.join(BASE_DIR, "gercek_api_egitim_verisi_ai.jsonl")
HEDEF_VERI_SAYISI = 5000
BEKLEME_SURESI = 0.5

# Dosya Yolları
VERI_DOSYASI_PATH = os.path.join(BASE_DIR, "Veri.xlsx")
VERIM_DOSYASI_PATH = os.path.join(BASE_DIR, "verimler.xls")
GRID_DOSYASI_PATH = os.path.join(BASE_DIR, "grid_urfa_genis.csv")


# --- TARIM KÜTÜPHANESİ ---
class TarimBilgiBankasi:
    def __init__(self, veri_path, verim_path):
        self.veri_df = self._dosya_oku_robust(veri_path)
        self.verim_df = self._dosya_oku_robust(verim_path, header=None)  # Hiyerarşik okuma için header yok
        self.bitki_bilgileri = {}
        self.gecmis_verimler = {}
        self._verileri_islee()
        self._verimleri_isle()

    def _dosya_oku_robust(self, path, header=0):
        if not os.path.exists(path):
            print(f"HATA: '{path}' dosyası bulunamadı!")
            sys.exit(1)
        _, ext = os.path.splitext(path)
        try:
            if ext.lower() in ['.xls', '.xlsx']:
                return pd.read_excel(path, header=header)
            return pd.read_csv(path, sep=None, engine='python', header=header)
        except Exception as e:
            print(f"Dosya okuma hatası ({path}): {e}")
            sys.exit(1)

    def _temizle_sayisal_aralik(self, deger):
        if pd.isna(deger) or str(deger).strip() == "": return None
        deger = str(deger).strip().replace(" mm", "").replace(" C", "")
        aralik_match = re.match(r"(\d+)-(\d+)", deger)
        if aralik_match: return {"min": float(aralik_match.group(1)), "max": float(aralik_match.group(2))}
        sayi_match = re.match(r"(\d+)", deger)
        if sayi_match: return {"min": float(sayi_match.group(1)), "max": float(sayi_match.group(1))}
        return deger

    def _verileri_islee(self):
        parametreler = self.veri_df.iloc[:, 0].fillna("Bilinmiyor").tolist()
        bitki_isimleri = self.veri_df.columns[1:]

        for bitki in bitki_isimleri:
            bilgiler = {}
            col_data = self.veri_df[bitki].tolist()
            for i, param in enumerate(parametreler):
                if i >= len(col_data): break

                raw_val = col_data[i]
                clean_val = self._temizle_sayisal_aralik(raw_val)
                key = str(param).strip().lower()

                if "ideal sıcaklık" in key:
                    key = "ideal_sicaklik"
                elif "ekim yapılan gün" in key:
                    key = "ekim_zamani"
                elif "ürün miktarı" in key:
                    key = "tohum_miktari"
                elif "yağış miktarı" in key:
                    key = "yagis_ihtiyaci"

                if clean_val: bilgiler[key] = clean_val

            ana_isim = bitki.split("-")[0].strip() if "-" in str(bitki) else str(bitki).strip()
            bilgiler["tam_isim"] = bitki
            bilgiler["tur"] = ana_isim
            self.bitki_bilgileri[bitki] = bilgiler

    def _verimleri_isle(self):
        # Düzeltilmiş Hiyerarşik Okuma Mantığı
        print("Geçmiş verim verileri işleniyor...")
        current_urun = None

        for index, row in self.verim_df.iterrows():
            row_values = [str(x).strip() for x in row.values]
            full_row_str = " ".join(row_values)

            # Ürün Adı Bul
            if "Kg/Dekar" in full_row_str:
                match = re.search(r"\((.*?)\)", full_row_str)
                if match:
                    raw_name = match.group(1).split("(")[0].strip()
                    current_urun = raw_name
                else:
                    current_urun = full_row_str.split("-")[0].strip()[:30]

                if current_urun and current_urun not in self.gecmis_verimler:
                    self.gecmis_verimler[current_urun] = {}

            # Veri Bul
            if current_urun:
                yil = None
                verim = None
                for cell in row_values:
                    try:
                        val = float(cell)
                        if 2010 < val < 2030 and val.is_integer():
                            yil = int(val)
                        elif val > 0 and val != yil:
                            verim = val
                    except:
                        continue

                if yil and verim:
                    self.gecmis_verimler[current_urun][yil] = verim

    def bitki_getir_random(self):
        return self.bitki_bilgileri[random.choice(list(self.bitki_bilgileri.keys()))]


# --- HELPER FONKSİYONLAR ---
def get_historical_weather(lat, lon, date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": date_str, "end_date": date_str,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            d = r.json().get("daily", {})
            if d.get("temperature_2m_max"):
                mx = d["temperature_2m_max"][0]
                mn = d["temperature_2m_min"][0]
                rain = d["precipitation_sum"][0]
                avg = (mx + mn) / 2
                return {"temp": round(avg, 1), "rain": rain, "max": mx, "min": mn}
    except Exception:
        pass
    return None


# --- AI GENERATOR ---
def generate_ai_response(soru, weather, target_date, bitki_bilgisi, gecmis_verimler):
    gecmis_text = ""
    if gecmis_verimler:
        gecmis_text = "BÖLGE GEÇMİŞ YIL VERİMLERİ (REFERANS):\n"
        sirali_yillar = sorted(gecmis_verimler.keys())
        for yil in sirali_yillar:
            gecmis_text += f"- {yil}: {gecmis_verimler[yil]} kg/dekar\n"
        gecmis_text += "(Bu verileri kullanarak kıyaslama yap.)"
    else:
        gecmis_text = "Bu ürün için spesifik geçmiş yıl verisi bulunamadı."

    realtime_info = (
        f"Sıcaklık: {weather['temp']}°C (Min: {weather['min']} - Max: {weather['max']}), "
        f"Yağış: {weather['rain']}mm. "
        f"Toprak: {'Çamurlu' if weather['rain'] > 10 else 'Uygun'}. "
        f"İdeal Sıcaklık: {bitki_bilgisi.get('ideal_sicaklik', 'Bilinmiyor')}"
    )

    current_date_str = target_date.strftime("%Y-%m-%d")

    system_prompt = f"""
### 1. KİMLİK ###
Sen Urfa bölgesini bilen 'Çiftçi AI'sın.

### 2. VERİLER ###
[TARİH]: {current_date_str}
[DURUM]: {realtime_info}
{gecmis_text}

### 3. GÖREV ###
Çiftçinin sorusunu cevapla.
1. "Uygun/Değil" kararını ver ve nedenini açıkla.
2. Geçmiş yıllardaki verim verilerine (varsa) atıfta bulunarak kıyasla.
3. Çiftçi diliyle samimi konuş.

### 4. FORMAT ###
Markdown kullan. Eğer ekim/ilaçlama uygunsa cevabın sonuna şunu ekle:
[GÖREV: <Eylem> | <Detay> | YYYY-MM-DD HH:MM]
"""

    try:
        response = client.chat.completions.create(
            model="glm-4.6v-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": soru}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Hatası: {e}")
        return None


def main():
    print("Veritabanı yükleniyor...")
    if not os.path.exists(VERI_DOSYASI_PATH):
        print(f"Dosya yok: {VERI_DOSYASI_PATH}");
        return

    if not os.path.exists(GRID_DOSYASI_PATH):
        grid_df = pd.DataFrame({'lat': [37.15], 'lon': [38.80]})
    else:
        grid_df = pd.read_csv(GRID_DOSYASI_PATH)

    db = TarimBilgiBankasi(VERI_DOSYASI_PATH, VERIM_DOSYASI_PATH)

    # --- DEVAM ETME MANTIĞI (RESUME LOGIC) ---
    mevcut_satir_sayisi = 0
    if os.path.exists(CIKTI_DOSYASI):
        print(f"Mevcut dosya kontrol ediliyor: {CIKTI_DOSYASI}")
        with open(CIKTI_DOSYASI, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():  # Boş satırları sayma
                    mevcut_satir_sayisi += 1
        print(f"⚠️ Dosyada zaten {mevcut_satir_sayisi} satır veri var. Kaldığı yerden devam edilecek.")

    if mevcut_satir_sayisi >= HEDEF_VERI_SAYISI:
        print(f"Hedeflenen veri sayısına ({HEDEF_VERI_SAYISI}) zaten ulaşılmış. İşlem yapılmayacak.")
        return

    print(f"Veri Üretimi Başlıyor... Hedef: {HEDEF_VERI_SAYISI} (Kalan: {HEDEF_VERI_SAYISI - mevcut_satir_sayisi})")

    # "a" (append) modu ile açıyoruz, üzerine eklemesi için.
    with open(CIKTI_DOSYASI, "a", encoding="utf-8") as f:
        count = mevcut_satir_sayisi

        while count < HEDEF_VERI_SAYISI:
            try:
                # 1. Veri Hazırlığı
                row = grid_df.sample(1).iloc[0]
                lat, lon = row["lat"], row["lon"]

                days_diff = (datetime.date(2024, 12, 1) - datetime.date(2020, 1, 1)).days
                target_date = datetime.date(2020, 1, 1) + datetime.timedelta(days=random.randrange(days_diff))

                weather = get_historical_weather(lat, lon, target_date)
                if not weather:
                    time.sleep(0.5)
                    continue

                bitki_bilgisi = db.bitki_getir_random()
                bitki_tur = bitki_bilgisi["tur"]
                bitki_adi = bitki_bilgisi["tam_isim"]

                # 2. Geçmiş Veri
                gecmis_data = {}
                for k, v in db.gecmis_verimler.items():
                    if bitki_tur.lower() in k.lower() or k.lower() in bitki_tur.lower():
                        gecmis_data = v
                        break

                # 3. Soru ve Cevap
                adres = "Şanlıurfa"
                soru = f"{adres} konumunda tarlam var. Tarih {target_date.strftime('%d.%m.%Y')}. Geçen günlerde hava ortalama {weather['temp']}°C idi ve {weather['rain']}mm yağış düştü. {bitki_adi} ekimi için şartlar nasıldı?"

                # Ekrana basarken hangi satırda olduğumuzu göster
                print(f"[{count + 1}/{HEDEF_VERI_SAYISI}] Üretiliyor: {bitki_adi} - {target_date}...")

                ai_cevap = generate_ai_response(soru, weather, target_date, bitki_bilgisi, gecmis_data)

                if ai_cevap:
                    veri_satiri = {
                        "instruction": soru,
                        "input": f"Lokasyon: {lat},{lon} ({adres}) | Tarih: {target_date} | Veri: Temp={weather['temp']}C, Rain={weather['rain']}mm",
                        "output": ai_cevap
                    }
                    f.write(json.dumps(veri_satiri, ensure_ascii=False) + "\n")
                    # Dosyayı anında diske yazması için flush edelim (çökme durumuna karşı)
                    f.flush()
                    count += 1

                time.sleep(BEKLEME_SURESI)

            except Exception as e:
                print(f"Döngü hatası: {e}")
                continue

    print(f"✅ İŞLEM TAMAMLANDI! Toplam {count} satır veri hazır: {CIKTI_DOSYASI}")


if __name__ == "__main__":
    main()
