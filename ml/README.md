# Bitki Hastalık Tespiti — ML Pipeline

Bu klasör, Çiftçi AI uygulamasındaki **bitki hastalık tespit modelinin** eğitimi için gerekli tüm araçları içerir.

> Hedef: PlantVillage dataset (38 sınıf) üzerinde **MobileNetV2 transfer learning** ile bir sınıflandırıcı eğitmek, en iyi checkpoint'i (`best.pt`) backend'e koyup `/tools/analyze-plant` endpoint'i üzerinden mobil uygulamaya sunmak.

---

## Klasör Yapısı

```
ml/
├── README.md                  # Bu dosya
├── requirements-ml.txt        # Eğitim için Python bağımlılıkları
├── class_labels.json          # 38 sınıf → Türkçe ad + tedavi önerisi
│
├── download_dataset.py        # HuggingFace'ten PlantVillage indir (38 sınıf)
├── verify_dataset.py          # İndirilen dataset'i doğrula
├── prepare_dataset.py         # train/val/test split (leaf-aware destekli)
├── train.py                   # Transfer learning eğitimi (2 aşama)
├── evaluate.py                # Test seti üzerinde metrikler + confusion matrix
├── inference_test.py          # Tek görsel üzerinde tahmin
│
├── data/                      # (gitignore) Dataset dosyaları
│   ├── raw/                   # download_dataset.py çıktısı: ham görseller
│   └── splits/                # prepare_dataset.py çıktısı (train/val/test)
│
└── checkpoints/               # (gitignore) Eğitim çıktıları
    ├── best.pt                # En iyi val_acc'lı model — backend bunu kullanır
    ├── last.pt
    ├── history.json
    ├── confusion_val.png
    ├── confusion_test.png
    └── test_report.json
```

---

## Hızlı Başlangıç (Lokal GPU — Windows / PowerShell)

### 1. Ortam kur

Projenin ana `venv`'ini kullanıyorsan eğitim bağımlılıklarını ayrı kurmanı öneririm — torch kocaman bir paket ve production backend'ini şişirir.

```powershell
# Proje kökünden çalıştır
cd C:\Users\agdbe\Desktop\CiftciApp

# Eğitime özel ayrı sanal ortam (önerilir)
python -m venv venv-ml
.\venv-ml\Scripts\Activate.ps1

# CUDA 12.1 için PyTorch (NVIDIA GPU'n varsa)
pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121

# Geri kalan paketler
pip install -r ml\requirements-ml.txt
```

**GPU kontrolü:**
```powershell
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| Cihaz:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'YOK')"
```
Çıktıda `CUDA: True` görmen lazım. Görmüyorsan NVIDIA driver + CUDA Toolkit uyumunu kontrol et.

### 2. Dataset'i indir (HuggingFace — önerilen)

`download_dataset.py` orijinal Mohanty et al. 2016 dataset'ini HuggingFace'ten otomatik indirir, `leaf_id` bilgisini dosya adında saklar (`<leaf_id>__<idx>.jpg`).

```powershell
# Tüm 38 sınıfı indir (~2.2 GB, ~54.000 görsel)
python ml\download_dataset.py
```

İlk indirme sırasında HuggingFace 2.2 GB önbelleğe alır, sonra `ml/data/raw/` altına ImageFolder formatında yazar:

```
ml/data/raw/
├── Apple___Apple_scab/
│   ├── 0a76__000000.jpg     # 0a76 = leaf_id
│   ├── 0a76__000001.jpg
│   └── ...
├── ... (38 klasör)
└── Tomato___healthy/
```

