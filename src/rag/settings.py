from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "")
    chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:8b")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    top_k: int = int(os.getenv("RAG_TOP_K", "10"))
    max_distance: float = float(os.getenv("RAG_MAX_DISTANCE", "0.65"))
    approved_only: bool = os.getenv("RAG_APPROVED_ONLY", "1").lower() in {"1","true","yes","on"}
    event_window_seconds: int = int(os.getenv("RAG_EVENT_WINDOW_SECONDS", "30"))
    output_dir: Path = ROOT / os.getenv("RAG_OUTPUT_DIR", "output/rag")

settings = Settings()
from pathlib import Path
import os
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2];load_dotenv(ROOT/'.env')
BASE=os.getenv('OLLAMA_BASE_URL','http://localhost:11434').rstrip('/');EMBED=os.getenv('OLLAMA_EMBED_MODEL','');CHAT=os.getenv('OLLAMA_CHAT_MODEL','qwen3:8b');DIM=int(os.getenv('EMBEDDING_DIMENSION','1024'))