"""
Procesamiento de PDFs: extracción de texto por página y chunking.
Patrón Strategy para los algoritmos de chunking.
"""
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Iterator


class IChunker(ABC):
    @abstractmethod
    def chunk(self, pages: list[tuple[int, str]]) -> list[dict]:
        """Devuelve [{content, page_number, tokens, chunk_index}]"""
        ...


class FixedSizeChunker(IChunker):
    """Divide en chunks de tamaño fijo con overlap."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, pages: list[tuple[int, str]]) -> list[dict]:
        chunks = []
        chunk_index = 0
        for page_num, text in pages:
            words = text.split()
            i = 0
            while i < len(words):
                chunk_words = words[i:i + self.chunk_size]
                if not chunk_words:
                    break
                content = " ".join(chunk_words)
                chunks.append({
                    "content": content,
                    "page_number": page_num,
                    "tokens": len(chunk_words),
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
                i += self.chunk_size - self.overlap
        return chunks


class SemanticChunker(IChunker):
    """Divide por párrafos / secciones (heurística simple)."""

    def chunk(self, pages: list[tuple[int, str]]) -> list[dict]:
        chunks = []
        chunk_index = 0
        for page_num, text in pages:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for para in paragraphs:
                if len(para) < 50:
                    continue
                chunks.append({
                    "content": para,
                    "page_number": page_num,
                    "tokens": len(para.split()),
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
        return chunks


def extract_pages(file_bytes: bytes) -> list[tuple[int, str]]:
    """Devuelve [(page_number, text)] por cada página del PDF."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((i, text))
        return pages
    except Exception:
        return []


def get_chunker(strategy: str = "fixed") -> IChunker:
    if strategy == "semantic":
        return SemanticChunker()
    return FixedSizeChunker()
