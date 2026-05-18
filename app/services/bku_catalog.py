"""
BKÜ (bku.tarimorman.gov.tr) — kullanıcı arama modüllerine karşılık gelen autocomplete uçları.

Notlar:
- Bazı tam liste sayfaları (ör. /Zararli/Index) oturum gerektirebilir; aşağıdaki uçlar
  tarayıcıda giriş yapılmadan kullanılabilen indeks sayfalarından türetilmiştir.
- Genel arama motoru çoklu kayıt tipini (bitki, zararlı, aktif madde, MRL, entegre vb.)
  tek autocomplete içinde döndürür; istemci tarafında Name/text önekine göre süzebilirsiniz.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

ParamStyle = Literal["query", "select2_id"]


@dataclass(frozen=True)
class BkuAutocompleteEndpoint:
    """BKÜ'deki Select2 / Typeahead JSON uçları."""

    slug: str
    title_tr: str
    description_tr: str
    covers_user_topics_tr: List[str]
    autocomplete_path: str
    referer_path: str
    param_style: ParamStyle
    related_datatable_post: Optional[str]
    official_page_path: str


BKU_AUTOCOMPLETE_ENDPOINTS: List[BkuAutocompleteEndpoint] = [
    BkuAutocompleteEndpoint(
        slug="genel_arama_motoru",
        title_tr="Yeni Arama Motoru (genel)",
        description_tr=(
            "T.C. Arama Motoru — tek kutuda birden çok konu tipi (BKÜ kayıt kartına giden öneriler)."
        ),
        covers_user_topics_tr=[
            "Ruhsatlı Bitki Koruma Ürünü / Formülasyon / Aktif madde (öneri listesi)",
            "Zararlı organizma adı ve latince ad içeren sonuçlar",
            "Bitki adı",
            "MRL ile ilişkili ürün/kayıt önerileri",
            "Entegre Mücadele Teknik Talimat satırları",
            "Aktif madde",
            "Formülasyon",
            "Geçici tavsiye ile ilişkili çapraz kayıtlar (öneri metninde geçebilir)",
        ],
        autocomplete_path="/Tamamla/GenelAramaKelimesiGetir5",
        referer_path="/Arama/Index",
        param_style="query",
        related_datatable_post="/Arama/Index",
        official_page_path="/Arama/Index",
    ),
    BkuAutocompleteEndpoint(
        slug="ruhsatli_bku_indeks",
        title_tr="Ruhsatlı Bitki Koruma Ürünleri — detaylı indeks",
        description_tr=(
            "Ruhsatlı ürün grid filtresi — ürün adı, formulasyon ve aktif madde araması aynı çoklu seçim kutusunda."
        ),
        covers_user_topics_tr=[
            "Ruhsatlı Bitki Koruma Ürün bilgileri — Bitki Koruma Ürünü Adı",
            "Ruhsatlı Bitki Koruma Ürün bilgileri — Formülasyon Adı",
            "Ruhsatlı Bitki Koruma Ürün bilgileri — Aktif Madde Adı",
        ],
        autocomplete_path="/BKURuhsat/IndeksSelect2ListesiGetir",
        referer_path="/BKURuhsat/Index",
        param_style="select2_id",
        related_datatable_post="/BKURuhsat/RuhsatIndeksGetir",
        official_page_path="/BKURuhsat/Index",
    ),
    BkuAutocompleteEndpoint(
        slug="mrl_orani_indeks_secim",
        title_tr="MRL Oranları — indeks çoklu seçim",
        description_tr=("MRL Oranları sayfasındaki çoklu seçim kutusu (bitki + MRL aktif madde önerileri birlikte)."),
        covers_user_topics_tr=[
            "MRL Oran bilgilerine — Bitki Adı",
            "MRL Oran bilgilerine — MRL Aktif Madde Adı",
        ],
        autocomplete_path="/Tamamla/MrlOraniSecimListesiGetir",
        referer_path="/MRLOrani/Index",
        param_style="select2_id",
        related_datatable_post="/MrlOrani/MrlOranGetir",
        official_page_path="/MRLOrani/Index",
    ),
    BkuAutocompleteEndpoint(
        slug="gecici_tavsiye_alan_secim",
        title_tr="Geçici Tavsiye Alanları — indeks seçimi",
        description_tr=(
            "Geçici tavsiye alanı kayıtlarında bitki, zararlı (latince parantez içinde), aktif madde ve formulasyon kolonları için ortak çoklu seçim."
        ),
        covers_user_topics_tr=[
            "Geçici Tavsiye Alan ürün bilgileri — Bitki Adı",
            "Geçici Tavsiye Alan ürün bilgileri — Zararlı Adı",
            "Geçici Tavsiye Alan ürün bilgileri — Zararlı Latince Adı",
            "Geçici Tavsiye Alan ürün bilgileri — Aktif Madde Adı",
        ],
        autocomplete_path="/BKUGeciciTavsiyeAlanlar/Select2ListesiGetir",
        referer_path="/BKUGeciciTavsiyeAlanlar/GeciciTavsiyeIndeks",
        param_style="select2_id",
        related_datatable_post="/BKUGeciciTavsiyeAlanlar/DataTableGetir",
        official_page_path="/BKUGeciciTavsiyeAlanlar/GeciciTavsiyeIndeks",
    ),
    BkuAutocompleteEndpoint(
        slug="tavsiye_arama",
        title_tr="Tavsiye Arama",
        description_tr=(
            "Kayıtlı tavsiye çizelgesi için öneri listesi (bitki, zararlı, aktif madde, ruhsatlı BKÜ satırı bağlantıları)."
        ),
        covers_user_topics_tr=[
            "Ruhsatlı ürün ile bağlantılı tavsiye satırları",
            "Zararlı organizma",
            "Bitki adı",
            "Aktif madde",
            "Entegre kayıtları — gridde yıldız işareti ile ilişkilendirilir (sayfa: Tavsiye Arama)",
        ],
        autocomplete_path="/Kullanim/TavsiyeAramaKelimesiGetir3",
        referer_path="/Kullanim/TavsiyeArama",
        param_style="select2_id",
        related_datatable_post="/Kullanim/TavsiyeGetir",
        official_page_path="/Kullanim/TavsiyeArama",
    ),
    BkuAutocompleteEndpoint(
        slug="tavsiye_alternatif",
        title_tr="Tavsiye Alternatif",
        description_tr=("Alternatif mücadele / ürün önerileri tablosu için çoklu seçim önerileri."),
        covers_user_topics_tr=[
            "Alternatif tavsiye satırlarında bitki, zararlı, aktif madde seçimi",
        ],
        autocomplete_path="/Kullanim/AlternatifCokluSelect2ListesiGetir",
        referer_path="/Kullanim/TavsiyeAlternatif",
        param_style="select2_id",
        related_datatable_post="/Kullanim/TavsiyeAlternatifListeGetir",
        official_page_path="/Kullanim/TavsiyeAlternatif",
    ),
    BkuAutocompleteEndpoint(
        slug="mrl_aktif_madde_detay_secim",
        title_tr="MRL Aktif Madde detay — tablo filtresi",
        description_tr=(
            "Belirli bir MRL aktif madde detay sayfasındaki çoklu seçim (Mrl Ürün veya Bitki filtreleri)."
        ),
        covers_user_topics_tr=[
            "MRL Aktif Madde detay sayfasında ürün/bitki süzme (ör. /MRLAktifMadde/Details/{id})",
        ],
        autocomplete_path="/Tamamla/MrlAktifMaddeDetaySecimListesiGetir",
        referer_path="/MRLAktifMadde/Details/17",
        param_style="select2_id",
        related_datatable_post="/MRLAktifMadde/MrlAktifeAitOranlariGetir",
        official_page_path="/MRLAktifMadde/Details/17",
    ),
]

