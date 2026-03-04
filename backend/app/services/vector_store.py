from pathlib import Path
import re
from hashlib import md5
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHROMA_PATH = PROJECT_ROOT / "backend" / "data" / "chroma"
COLLECTION_NAME = "tg_admin_chunks_hash_v1"


class HashEmbeddingFunction:
    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def name(self) -> str:
        return f"hash-embedding-{self.dim}"

    def __call__(self, input: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in input:
            vec = [0.0] * self.dim
            tokens = re.findall(r"[a-z0-9']+", text.lower())
            if not tokens:
                vectors.append(vec)
                continue
            for token in tokens:
                idx = int(md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
                vec[idx] += 1.0
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


class VectorStore:
    def __init__(self) -> None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        embedding_fn = HashEmbeddingFunction(dim=128)
        self.embedding_fn = embedding_fn
        self.collection: Collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn
        )

    def reset_collection(self) -> None:
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )

    def upsert_chunks(self, items: list[dict[str, Any]]) -> int:
        if not items:
            return 0

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        metadatas = [item["metadata"] for item in items]
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(items)

    def search(
        self,
        query: str,
        top_k: int = 4,
        category_filter: str | None = None
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []

        query_args: dict[str, Any] = {
            "query_texts": [query],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"]
        }
        if category_filter:
            query_args["where"] = {"category": category_filter}

        result = self.collection.query(**query_args)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        out: list[dict[str, Any]] = []
        for i, doc in enumerate(docs):
            out.append(
                {
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distances[i] if i < len(distances) else None
                }
            )
        return out

    def count(self) -> int:
        return self.collection.count()
