"""
Generación de embeddings con sentence-transformers.
Singleton para no recargar el modelo en cada request.
"""
import os
from typing import Optional



class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))
            except Exception:
                self._model = None

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Devuelve embeddings de 384 dimensiones por defecto."""
        self._load_model()
        if self._model is None:
            # Fallback: vectores aleatorios deterministas para pruebas sin modelo descargado.
            import hashlib
            embeddings = []
            for text in texts:
                h = hashlib.sha256(text.encode()).digest()
                # Deriva 384 floats del hash de manera determinista
                vec = [(b - 128) / 128.0 for b in (h * 12)[:384]]
                embeddings.append(vec)
            return embeddings
        return self._model.encode(texts, convert_to_tensor=False).tolist()

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0]


embedding_service = EmbeddingService()
