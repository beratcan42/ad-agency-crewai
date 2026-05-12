"""Vault dosya CRUD — senkron pathlib (Celery / Tool uyumlu)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ..config.settings import settings
from .paths import client_vault_root, resolve_note_path, should_index_relative

log = logging.getLogger(__name__)


class VaultStore:
    """Markdown notlari okuma/yazma/listeleme."""

    def list_markdown(self, client_id: str, *, max_files: int = 500) -> list[str]:
        root = client_vault_root(client_id)
        if not root.is_dir():
            raise FileNotFoundError(f"Vault bulunamadi: {client_id}")
        out: list[str] = []
        for path in sorted(root.rglob("*.md")):
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if not should_index_relative(rel):
                continue
            out.append(rel)
            if len(out) >= max_files:
                break
        return out

    def read_note(self, client_id: str, relative_path: str) -> str:
        path = resolve_note_path(client_id, relative_path)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        return path.read_text(encoding="utf-8")

    def write_note(self, client_id: str, relative_path: str, content: str) -> dict[str, str]:
        path = resolve_note_path(client_id, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        log.info("vault.write", extra={"client_id": client_id, "path": relative_path})
        return {"client_id": client_id, "path": relative_path, "bytes": str(path.stat().st_size)}


_store: VaultStore | None = None


def get_vault_store() -> VaultStore:
    global _store
    if _store is None:
        _store = VaultStore()
    return _store


def write_heartbeat(client_id: str, payload: dict) -> Path:
    """Watcher kalp atisi JSON dosyasi."""
    root = client_vault_root(client_id)
    root.mkdir(parents=True, exist_ok=True)
    path = root / settings.VAULT_HEARTBEAT_FILENAME
    body = {"ts": datetime.now(UTC).isoformat(), **payload}
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
