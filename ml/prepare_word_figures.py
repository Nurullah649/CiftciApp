"""Ara rapor Word dosyasina konacak sekilleri numarali dosya adlariyla hazirlar."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ml" / "report" / "word_sekiller"
DOCX = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
REPORT = ROOT / "ml" / "report"

# (dosya_adi, kaynak, word_sekil_no, bolum)
FIGURES: list[tuple[str, Path, str, str]] = [
    (
        "Sekil_01_PlantVillage_veri_seti_dagilimi.png",
        ROOT / "ml" / "class_distribution.png",
        "Sekil 1",
        "3.2.1 PlantVillage",
    ),
    (
        "Sekil_02_Hibrit_veri_seti_dagilimi.png",
        ROOT / "ml" / "class_distribution_hybrid.png",
        "Sekil 2",
        "3.2.2 Hibrit veri seti",
    ),
    (
        "Sekil_07_karmasiklik_matrisi.png",
        REPORT / "confusion_test.png",
        "Sekil 7",
        "3.6 — test karmaşıklık matrisi (TEK sayfa)",
    ),
    (
        "Sekil_08_sinif_F1_skorlari.png",
        REPORT / "per_class_f1.png",
        "Sekil 8",
        "3.6 — sınıf bazında F1 (TEK sayfa)",
    ),
    (
        "Sekil_09_guven_dagilimi.png",
        REPORT / "confidence_hist.png",
        "Sekil 9",
        "3.6 — güven skoru dağılımı (TEK sayfa)",
    ),
    (
        "Sekil_10_saglikli_vs_hastalik_guven.png",
        REPORT / "healthy_vs_disease_conf.png",
        "Sekil 10",
        "3.6 — sağlıklı vs hastalık (TEK sayfa)",
    ),
    (
        "Sekil_11_guven_esigi_taramasi.png",
        REPORT / "threshold_sweep.png",
        "Sekil 11",
        "3.6 — eşik taraması (TEK sayfa)",
    ),
    (
        "Sekil_12_sinif_kabul_orani.png",
        REPORT / "gate_acceptance_by_class.png",
        "Sekil 12",
        "3.6 — sınıf kabul oranı (TEK sayfa)",
    ),
]

OPTIONAL = [
    (
        "OPSIYONEL_Sekil_01_02_BIRLESIK_veri_seti_tek_sayfa.png",
        ROOT / "ml" / "class_distribution_combined_page.png",
        "Sekil 1+2 yerine tek sayfa",
    ),
    (
        "EKSTRA_margin_dagilimi.png",
        REPORT / "margin_hist.png",
        "Rapora zorunlu degil — referans",
    ),
]

DOCX_MOBILE = [
    ("Sekil_03_mobil_foto_secimi_ve_ipuclari.jpeg", "word/media/image3.jpeg"),
    ("Sekil_04_mobil_sonuc_karti_tani_guven.jpeg", "word/media/image4.jpeg"),
    ("Sekil_05_mobil_dusuk_guven_reddedildi.jpeg", "word/media/image5.jpeg"),
    ("Sekil_06_mobil_etken_madde_BKU_MRL.jpeg", "word/media/image6.jpeg"),
]


def copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.is_file():
        print(f"[ATLA] Kaynak yok: {src}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[OK] {dst.name}")
    return True


def extract_mobile_from_docx() -> None:
    if not DOCX.is_file():
        print(f"[UYARI] Word dosyasi bulunamadi: {DOCX}")
        return
    with zipfile.ZipFile(DOCX) as z:
        for out_name, inner in DOCX_MOBILE:
            if inner not in z.namelist():
                print(f"[ATLA] Docx icinde yok: {inner}")
                continue
            (OUT / out_name).write_bytes(z.read(inner))
            print(f"[OK] {out_name} (Word'den)")


def write_index() -> None:
    lines = [
        "CIFTCIAPP ARA RAPOR — SEKIL DOSYALARI (12 adet)",
        "=" * 55,
        "",
        "Klasor: ml/report/word_sekiller/",
        "Her dosya Word'de AYRI bir sayfaya / sekil slotuna gider.",
        "",
        "SIRA | DOSYA | WORD BOLUMU",
        "-" * 55,
        " 1  | Sekil_01_PlantVillage_veri_seti_dagilimi.png     | 3.2.1",
        " 2  | Sekil_02_Hibrit_veri_seti_dagilimi.png           | 3.2.2",
        " 3  | Sekil_03_mobil_foto_secimi_ve_ipuclari.jpeg      | 3.4 mobil",
        " 4  | Sekil_04_mobil_sonuc_karti_tani_guven.jpeg       | analiz sonucu",
        " 5  | Sekil_05_mobil_dusuk_guven_reddedildi.jpeg       | dusuk guven",
        " 6  | Sekil_06_mobil_etken_madde_BKU_MRL.jpeg          | 3.5 BKÜ",
        " 7  | Sekil_07_karmasiklik_matrisi.png                 | 3.6 Tablo 1 sonrasi",
        " 8  | Sekil_08_sinif_F1_skorlari.png                   | 3.6",
        " 9  | Sekil_09_guven_dagilimi.png                      | 3.6",
        "10  | Sekil_10_saglikli_vs_hastalik_guven.png          | 3.6",
        "11  | Sekil_11_guven_esigi_taramasi.png                | 3.6",
        "12  | Sekil_12_sinif_kabul_orani.png                   | 3.6",
        "",
        "NOT: Sekil_07 ve sonrasi TEKER TEK, birlesik degil.",
        "Word'de birlesik eski dosyalari (Sekil_07_model_performans_birlesik...)",
        "varsa silip yukaridaki 7-12 ayri dosyalari kullan.",
        "",
        "Yeniden uret:",
        "  .\\venv-ml\\Scripts\\Activate.ps1",
        "  python ml/evaluate_report.py",
        "  python ml/prepare_word_figures.py",
    ]
    (OUT / "SEKIL_LISTESI.txt").write_text("\n".join(lines), encoding="utf-8")
    print("[OK] SEKIL_LISTESI.txt")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for name, src, _no, _section in FIGURES:
        copy_if_exists(src, OUT / name)

    for name, src, note in OPTIONAL:
        if copy_if_exists(src, OUT / name):
            print(f"       -> {note}")

    extract_mobile_from_docx()
    write_index()
    print(f"\nHazir: {OUT}")


if __name__ == "__main__":
    main()
