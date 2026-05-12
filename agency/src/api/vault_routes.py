"""Asama 4 — Obsidian Vault REST API."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..middleware.client_context import require_client_id
from ..vault.paths import client_vault_root, iter_client_ids_on_disk, vault_base
from ..vault.search import hybrid_search
from ..vault.store import get_vault_store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/vault", tags=["vault"])


class VaultNoteWrite(BaseModel):
    path: str = Field(..., max_length=512)
    content: str = Field(..., max_length=500_000)


class VaultSearchBody(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=8, ge=1, le=25)


def _heartbeat_info(client_id: str) -> dict[str, Any]:
    """Kalp atisi JSON — yas saniye."""
    try:
        root = client_vault_root(client_id)
    except ValueError:
        return {"client_id": client_id, "heartbeat_found": False}
    path = root / settings.VAULT_HEARTBEAT_FILENAME
    if not path.is_file():
        return {"client_id": client_id, "heartbeat_found": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts_raw = data.get("ts")
        if not ts_raw:
            return {"client_id": client_id, "heartbeat_found": True, "parse_error": True}
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - ts.astimezone(UTC)).total_seconds()
        return {
            "client_id": client_id,
            "heartbeat_found": True,
            "age_seconds": round(age, 1),
            "md_files": data.get("md_files"),
            "poller": data.get("poller"),
        }
    except Exception:
        return {"client_id": client_id, "heartbeat_found": True, "parse_error": True}


@router.get("/status")
async def vault_status() -> dict[str, Any]:
    """Vault mount + musteri klasorleri + heartbeat ozeti (doctor icin public)."""
    base = vault_base()
    mount_ok = base.is_dir()
    clients: list[dict[str, Any]] = []
    if mount_ok:
        for cid in iter_client_ids_on_disk():
            hb = _heartbeat_info(cid)
            try:
                n_md = len(get_vault_store().list_markdown(cid))
            except Exception:
                n_md = None
            clients.append({**hb, "indexed_md_count_api": n_md})
    return {
        "vault_base": str(base),
        "mount_ok": mount_ok,
        "watcher_enabled": settings.VAULT_WATCHER_ENABLED,
        "polling_interval_sec": settings.WATCHER_POLLING_INTERVAL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "clients": clients,
    }


@router.get("/files")
async def vault_list_files(client_id: str = Depends(require_client_id)) -> dict[str, Any]:
    try:
        files = get_vault_store().list_markdown(client_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Vault klasoru yok — new-client.ps1 calistirin")
    return {"client_id": client_id, "count": len(files), "files": files}


@router.get("/note")
async def vault_read_note(
    path: str = Query(..., max_length=512),
    client_id: str = Depends(require_client_id),
) -> dict[str, Any]:
    try:
        content = get_vault_store().read_note(client_id, path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dosya bulunamadi")
    return {"client_id": client_id, "path": path, "content": content}


@router.put("/note")
async def vault_write_note(
    body: VaultNoteWrite,
    client_id: str = Depends(require_client_id),
) -> dict[str, Any]:
    try:
        meta = get_vault_store().write_note(client_id, body.path, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return meta


@router.post("/search")
async def vault_search(
    body: VaultSearchBody,
    client_id: str = Depends(require_client_id),
) -> dict[str, Any]:
    try:
        hits = await hybrid_search(client_id, body.query, limit=body.limit)
    except Exception as e:
        log.exception("vault.search.fail")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Arama basarisiz (DB/embed): {e}",
        )
    return {"client_id": client_id, "query": body.query, "count": len(hits), "hits": hits}
