import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

def generate_invoice_pdf(invoice_id: str, client_id: str, amount: float, tax_rate: float, total_amount: float) -> str:
    """Faturalar icin basit bir PDF uretir ve dosya yolunu dondurur."""
    os.makedirs("/tmp/invoices", exist_ok=True)
    pdf_path = f"/tmp/invoices/{invoice_id}.pdf"
    
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, 800, "FATURA")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, f"Fatura No: {invoice_id}")
    c.drawString(50, 730, f"Musteri: {client_id}")
    c.drawString(50, 710, f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    c.drawString(50, 650, f"Ara Toplam: {amount:.2f} TL")
    c.drawString(50, 630, f"KDV (%{tax_rate}): {(amount * tax_rate / 100):.2f} TL")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 600, f"Genel Toplam: {total_amount:.2f} TL")
    
    c.save()
    return pdf_path

def generate_proposal_pdf(proposal_id: str, client_id: str, title: str, total_amount: float) -> str:
    """Teklifler icin basit bir PDF uretir."""
    os.makedirs("/tmp/proposals", exist_ok=True)
    pdf_path = f"/tmp/proposals/{proposal_id}.pdf"
    
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, 800, "KAMPANYA TEKLIFI")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, f"Teklif No: {proposal_id}")
    c.drawString(50, 730, f"Musteri: {client_id}")
    c.drawString(50, 710, f"Baslik: {title}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 650, f"Tahmini Butce: {total_amount:.2f} TL")
    
    c.save()
    return pdf_path
