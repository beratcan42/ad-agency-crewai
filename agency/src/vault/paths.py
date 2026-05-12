"""Guvenli Vault dosya yolu cozumlemesi (path traversal engeli)."""

from __future__ import annotations

from pathlib import Path

from ..config.settings import settings
from ..middleware.client_context import normalize_client_id

_RESERVED_TOP = frozenset({"_template", "_shared"})


def vault_base() -> Path:
    return Path(settings.VAULT_BASE_PATH).expanduser().resolve()


def client_vault_root(client_id: str) -> Path:
    """Musteri vault kokunu dondurur (/vaults/<client_id>)."""
    cid = normalize_client_id(client_id)
    if not cid:
        raise ValueError("Gecersiz client_id")
    base = vault_base()
    root = (base / cid).resolve()
    root.relative_to(base)
    return root


def resolve_note_path(client_id: str, relative_path: str) -> Path:
    """Not goreceli yolu mutlak dosyaya cevirir; traversal reddeder."""
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel or rel.startswith("/"):
        raise ValueError("Gecersiz relative_path")
    if ".." in Path(rel).parts:
        raise ValueError("relative_path icinde '..' olamaz")

    root = client_vault_root(client_id)
    target = (root / rel).resolve()
    target.relative_to(root)

    if target.suffix.lower() != ".md":
        raise ValueError("Sadece .md dosyalari destekleniyor")

    return target


def iter_client_ids_on_disk() -> list[str]:
    """Vault mount altindaki gecerli musteri klasorleri."""
    base = vault_base()
    if not base.is_dir():
        return []
    out: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") or name in _RESERVED_TOP:
            continue
        cid = normalize_client_id(name)
        if cid:
            out.append(cid)
    return out


def should_index_relative(rel_posix: str) -> bool:
    """Gizli klasor/dosyalari indeks disi birak."""
    parts = rel_posix.split("/")
    if any(p.startswith(".") for p in parts):
        return False
    return rel_posix.lower().endswith(".md")
