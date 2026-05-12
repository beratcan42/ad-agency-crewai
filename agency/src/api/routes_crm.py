import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg
from ..config.settings import settings
from ..middleware.client_context import require_client_id
from ..crm.pdf_gen import generate_proposal_pdf, generate_invoice_pdf

log = logging.getLogger(__name__)

router = APIRouter(prefix="/crm", tags=["CRM"])

async def get_db_connection():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

class ProposalCreate(BaseModel):
    title: str
    total_amount: float

class InvoiceCreate(BaseModel):
    proposal_id: str
    amount: float
    tax_rate: float = 20.0

@router.get("/clients")
async def get_client_info(client_id: str = Depends(require_client_id), conn: asyncpg.Connection = Depends(get_db_connection)):
    """Musteri profili, bakiye, teklif ve fatura ozetini getirir."""
    client = await conn.fetchrow("SELECT * FROM crm.clients WHERE client_id = $1", client_id)
    if not client:
        # Oto-kayit (mock amacli)
        await conn.execute("INSERT INTO crm.clients (client_id, name) VALUES ($1, $2)", client_id, f"{client_id} (Oto)")
        client = await conn.fetchrow("SELECT * FROM crm.clients WHERE client_id = $1", client_id)
        
    proposals = await conn.fetch("SELECT * FROM crm.proposals WHERE client_id = $1 ORDER BY created_at DESC LIMIT 5", client_id)
    invoices = await conn.fetch("SELECT * FROM crm.invoices WHERE client_id = $1 ORDER BY created_at DESC LIMIT 5", client_id)
    
    return {
        "client": dict(client),
        "proposals": [dict(p) for p in proposals],
        "invoices": [dict(i) for i in invoices]
    }

@router.post("/proposals")
async def create_proposal(body: ProposalCreate, client_id: str = Depends(require_client_id), conn: asyncpg.Connection = Depends(get_db_connection)):
    """Yeni teklif olusturur ve PDF ciktisi uretir."""
    proposal_id = await conn.fetchval(
        "INSERT INTO crm.proposals (client_id, title, total_amount) VALUES ($1, $2, $3) RETURNING proposal_id",
        client_id, body.title, body.total_amount
    )
    # PDF uret
    pdf_path = generate_proposal_pdf(str(proposal_id), client_id, body.title, body.total_amount)
    
    await conn.execute("UPDATE crm.proposals SET pdf_path = $1 WHERE proposal_id = $2", pdf_path, proposal_id)
    return {"status": "success", "proposal_id": str(proposal_id), "pdf_path": pdf_path}

@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, client_id: str = Depends(require_client_id), conn: asyncpg.Connection = Depends(get_db_connection)):
    """Kampanya icin fatura keser ve PDF uretir."""
    total_amount = body.amount * (1 + body.tax_rate / 100)
    
    invoice_id = await conn.fetchval(
        "INSERT INTO crm.invoices (proposal_id, client_id, amount, tax_rate, total_amount) VALUES ($1::uuid, $2, $3, $4, $5) RETURNING invoice_id",
        body.proposal_id, client_id, body.amount, body.tax_rate, total_amount
    )
    
    # PDF uret
    pdf_path = generate_invoice_pdf(str(invoice_id), client_id, body.amount, body.tax_rate, total_amount)
    await conn.execute("UPDATE crm.invoices SET pdf_path = $1 WHERE invoice_id = $2", pdf_path, invoice_id)
    
    return {"status": "success", "invoice_id": str(invoice_id), "total_amount": total_amount, "pdf_path": pdf_path}
