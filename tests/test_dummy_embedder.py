from src.rag.ollama_client import DeterministicDummyEmbedder
from src.rag.settings import settings

def test_dummy_embedding_is_deterministic_and_correct_dimension():
    e=DeterministicDummyEmbedder(); a=e.embed(["abc"])[0]; b=e.embed(["abc"])[0]
    assert a==b and len(a)==settings.embedding_dimension
