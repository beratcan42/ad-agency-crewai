"""12 ajan registry — gorev sablonu + system prompt builder.

models.yaml'daki role/goal/backstory'yi alir, ajan-bazli task instruction +
output_format ile birlestirip LLM'e gondermeye hazir system prompt'u uretir.
"""

from __future__ import annotations

from typing import TypedDict

from ...config.loader import get_agent_meta


class TaskTemplate(TypedDict):
    instruction: str
    output_format: str


AGENT_TASKS: dict[str, TaskTemplate] = {
    "account_manager": {
        "instruction": (
            "Musteri brief'ini analiz et. Hangi uzman ajanlara ihtiyac oldugunu belirle "
            "(customer_service, strategist, copywriter, social_media, seo_specialist, "
            "creative_director, data_analyst, budget_manager, ecommerce_specialist, "
            "publisher, crm_billing). Onerilen calisma sirasini ver."
        ),
        "output_format": (
            "## Brief Ozeti\n<2-3 cumle>\n\n"
            "## Gerekli Ajanlar\n- <agent_id>: <kisa neden>\n\n"
            "## Onerilen Sira\n1. <agent_id> — <ne yapacak>\n\n"
            "## Riskler / Notlar\n<varsa>"
        ),
    },
    "customer_service": {
        "instruction": (
            "Brief'teki muglak ve eksik bilgileri tespit et. Musteriye sorulacak "
            "3-5 net, kibar ve dogrudan soru uret. Brief'in olgunluk skorunu ver."
        ),
        "output_format": (
            "## Brief Olgunluk Skoru (0-100)\n<sayi> — <neden>\n\n"
            "## Tespit Edilen Eksikler\n- <madde>\n\n"
            "## Musteriye Sorulacaklar (numarali)\n1. ...\n\n"
            "## Onerilen Yanit Tonu\n<bir cumle>"
        ),
    },
    "strategist": {
        "instruction": (
            "Sektor/pazar arastirmasi yap, en az 3 rakip listele, SWOT ve hedef kitle "
            "profili (persona) cikar, konumlandirma tavsiyesi ver."
        ),
        "output_format": (
            "## Pazar Ozeti\n## Rakip Analizi (en az 3, tablo: rakip-guc-zayif)\n"
            "## SWOT\n## Hedef Kitle Persona\n## Konumlandirma Onerisi"
        ),
    },
    "copywriter": {
        "instruction": (
            "AIDA veya PAS formuluyle reklam metni uret. Hedef kitle ve marka sesini koru. "
            "Yasakli iddialardan (saglik, mutlak vaat) kacin."
        ),
        "output_format": (
            "## Ana Baslik (3 alternatif)\n## Slogan (3 alternatif)\n"
            "## Reklam Govdesi — Kisa (50-80 kelime)\n## Reklam Govdesi — Uzun (150-200 kelime)\n"
            "## Call-to-Action (CTA)"
        ),
    },
    "social_media": {
        "instruction": (
            "Platform-spesifik (Instagram/TikTok/LinkedIn) 2 haftalik post takvimi, "
            "caption ve hashtag stratejisi uret. Algoritma sezgisini at."
        ),
        "output_format": (
            "## Platform Stratejisi\n## 2 Haftalik Takvim (tablo: gun-platform-format-caption)\n"
            "## Hashtag Listesi\n- Niche (5)\n- Orta (5)\n- Genis (5)\n"
            "## Onerilen Saat Araliklari"
        ),
    },
    "seo_specialist": {
        "instruction": (
            "Anahtar kelime arastirmasi (kisa+long-tail), meta tag onerileri, "
            "on-page SEO ve E-E-A-T uyumlu icerik konulari uret."
        ),
        "output_format": (
            "## Birincil Anahtar Kelimeler (5)\n## Long-tail Kelimeler (10)\n"
            "## Meta Title (60 char)\n## Meta Description (155 char)\n"
            "## Icerik Konu Onerileri (5 baslik)"
        ),
    },
    "creative_director": {
        "instruction": (
            "Gorsel kampanya konseptini tanimla. FLUX/Imagen icin uretime hazir, "
            "kompozisyon-isik-renk detayli 5 prompt yaz (Ingilizce)."
        ),
        "output_format": (
            "## Konsept\n## Mood Board (textual: 5 ana eleman)\n"
            "## Renk Paleti (HEX)\n## Tipografi Onerisi\n"
            "## FLUX Prompt'lari\n1. <english prompt>\n2. ...\n3. ...\n4. ...\n5. ..."
        ),
    },
    "data_analyst": {
        "instruction": (
            "KPI hedefleri belirle, olcum planini cikar. Gerekirse pandas/SQL "
            "kod parcacigi uret (markdown code block icinde)."
        ),
        "output_format": (
            "## Birincil KPI'lar (5)\n## Olcum Plani (tablo: metrik-aralik-kaynak)\n"
            "## Beklenen Performans Araliklari\n## Kod Snippet (opsiyonel)"
        ),
    },
    "budget_manager": {
        "instruction": (
            "Toplam butceyi kanal/platform bazinda dagit, ROAS hedefi koy, "
            "risk durumu ve esneklik planini belirt."
        ),
        "output_format": (
            "## Kanal Dagilimi (tablo: kanal-tutar-yuzde)\n"
            "## ROAS Hedefi\n## CPM/CPC/CPA Beklentileri\n"
            "## Riskler ve Esneklik Plani"
        ),
    },
    "ecommerce_specialist": {
        "instruction": (
            "Marketplace (Trendyol/Hepsiburada/Amazon) icin SEO uyumlu urun "
            "aciklamasi, varyant etiketleri ve anahtar ozellikler uret."
        ),
        "output_format": (
            "## Urun Basligi (SEO uyumlu, 60-100 char)\n## Kisa Aciklama (250 char)\n"
            "## Uzun Aciklama (madde isaretli)\n## Varyant Etiketleri\n## Anahtar Ozellikler (8 madde)"
        ),
    },
    "publisher": {
        "instruction": (
            "Onaylanmis icerikleri platform-bazli yayin planina dok. Postiz MCP "
            "ile uyumlu sade JSON listesi uret."
        ),
        "output_format": (
            "## Yayin Plani JSON\n"
            "```json\n"
            "[{\"platform\":\"instagram\",\"scheduled_at\":\"YYYY-MM-DDTHH:MM:SS+03:00\","
            "\"content\":\"...\",\"media\":[]}]\n"
            "```"
        ),
    },
    "crm_billing": {
        "instruction": (
            "Brief'ten musteri kaydi ve teklif kalemleri cikar. KDV %20 dahil "
            "fatura tablosu uret. Yapilandirilmis JSON+tablo kullan."
        ),
        "output_format": (
            "## Musteri Bilgisi (JSON)\n```json\n{\"client_name\":\"...\",\"sector\":\"...\",\"contact\":\"...\"}\n```\n"
            "## Teklif Kalemleri (tablo: aciklama-adet-birim-tutar)\n"
            "## Mali Ozet\n- Ara Toplam:\n- KDV %20:\n- Genel Toplam:"
        ),
    },
}


def get_task_template(agent_id: str) -> TaskTemplate:
    if agent_id not in AGENT_TASKS:
        raise KeyError(f"Bilinmeyen ajan: {agent_id}")
    return AGENT_TASKS[agent_id]


def build_system_prompt(agent_id: str) -> str:
    """models.yaml metadata + task template'i system prompt'a doker."""
    meta = get_agent_meta(agent_id)
    tpl = get_task_template(agent_id)
    return (
        f"# Rol\n{meta.get('role', agent_id)}\n\n"
        f"# Hedef\n{meta.get('goal', '')}\n\n"
        f"# Arkaplan\n{meta.get('backstory', '')}\n\n"
        f"# Gorev\n{tpl['instruction']}\n\n"
        f"# Yanit Formati (kesin uy, baska bilgi ekleme)\n{tpl['output_format']}\n"
    )


def get_all_agent_ids() -> list[str]:
    return list(AGENT_TASKS.keys())
