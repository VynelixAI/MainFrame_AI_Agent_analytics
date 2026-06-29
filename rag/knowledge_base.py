"""RAG Knowledge Base for Mainframe Operations."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from config import KNOWLEDGE_DIR, get_settings
from utils.logging_config import logger

try:
    from sentence_transformers import SentenceTransformer

    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

try:
    import faiss
    import numpy as np

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    import chromadb

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class KnowledgeBase:
    """Vector knowledge base with FAISS/Chroma backends."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._embedder: Any = None
        self._faiss_index: Any = None
        self._documents: list[dict[str, str]] = []
        self._chroma_client: Any = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._load_documents()
        try:
            if ST_AVAILABLE:
                self._embedder = SentenceTransformer(self.settings.embedding_model)
                self._build_index()
        except Exception as exc:
            logger.warning("Vector index unavailable, using keyword search: %s", exc)
            self._embedder = None
        self._initialized = True
        logger.info("Knowledge base initialized with %d documents", len(self._documents))

    def _load_documents(self) -> None:
        for subdir in ["JCL", "COBOL", "ABEND", "RUNBOOKS", "DB2", "MQ", "CICS"]:
            dir_path = KNOWLEDGE_DIR / subdir
            if not dir_path.exists():
                continue
            for file_path in dir_path.glob("**/*"):
                if file_path.suffix in (".md", ".txt", ".cbl", ".jcl"):
                    content = file_path.read_text(errors="replace")
                    self._documents.append({
                        "id": hashlib.md5(str(file_path).encode()).hexdigest()[:12],
                        "source": str(file_path.relative_to(KNOWLEDGE_DIR)),
                        "category": subdir,
                        "content": content,
                    })

    def _chunk_text(self, text: str) -> list[str]:
        size = self.settings.chunk_size
        overlap = self.settings.chunk_overlap
        chunks: list[str] = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + size])
            start += size - overlap
        return chunks

    def _build_index(self) -> None:
        if not self._documents or not ST_AVAILABLE or self._embedder is None:
            return

        all_chunks: list[str] = []
        self._chunk_metadata: list[dict[str, str]] = []
        for doc in self._documents:
            for i, chunk in enumerate(self._chunk_text(doc["content"])):
                all_chunks.append(chunk)
                self._chunk_metadata.append({
                    "doc_id": doc["id"],
                    "source": doc["source"],
                    "category": doc["category"],
                    "chunk_index": str(i),
                })

        embeddings = self._embedder.encode(all_chunks, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")

        if self.settings.vector_store_backend == "faiss" and FAISS_AVAILABLE:
            dim = embeddings.shape[1]
            self._faiss_index = faiss.IndexFlatIP(dim)
            faiss.normalize_L2(embeddings)
            self._faiss_index.add(embeddings)
            self._faiss_chunks = all_chunks
        elif CHROMA_AVAILABLE:
            self._chroma_client = chromadb.PersistentClient(path=self.settings.chroma_persist_dir)
            collection = self._chroma_client.get_or_create_collection("mainframe_kb")
            ids = [f"chunk_{i}" for i in range(len(all_chunks))]
            collection.add(
                documents=all_chunks,
                metadatas=self._chunk_metadata,
                ids=ids,
            )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self._initialized:
            self.initialize()

        if not self._documents:
            return []

        if ST_AVAILABLE and self._embedder is not None:
            return self._vector_search(query, top_k)

        return self._keyword_search(query, top_k)

    def _vector_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        query_emb = self._embedder.encode([query])
        query_emb = np.array(query_emb).astype("float32")

        if self._faiss_index is not None and FAISS_AVAILABLE:
            faiss.normalize_L2(query_emb)
            scores, indices = self._faiss_index.search(query_emb, min(top_k, len(self._faiss_chunks)))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0:
                    meta = self._chunk_metadata[idx]
                    results.append({
                        "content": self._faiss_chunks[idx],
                        "score": float(score),
                        "source": meta["source"],
                        "category": meta["category"],
                    })
            return results

        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        query_terms = set(query.lower().split())
        scored: list[tuple[float, dict[str, str]]] = []
        for doc in self._documents:
            content_lower = doc["content"].lower()
            score = sum(1 for term in query_terms if term in content_lower) / max(len(query_terms), 1)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"content": doc["content"][:500], "score": score, "source": doc["source"], "category": doc["category"]}
            for score, doc in scored[:top_k]
        ]

    def get_context_for_investigation(self, query: str, top_k: int = 5) -> list[str]:
        results = self.search(query, top_k)
        return [f"[{r['category']}] {r['content'][:300]}" for r in results]


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
