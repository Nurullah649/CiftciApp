"""ml/treatment_active_ingredients.json üretir — bir kerelik."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ingredients_for(key: str) -> list:
    k = key.lower()
    if "healthy" in k or k.endswith("___healthy"):
        return []
    if "virus" in k or "mosaic" in k or "yellow_leaf_curl" in k or "tylcv" in k:
        return [
            {
                "name": "Doğrudan antiviral bitki koruma ürünü yoktur",
                "role": "Önlem odaklı",
                "notes": "Vektör ve kültürel önlemler önemlidir; etken madde hastalığı iyileştirmez.",
            }
        ]
    if "bacterial" in k:
        return [
            {
                "name": "Bakır bileşikleri (ör. bakır oksiklorür)",
                "role": "Koruyucu / bakteri baskılama",
                "notes": "Etiket dozu ve güvenlik aralığına uyun; yağmurlama sulama yapmayın.",
            },
            {
                "name": "Mancozeb (destekleyici)",
                "role": "Karma preparatlarda sık görülür",
                "notes": "Üretici etiketinde hastalığa onaylı kombinasyonları tercih edin.",
            },
        ]
    if "mite" in k or "spider" in k or "aculus" in k:
        return [
            {
                "name": "Abamektin",
                "role": "Akarisit",
                "notes": "Doğal düşmanları koruyun; dönüşümlü aktif kullanın.",
            },
            {
                "name": "Kükürt",
                "role": "Kontakt akarisit",
                "notes": "Sıcak havalarda yanık riskine dikkat; etikete uyun.",
            },
        ]
    if "powdery" in k:
        return [
            {"name": "Kükürt", "role": "Kontakt fungisit", "notes": "Erken evrede etkilidir."},
            {
                "name": "Myclobutanil veya Tebukonazol",
                "role": "Triazol fungisit",
                "notes": "Direnç için tek başına sürekli kullanmayın.",
            },
        ]
    if "late_blight" in k:
        return [
            {
                "name": "Metalaksil + Mancozeb (kombine)",
                "role": "Sistemik + koruyucu",
                "notes": "Mildiyöde etiket onaylı kombinasyonları kullanın.",
            },
            {
                "name": "Cimoksanil içerikli preparatlar",
                "role": "Anti-sporulant etki",
                "notes": "Erken müdahale; sık tekrar gerekebilir.",
            },
        ]
    if "rust" in k:
        return [
            {"name": "Propikonazol", "role": "Triazol fungisit", "notes": "Pas için yaygın grup."},
            {"name": "Mancozeb", "role": "Koruyucu", "notes": "Programda rotasyonlu kullanın."},
        ]
    if "cercospora" in k or "gray_leaf" in k:
        return [
            {
                "name": "Azoksistrobin veya Piraklostrobin",
                "role": "Strobilurin",
                "notes": "FRAC rotasyonu yapın.",
            },
            {"name": "Propikonazol", "role": "Triazol", "notes": "Mısır için etiket onayı kontrol edin."},
        ]
    if "northern_leaf_blight" in k:
        return [
            {
                "name": "Azoksistrobin + Propikonazol (kombine)",
                "role": "Geniş spektrum",
                "notes": "Şiddetli enfeksiyonda erken uygulama.",
            },
            {"name": "Mancozeb", "role": "Koruyucu", "notes": "Program başında veya destek olarak."},
        ]
    if "esca" in k:
        return [
            {
                "name": "Kimyasal tedavi sınırlıdır",
                "role": "Kültürel öncelik",
                "notes": "Enfekte kolları kesip macunlama; profesyonel bağ gözetimi önerilir.",
            }
        ]
    if "grape" in k:
        return [
            {"name": "Mancozeb", "role": "Koruyucu fungisit", "notes": "Üzüm için etiket dozuna uyun."},
            {"name": "Myclobutanil", "role": "Triazol", "notes": "Risk döneminde program parçası olabilir."},
        ]
    if "orange" in k or "haunglongbing" in k or "greening" in k:
        return [
            {
                "name": "İmidakloprid veya etikette önerilen neonikotinoid",
                "role": "Psillid (vektör) mücadelesi",
                "notes": "Ağaçta doğrudan ilaç tedavisi yoktur; vektör ve sertifikalı materyal kritiktir.",
            },
            {
                "name": "Yayılım kontrolü (söküm / karantina)",
                "role": "Mevzuatsal / kültürel",
                "notes": "Bölgesel kurallara uygun hareket edin.",
            },
        ]
    if "peacock" in k:
        return [
            {
                "name": "Bakır bileşikleri",
                "role": "Koruyucu fungisit",
                "notes": "Sonbahar ve ilkbahar koruyucu program.",
            },
            {"name": "Bordo bulamacı", "role": "Koruyucu", "notes": "Onaylı kullanım ve çevresel duyarlılık."},
        ]
    if "leaf_mold" in k:
        return [
            {"name": "Clorotalonil", "role": "Koruyucu fungisit", "notes": "Serada nem kontrolü ile birlikte."},
            {"name": "Azoksistrobin", "role": "Strobilurin", "notes": "Etiket onayına göre domates için."},
        ]
    if "target_spot" in k:
        return [
            {"name": "Mancozeb", "role": "Koruyucu", "notes": "Erken müdahale."},
            {"name": "Difenokonazol", "role": "Triazol", "notes": "Dönüşümlü kullanın."},
        ]
    if "septoria" in k:
        return [
            {"name": "Clorotalonil", "role": "Koruyucu", "notes": "7-10 gün aralıklı program."},
            {"name": "Mancozeb", "role": "Koruyucu", "notes": "Yaprağın kuru kalmasıyla destekleyin."},
        ]
    if "early_blight" in k:
        return [
            {"name": "Clorotalonil", "role": "Koruyucu fungisit", "notes": "Alternaria için sık kullanılır."},
            {"name": "Azoksistrobin", "role": "Strobilurin", "notes": "Direnç yönetimi için rotasyon şart."},
        ]
    if "scab" in k and "apple" in k:
        return [
            {"name": "Mancozeb", "role": "Koruyucu", "notes": "Çiçeklenme öncesi koruyucu program."},
            {"name": "Myclobutanil", "role": "Triazol", "notes": "Risk döneminde etiket programına göre."},
        ]
    if "cedar" in k and "rust" in k:
        return [
            {"name": "Myclobutanil", "role": "Triazol", "notes": "Pas için sistemik seçenek."},
            {"name": "Mancozeb", "role": "Koruyucu", "notes": "Tekrarlayan uygulamalarda rotasyon."},
        ]
    if "black_rot" in k and "apple" in k:
        return [
            {"name": "Captan", "role": "Koruyucu fungisit", "notes": "Meyve dönemi etiket programı."},
            {
                "name": "Tiyofanat-metil",
                "role": "Benzoimidazol grubu",
                "notes": "Elma için onaylı preparat kullanın.",
            },
        ]
    if "strawberry" in k and "scorch" in k:
        return [
            {"name": "Captan", "role": "Koruyucu", "notes": "Çilek için etiket onayı kontrol edin."},
            {"name": "Myclobutanil", "role": "Triazol", "notes": "Rotasyonlu program."},
        ]
    return [
        {"name": "Mancozeb", "role": "Koruyucu fungisit", "notes": "Etiket bitki/hastalık eşleşmesini doğrulayın."},
        {
            "name": "Azoksistrobin veya benzeri strobilurin",
            "role": "Geniş spektrum",
            "notes": "FRAC rotasyonu ile kullanın.",
        },
    ]


def main() -> None:
    labels = json.loads((ROOT / "ml/class_labels.json").read_text(encoding="utf-8"))
    classes = sorted(labels["classes"].keys())
    disclaimer = (
        "Bu liste genel bilgilendirme amaçlıdır; ticari ürün adı önerilmez. "
        "Türkiye'de kayıtlı bitki koruma ürününü, ürün etiketi ve ziraat mühendisi kontrolünde kullanın. "
        "Doz, güvenlik aralığı ve çevre uyarılarına mutlaka uyun."
    )
    out = {"_meta": {"disclaimer_tr": disclaimer}, "by_class": {c: ingredients_for(c) for c in classes}}
    path = ROOT / "ml/treatment_active_ingredients.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> {path} ({len(classes)} sınıf)")


if __name__ == "__main__":
    main()
