from crewai.tools import tool
import httpx
import os

MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://mcp-gateway:8811")

@tool("PostizDraftCreator")
def create_postiz_draft(content: str, platforms: str) -> str:
    """
    Sosyal medya metinlerini Postiz sistemine taslak olarak kaydeder.
    content: Paylasilacak sosyal medya metni (ornek: "Yazin tadi plajda cikar! 🏖️")
    platforms: Paylasilacak platformlar, virgul ile ayrilmis (ornek: "instagram,twitter")
    """
    try:
        platform_list = [p.strip() for p in platforms.split(",")]
        payload = {"content": content, "platforms": platform_list}
        
        response = httpx.post(f"{MCP_GATEWAY_URL}/mcp/postiz/draft", json=payload, timeout=10.0)
        response.raise_for_status()
        
        data = response.json()
        return f"Basariyla taslak olusturuldu. Postiz ID: {data.get('post_id')}"
    except Exception as e:
        return f"Taslak olusturulamadi. Hata: {str(e)}"
