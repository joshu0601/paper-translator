"""Embedding provider abstraction (SPEC §58)."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from app.config import get_settings
from app.services.text import ZH_EN_HINTS, tokenize


class EmbeddingProvider(ABC):
    name: str = "base"
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, dimensions: int, base_url: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 64):
            batch = [t[:8000] for t in texts[i : i + 64]]
            res = self.client.embeddings.create(model=self.model, input=batch, dimensions=self.dimensions)
            out.extend(d.embedding for d in sorted(res.data, key=lambda d: d.index))
        return out


class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic feature-hashing bag-of-words (unigrams + bigrams) embedding.

    Not semantic, but it needs no network and makes retrieval and search work
    offline; swap for OpenAI embeddings in production."""

    name = "mock"

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def _vector(self, text: str, is_query: bool = False) -> list[float]:
        vec = np.zeros(self.dimensions, dtype=np.float32)
        toks = tokenize(text)
        if is_query:
            for zh, en in ZH_EN_HINTS.items():
                if zh in text:
                    toks.extend(tokenize(en))
        feats = toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]
        for f in feats:
            h = int(hashlib.md5(f.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimensions
            sign = 1.0 if (h >> 64) & 1 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text, is_query=True)


def build_embeddings(kind: str | None = None) -> EmbeddingProvider:
    s = get_settings()
    kind = kind or s.embedding_provider
    if kind == "openai":
        if not s.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddingProvider(s.openai_api_key, s.openai_embedding_model, s.openai_embedding_dimensions, s.openai_base_url)
    return HashingEmbeddingProvider(s.mock_embedding_dimensions)


@lru_cache
def get_embeddings() -> EmbeddingProvider:
    return build_embeddings()


def cosine_similarity(query: list[float], matrix: np.ndarray) -> np.ndarray:
    q = np.asarray(query, dtype=np.float32)
    qn = np.linalg.norm(q)
    if qn == 0 or matrix.size == 0:
        return np.zeros(len(matrix), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1.0
    return (matrix @ q) / (norms * qn)
