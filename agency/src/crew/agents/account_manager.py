"""Account Manager — orchestrator ajan.

Aşama 2'de minimal: ModelRouter ile tek seferlik çağrı (CrewAI Agent değil, doğrudan LLM).
Aşama 3'te CrewAI Agent + Task + Flow ile tam entegre edilecek.
"""

from __future__ import annotations

from ...config.loader import get_agent_meta

AGENT_ID = "account_manager"


def get_system_prompt() -> str:
    meta = get_agent_meta(AGENT_ID)
    role = meta.get("role", "Account Manager")
    goal = meta.get("goal", "")
    backstory = meta.get("backstory", "")

    return (
        f"# Rol\n{role}\n\n"
        f"# Hedef\n{goal}\n\n"
        f"# Geçmiş\n{backstory}\n\n"
        "# Görev\n"
        "Müşteri brief'ini analiz et. Hangi uzman ajanlara ihtiyaç olduğunu belirle "
        "(Strateji, Copywriter, Sosyal Medya, SEO, Kreatif, Veri Analist, Bütçe, "
        "E-ticaret, Yayın, CRM). Türkçe ve madde işaretli yanıtla.\n\n"
        "# Yanıt Formatı\n"
        "## Brief Özeti\n"
        "<2 cümle>\n\n"
        "## Gerekli Ajanlar\n"
        "- <ajan>: <neden>\n\n"
        "## Önerilen Sıra\n"
        "<numaralı liste>\n"
    )
