import json
from pathlib import Path

from app.services.chunking import chunk_text
from app.services.vector_store import VectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "backend" / "data" / "raw" / "sources.jsonl"


def load_sources() -> list[dict]:
    if not INPUT_FILE.exists():
        return []
    items: list[dict] = []
    for line in INPUT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def build_chunks(source: dict) -> list[dict]:
    source_id = str(source.get("id", "source"))
    text = str(source.get("text", ""))
    parts = chunk_text(text)
    chunks: list[dict] = []
    for idx, part in enumerate(parts):
        chunks.append(
            {
                "id": f"{source_id}-chunk-{idx}",
                "text": part,
                "metadata": {
                    "title": str(source.get("title", "")),
                    "url": str(source.get("url", "")),
                    "updated_at": str(source.get("updated_at", "")),
                    "category": str(source.get("category", "general")),
                    "country": str(source.get("country", "Togo"))
                }
            }
        )
    return chunks


def main() -> None:
    sources = load_sources()
    if not sources:
        print(f"[RAG] No source file found or empty: {INPUT_FILE}")
        return

    all_chunks: list[dict] = []
    for source in sources:
        all_chunks.extend(build_chunks(source))

    store = VectorStore()
    store.reset_collection()
    total = store.upsert_chunks(all_chunks)
    print(f"[RAG] Indexed chunks: {total}")
    print(f"[RAG] Collection count: {store.count()}")


if __name__ == "__main__":
    main()
