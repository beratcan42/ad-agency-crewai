from crewai.tools import tool
import httpx
import os
import json

API_URL = os.getenv("API_URL", "http://localhost:8010")

@tool("GetClientInfo")
def get_client_info(client_id: str) -> str:
    """
    Müşterinin CRM üzerindeki profilini, önceki kampanya tekliflerini ve faturalarını getirir.
    client_id: Müşteri kısa adı (slug), örn: 'akme-tekstil'
    """
    try:
        response = httpx.get(f"{API_URL}/crm/clients", headers={"X-Client-Id": client_id}, timeout=10.0)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Müşteri bilgisi alınamadı. Hata: {str(e)}"

@tool("CreateProposal")
def create_proposal(client_id: str, title: str, total_amount: float) -> str:
    """
    Yeni bir kampanya için CRM üzerinde teklif (proposal) kaydı açar ve bir PDF teklif dökümanı üretir.
    client_id: Müşteri kısa adı (örn: 'akme-tekstil')
    title: Teklif başlığı (örn: '2024 Yaz Kampanyası')
    total_amount: Tahmini bütçe/teklif tutarı
    """
    try:
        payload = {"title": title, "total_amount": total_amount}
        response = httpx.post(f"{API_URL}/crm/proposals", headers={"X-Client-Id": client_id}, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        return f"Teklif başarıyla oluşturuldu. ID: {data['proposal_id']}, PDF: {data['pdf_path']}"
    except Exception as e:
        return f"Teklif oluşturulamadı. Hata: {str(e)}"

@tool("GenerateInvoice")
def generate_invoice(client_id: str, proposal_id: str, amount: float) -> str:
    """
    Tamamlanan kampanya/teklif üzerinden fatura (invoice) keser ve PDF oluşturur.
    client_id: Müşteri kısa adı
    proposal_id: Faturaya konu olan teklifin UUID'si
    amount: Fatura tutarı (KDV hariç)
    """
    try:
        payload = {"proposal_id": proposal_id, "amount": amount, "tax_rate": 20.0}
        response = httpx.post(f"{API_URL}/crm/invoices", headers={"X-Client-Id": client_id}, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        return f"Fatura başarıyla kesildi. ID: {data['invoice_id']}, Toplam Tutar: {data['total_amount']}, PDF: {data['pdf_path']}"
    except Exception as e:
        return f"Fatura kesilemedi. Hata: {str(e)}"