SLUG_MAP: Dict[str, BkuAutocompleteEndpoint] = {e.slug: e for e in BKU_AUTOCOMPLETE_ENDPOINTS}


def catalog_public_dict(base_url: str) -> Dict[str, Any]:
    root = base_url.rstrip("/")
    items: List[Dict[str, Any]] = []
    for e in BKU_AUTOCOMPLETE_ENDPOINTS:
        items.append(
            {
                "slug": e.slug,
                "title_tr": e.title_tr,
                "description_tr": e.description_tr,
                "covers_user_topics_tr": e.covers_user_topics_tr,
                "autocomplete_url": root + e.autocomplete_path,
                "referer_url": root + e.referer_path,
                "param_style": e.param_style,
                "query_or_select2_params": (
                    {"query": "<metin>"}
                    if e.param_style == "query"
                    else {"pageSize": 25, "id": "<metin>"}
                ),
                "official_page_url": root + e.official_page_path,
                "related_datatable_post_path": e.related_datatable_post,
            }
        )
    return {
        "official_site": "https://bku.tarimorman.gov.tr/Arama/Index",
        "base_url": root,
        "note_tr": (
            "Bu liste BKÜ web arayüzündeki autocomplete JSON uçlarıdır; "
            "tam tablo (DataTables) gövdeleri CSRF ve oturum gerektirir, bu API şimdilik autocomplete proxy sunar."
        ),
        "autocomplete_endpoints": items,
    }
