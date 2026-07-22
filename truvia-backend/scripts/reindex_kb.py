"""Re-chunk + re-embed the entire knowledge base with the current
(fixed) embedding + chunking pipeline.

Necessary after changing the embedding function: stored chunk embeddings must
be regenerated with the SAME function used at query time, otherwise query and
document vectors live in different spaces and similarity is meaningless.

Run: .venv\\Scripts\\python.exe -m scripts.reindex_kb
"""
import asyncio

from sqlalchemy import select

from app.data.postgres_client import AsyncSessionLocal
from app.models.knowledge import KnowledgeBase
from app.services.kb_ingest import index_document


async def main():
    async with AsyncSessionLocal() as session:
        kbs = (await session.execute(select(KnowledgeBase))).scalars().all()
        total_docs = 0
        total_chunks = 0
        for kb in kbs:
            try:
                n = await index_document(session, kb)
                total_docs += 1
                total_chunks += n
                print(f"[OK] {kb.source} :: {kb.title!r} -> {n} chunk(s)")
            except Exception as e:
                print(f"[FAIL] {kb.title!r}: {e}")
        print(f"\nRe-indexed {total_docs} document(s), {total_chunks} chunk(s) total.")


if __name__ == "__main__":
    asyncio.run(main())