**Sadece eksik sınıfları indirmek için** (`raw/`'da bazı sınıflar zaten varsa):
```powershell
python ml\download_dataset.py --only-missing
```

**Belirli sınıfları indirmek için:**
```powershell
python ml\download_dataset.py --classes Tomato___Late_blight Potato___Early_blight
```

> Kaggle alternatifi: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset
> Manuel indirip `ml/data/raw/` altına koyman da yeterli — bu durumda `leaf_aware` çalışmaz, klasik random split yapılır.

### 3. (İsteğe bağlı) Doğrulama

```powershell
python ml\verify_dataset.py ml\data\raw
```

38 sınıf, sınıf başına ~200-5000 görsel, toplam ~54.000 görmen lazım.

### 4. Train/val/test böl

```powershell
# Leaf-aware split (HuggingFace ile indirildiyse ÖNERİLİR — data leakage'ı önler)
python ml\prepare_dataset.py --leaf-aware --clean
```

`--leaf-aware`: Aynı yaprağın farklı açılardan çekilmiş görselleri **tek bir split**'e yerleşir.
Bu, Mohanty et al. 2016'da vurgulanan kritik bir noktadır — aksi halde val/test
accuracy yapay olarak yüksek görünür (görmediği yaprak değil, gördüğü yaprağın
yakın komşusunu tanır).

Varsayılan: **%70 train / %15 val / %15 test**, seed=42 (tekrar üretilebilir).

Beklenen çıktı:
```
[INFO] 38 sınıf işlenecek
[INFO] Mod: symlink  |  Split: leaf-aware (gruplu)  |  Oranlar: train=0.7, val=0.15, test=0.15
  ( 1/38) Apple___Apple_scab: train=441 val=94 test=95
  ...
============================================================
TAMAMLANDI
  Train: ~37.800
  Val  : ~8.100
  Test : ~8.100
  Toplam: ~54.000
```

**Windows'ta sembolik link hatası alırsan:** Geliştirici modunu aç (Settings → For Developers → Developer Mode), ya da `--mode copy` ile kopyalama yap (~1.5 GB ekstra alan kullanır).

### 5. Eğitim

```powershell
# Varsayılan: 3 epoch head + 7 epoch fine-tune, batch=64, class_weights=sqrt
python ml\train.py
```

Süre tahmini (RTX 3060 / 6GB VRAM):
- Head: ~3-4 dk/epoch × 3 = **~12 dk**
- Fine-tune: ~5-6 dk/epoch × 7 = **~40 dk**
- **Toplam: ~50-60 dk**, val_acc beklentisi **%96-99**.

VRAM yetmezse:
```powershell
python ml\train.py --batch-size 32
```

Daha uzun süre eğitim:
```powershell
python ml\train.py --epochs-head 5 --epochs-finetune 12 --batch-size 96
```

Çıktılar `ml/checkpoints/` altında oluşur. Eğitim sırasında her epoch sonunda en iyi val_acc'ı geçen ağırlıklar `best.pt`'ye yazılır.

#### Dengesiz sınıflar (class imbalance)

PlantVillage'da en az örnekli sınıf `Potato___healthy` (152 görsel, train'de 108), en kalabalık `Orange___Haunglongbing` (5507 görsel). Bu **~50x** dengesizliği nedeniyle modelin az örnekli sınıfları "es geçmesi" riski var.

`train.py` 3 farklı şema sunar (varsayılan: `sqrt`):

| `--class-weights` | Formül | Ne zaman |
|---|---|---|
| `none` | Yok | Sınıflar dengeli — bizim için uygun değil |
| `inverse` | `N / (K * n_c)` | Çok agresif düzeltme — az örnekli sınıfa fazla bias verir |
| **`sqrt`** | `√(N / n_c)` | **Önerilen** — yumuşak düzeltme, çoğunluk sınıfını bozmaz |
| `effective` | Cui et al. 2019, β=0.9999 | Modern alternatif — `sqrt`'a yakın sonuç |

