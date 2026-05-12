"""Vault .md -> agency.note_embeddings senkronizasyonu."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from ..router.telemetry import get_pool
from .embedder import chunk_text, embed_batch, sha256_text, vector_literal
from .paths import client_vault_root, iter_client_ids_on_disk, should_index_relative, vault_base
from .store import write_heartbeat

log = logging.getLogger(__name__)

_TABLE_MISSING_LOGGED = False


async def sync_markdown_to_db(client_id: str, rel_path: str, body: str) -> None:
    """Tek dosyanin chunklarini yazar; bos dosya satirlari siler."""
    global _TABLE_MISSING_LOGGED
    chunks = chunk_text(body)
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM agency.note_embeddings WHERE client_id=$1 AND rel_path=$2",
                client_id,
                rel_path,
            )
            if not chunks:
                return
            embeddings = await embed_batch(chunks)
            for idx, piece in enumerate(chunks):
                h = sha256_text(piece)
                emb = embeddings[idx] if idx < len(embeddings) else None
                if emb is None:
                    await conn.execute(
                        """
                        INSERT INTO agency.note_embeddings (
                            client_id, rel_path, chunk_index, content_hash, body, embedding
                        ) VALUES ($1, $2, $3, $4, $5, NULL)
                        """,
                        client_id,
                        rel_path,
                        idx,
                        h,
                        piece,
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO agency.note_embeddings (
                            client_id, rel_path, chunk_index, content_hash, body, embedding
                        ) VALUES ($1, $2, $3, $4, $5, $6::vector)
                        """,
                        client_id,
                        rel_path,
                        idx,
                        h,
                        piece,
                        vector_literal(emb),
                    )
    except Exception as e:
        err = str(e).lower()
        if "note_embeddings" in err or "does not exist" in err or "undefinedtable" in err:
            if not _TABLE_MISSING_LOGGED:
                log.warning(
                    "vault.sync.table_missing",
                    extra={"hint": "scripts/sql/init/03-note-embeddings.sql psql ile apply edin"},
                )
                _TABLE_MISSING_LOGGED = True
            return
        raise


async def poll_vault_once(state: dict[str, tuple[int, str]]) -> None:
    """Tum musteri vaultlarini tarar; degisen .md -> DB."""
    base = vault_base()
    if not base.is_dir():
        log.warning("vault.poller.no_mount", extra={"path": str(base)})
        return

    for cid in iter_client_ids_on_disk():
        try:
            root = client_vault_root(cid)
        except ValueError:
            continue
        n_md = 0
        for md_path in sorted(root.rglob("*.md")):
            try:
                rel = md_path.relative_to(root).as_posix()
            except ValueError:
                continue
            if not should_index_relative(rel):
                continue
            n_md += 1
            key = f"{cid}:{rel}"

            def _fp(p: Path = md_path) -> tuple[int, str]:
                data = p.read_bytes()
                return p.stat().st_mtime_ns, hashlib.sha256(data).hexdigest()

            try:
                mtime_ns, digest = await asyncio.to_thread(_fp)
            except OSError:
                continue

            prev = state.get(key)
            if prev == (mtime_ns, digest):
                continue

            try:
                body = await asyncio.to_thread(md_path.read_text, encoding="utf-8")
            except OSError:
                continue

            try:
                await sync_markdown_to_db(cid, rel, body)
            except Exception as e:
                log.warning(
                    "vault.sync.fail",
                    extra={"client_id": cid, "rel": rel, "err": str(e)[:160]},
                )

            state[key] = (mtime_ns, digest)

        try:
            write_heartbeat(cid, {"md_files": n_md, "poller": "ok"})
        except Exception:
            log.debug("vault.heartbeat.fail", extra={"client_id": cid})
