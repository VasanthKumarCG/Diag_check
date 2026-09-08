from __future__ import annotations
import hashlib
import json
import math
import requests
from .settings import settings

class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model = model or settings.embed_model
        if not model:
            raise RuntimeError("OLLAMA_EMBED_MODEL is not configured.")
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": model, "input": texts}, timeout=180,
        )
        if response.status_code == 404:
            vectors=[]
            for text in texts:
                old=requests.post(f"{self.base_url}/api/embeddings",json={"model":model,"prompt":text},timeout=180)
                old.raise_for_status(); vectors.append(old.json()["embedding"])
            return self._validate(vectors)
        response.raise_for_status()
        return self._validate(response.json()["embeddings"])

    def _validate(self, vectors: list[list[float]]) -> list[list[float]]:
        for vector in vectors:
            if len(vector) != settings.embedding_dimension:
                raise ValueError(f"Embedding dimension {len(vector)} does not match configured {settings.embedding_dimension}.")
        return vectors

    def chat_json(self, messages: list[dict], model: str | None = None) -> dict:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": model or settings.chat_model, "messages": messages, "stream": False, "format": "json"},
            timeout=300,
        )
        response.raise_for_status()
        return json.loads(response.json()["message"]["content"])

class DeterministicDummyEmbedder:
    """Offline test embedder. Never use for semantic-quality evaluation."""
    def embed(self, texts: list[str], model: str = "dummy-sha256") -> list[list[float]]:
        vectors=[]
        for text in texts:
            raw=hashlib.shake_256(text.encode("utf-8")).digest(settings.embedding_dimension * 4)
            vals=[]
            for i in range(settings.embedding_dimension):
                n=int.from_bytes(raw[i*4:(i+1)*4],"little")
                vals.append((n / 2**32) * 2 - 1)
            norm=math.sqrt(sum(v*v for v in vals)) or 1
            vectors.append([v/norm for v in vals])
        return vectors
