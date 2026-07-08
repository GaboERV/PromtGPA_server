"""
Wrapper de ChromaDB para almacenar y buscar embeddings.
Singleton para reutilizar la conexión.
"""
import os
from typing import Optional
from uuid import UUID



class VectorStore:
    _instance: Optional["VectorStore"] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=os.getenv("CHROMA_PERSIST_DIR"))
            except Exception:
                self._client = None
        return self._client

    def _get_collection(self, client_id: UUID | str):
        client = self._get_client()
        if client is None:
            return None
        return client.get_or_create_collection(
            name=f"client_{client_id}",
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self, client_id: UUID | str, ids: list[str],
        embeddings: list[list[float]], metadatas: list[dict],
        documents: list[str],
    ) -> None:
        col = self._get_collection(client_id)
        if col is None:
            return
        col.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def query(
        self, client_id: UUID | str, query_embedding: list[float],
        n_results: int = 5, filter: Optional[dict] = None,
    ) -> list[dict]:
        col = self._get_collection(client_id)
        if col is None:
            return []
        result = col.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter,
        )
        out = []
        if not result["ids"] or not result["ids"][0]:
            return []
        for i, chunk_id in enumerate(result["ids"][0]):
            out.append({
                "id": chunk_id,
                "content": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i] if result.get("distances") else 1.0,
                "relevance_score": 1.0 - (result["distances"][0][i] if result.get("distances") else 0.0),
            })
        return out

    def delete_document(self, client_id: UUID | str, document_id: UUID) -> None:
        col = self._get_collection(client_id)
        if col is None:
            return
        col.delete(where={"document_id": str(document_id)})


vector_store = VectorStore()
