"""Vault dosya araclari — CrewAI / sync worker icin."""

from __future__ import annotations

import logging

from ..vault.store import get_vault_store

log = logging.getLogger(__name__)


def vault_read_markdown(client_id: str, relative_path: str) -> str:
    """Markdown not oku (senkron)."""
    return get_vault_store().read_note(client_id, relative_path)


def vault_write_markdown(client_id: str, relative_path: str, content: str) -> str:
    """Markdown yaz; kisa onay mesaji doner."""
    meta = get_vault_store().write_note(client_id, relative_path, content)
    return f"OK yazildi: {meta['path']} ({meta['bytes']} byte)"


def vault_list_markdown_paths(client_id: str, max_files: int = 100) -> str:
    """Dosya listesini satir satir metin olarak doner."""
    paths = get_vault_store().list_markdown(client_id, max_files=max_files)
    return "\n".join(paths)
