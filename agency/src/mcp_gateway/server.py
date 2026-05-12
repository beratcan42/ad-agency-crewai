import logging
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mcp_gateway")

app = FastAPI(title="Ad Agency MCP Gateway", version="0.5.0")

POSTIZ_URL = os.getenv("POSTIZ_URL", "http://localhost:5000")

class PostRequest(BaseModel):
    content: str
    platforms: list[str]

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "mcp-gateway"}

@app.post("/mcp/postiz/draft")
async def create_postiz_draft(request: PostRequest):
    """
    Postiz API'sine taslak gonderir (MCP Tool olarak disa acilacak).
    Gercek API anahtarlari JWT ile saglanabilir.
    """
    log.info(f"Draft request received: platforms={request.platforms}")
    # Gercek Postiz entegrasyonu buraya gelecek.
    # Su anlik mock yanit donuyoruz.
    return {
        "status": "success",
        "post_id": "mock_123",
        "message": "Taslak basariyla olusturuldu",
        "content_length": len(request.content)
    }