Alternatif: `--sampling weighted` ile **WeightedRandomSampler** kullanılır (az örnekli sınıfı her epoch'ta daha sık görür). Class weights ile birlikte kullanma — biri yeterli.

```powershell
# Sadece weighted sampling (loss ağırlığı yok)
python ml\train.py --class-weights none --sampling weighted

# Sadece class weights (varsayılan)
python ml\train.py --class-weights sqrt

# Çok dengesiz sınıflar için agresif düzeltme
python ml\train.py --class-weights effective
```

### 6. Test seti üzerinde değerlendir

```powershell
python ml\evaluate.py
```

Çıktı:
```
=== Test Sonuçları (8129 görsel) ===
  Top-1 Accuracy: 0.9871
  Top-3 Accuracy: 0.9994

Sınıf bazında rapor:
                                              precision    recall  f1-score
Apple___Apple_scab                                0.984     0.978     0.981
...
```

`confusion_test.png` ve `test_report.json` de oluşur — bitirme raporunda kullanabilirsin.

### 7. Tek görselle hızlı test

```powershell
python ml\inference_test.py "C:\path\to\hasta_yaprak.jpg"
```

Çıktı:
```
=== Tahmin: hasta_yaprak.jpg ===
  1. [ 97.42%]  Domates — Erken Yaprak Yanıklığı (Alternaria)  (warning)
      Öneri: Alt yaprakları temizleyin, malçlama yapın. Chlorothalonil veya azoksistrobin uygulayın...
  2. [  1.86%]  Domates — Septoria Yaprak Lekesi  (warning)
  3. [  0.42%]  Domates — Hedef Leke (Corynespora)  (warning)
```

---

## Sonraki Adım (Backend Entegrasyonu)

`best.pt` hazır olunca:

1. `ml/checkpoints/best.pt` → projedeki `models/` klasörüne kopyalanacak (`models/plant_disease_mobilenetv2.pt`).
2. `ml/class_labels.json` → backend'in okuyabileceği bir yere taşınacak.
3. `app/services/plant_disease_service.py` oluşturulacak (model yükle + predict).
4. `app/routers/tools.py` içine `POST /tools/analyze-plant` eklenecek (multipart upload).
5. `requirements.txt` + `Dockerfile` güncellenecek (torch CPU + pillow).
6. Docker build + deploy, mobilde test.

Bu paketi **eğitim bittikten sonra** ben üreteceğim. Bana val_acc çıktısını gösterdiğinde "backend tarafına geç" dersen, geri kalanı da yaparım.

---

## Sorun Giderme

| Hata | Çözüm |
|---|---|
| `RuntimeError: CUDA out of memory` | `--batch-size 32` veya `16` ile dene |
| `OSError: [WinError 1314]` (symlink) | Win Geliştirici Modu aç ya da `--mode copy` |
| `ImportError: libcudart.so` | torch CUDA versiyonu CUDA driver ile uyuşmuyor — `pip install torch ... --index-url ...cu121` ile yeniden kur |
| `num_workers=4` çok yavaş başlatıyor | Windows'ta `--num-workers 0` ya da `2` |
| val_acc düşük (<%90) | Daha uzun eğitim (`--epochs-finetune 15`), öğrenme oranı düşür (`--lr-finetune 5e-5`), aug daha az agresif |

---

## Performans Hedefi

| Metrik | Hedef | Notlar |
|---|---|---|
| Test Top-1 | ≥ %97 | Literatür PlantVillage için %98+ raporluyor |
| Test Top-3 | ≥ %99.5 | |
| Model boyutu | < 20 MB | MobileNetV2 ~9 MB FP32, INT8 quantize edersek ~3 MB |
| CPU inference (backend) | < 500 ms | 224×224 görsel, single image |

---

## Lisans Notu

PlantVillage dataset CC BY 4.0 ile lisanslanmış — akademik kullanım serbest, kaynak göster yeterli. Bitirme raporuna referans olarak:

> Hughes, D., & Salathé, M. (2015). *An open access repository of images on plant health to enable the development of mobile disease diagnostics.* arXiv:1511.08060.
