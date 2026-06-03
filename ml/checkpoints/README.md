# Checkpoint

`best.pt` dosyasını buraya koyun, ardından commit edin:

```bash
git add ml/checkpoints/best.pt
git commit -m "chore: add plant disease CNN checkpoint"
```

Eğitim: `python ml/train.py` (çıktı varsayılan olarak bu klasördedir).

GGUF sohbet modeli repoda değildir (`models/*.gguf` — sunucuda `/opt/CiftciApp/models/`).
