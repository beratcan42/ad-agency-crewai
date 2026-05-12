"""CrewAI @tool sarmalayıcıları — Vault dosya işlemleri + semantic arama.

Aşama 5: vault_fs.py fonksiyonlarını CrewAI @tool dekoratörü ile sarar.
Ajanlar bu tool'ları doğrudan kullanabilir.
"""

from __future__ import annotations

import logging
from typing import Any

from crewai.tools import tool

log = logging.getLogger(__name__)


@tool("VaultReadNote")
def vault_read_note(client_id: str, path: str) -> str:
    """Müşteri vault'undan belirtilen path'teki markdown notu okur.

    Args:
        client_id: Müşteri slug'ı (örn. 'akme-tekstil')
        path: Vault içi relative path (örn. '01-Briefs/kampanya-x.md')

    Returns:
        Markdown içeriği
    """
    from .vault_fs import vault_read_markdown

    try:
        return vault_read_markdown(client_id, path)
    except FileNotFoundError:
        return f"HATA: Dosya bulunamadı — {path}"
    except Exception as e:
        return f"HATA: {e}"


@tool("VaultWriteNote")
def vault_write_note(client_id: str, path: str, content: str) -> str:
    """Müşteri vault'una markdown not yazar veya günceller.

    Args:
        client_id: Müşteri slug'ı
        path: Vault içi relative path
        content: Yazılacak markdown içeriği

    Returns:
        Onay mesajı
    """
    from .vault_fs import vault_write_markdown

    try:
        return vault_write_markdown(client_id, path, content)
    except Exception as e:
        return f"HATA: {e}"


@tool("VaultListFiles")
def vault_list_files(client_id: str) -> str:
    """Müşteri vault'undaki tüm markdown dosyalarını listeler.

    Args:
        client_id: Müşteri slug'ı

    Returns:
        Satır satır dosya yolları
    """
    from .vault_fs import vault_list_markdown_paths

    try:
        result = vault_list_markdown_paths(client_id)
        return result if result else "Vault boş — henüz dosya yok."
    except Exception as e:
        return f"HATA: {e}"


@tool("VaultSemanticSearch")
def vault_semantic_search(client_id: str, query: str, limit: int = 5) -> str:
    """Vault notlarında semantic (anlamsal) arama yapar.

    Embedding tabanlı benzerlik araması kullanır.

    Args:
        client_id: Müşteri slug'ı
        query: Arama sorgusu
        limit: Maksimum sonuç sayısı (varsayılan 5)

    Returns:
        Eşleşen chunk'lar metin olarak
    """
    import asyncio

    try:
        from ..vault.store import get_vault_store

        store = get_vault_store()

        # Sync context'ten async fonksiyon çağır
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Zaten async loop içindeyiz — yeni thread'de çalıştır
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(
                    asyncio.run,
                    _async_search(client_id, query, limit),
                ).result(timeout=30)
        else:
            results = asyncio.run(_async_search(client_id, query, limit))

        if not results:
            return f"'{query}' için sonuç bulunamadı."

        lines = []
        for i, r in enumerate(results, 1):
            score = r.get("similarity", 0)
            path = r.get("source_path", "?")
            chunk = r.get("chunk_text", "")[:300]
            lines.append(f"[{i}] (skor: {score:.2f}) {path}\n{chunk}\n")
        return "\n".join(lines)
    except Exception as e:
        log.warning("vault_semantic_search.fail: %s", e)
        return f"HATA: {e}"


async def _async_search(client_id: str, query: str, limit: int) -> list[dict]:
    """Async semantic search wrapper."""
    from ..vault.poller import _embed_text
    from ..router.telemetry import get_pool

    embedding = await _embed_text(query)
    if not embedding:
        return []

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT source_path, chunk_text,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM agency.note_embeddings
            WHERE client_id = $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            str(embedding),
            client_id,
            limit,
        )
        return [dict(r) for r in rows]
