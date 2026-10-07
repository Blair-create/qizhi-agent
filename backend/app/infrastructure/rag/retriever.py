import chromadb
import urllib.request
import json
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from core.config import settings

client = chromadb.PersistentClient(path=settings.CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
class OllamaEmbeddings:
    """Minimal LangChain embedding adapter for the local Ollama API."""

    def _embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text}).encode()
        request = urllib.request.Request(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read()).get("embedding", [])

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


embeddings = OllamaEmbeddings()
hand_book_vector_store = Chroma(
    collection_name="handbook", persist_directory=settings.CHROMA_PATH,
    embedding_function=embeddings, client=client, create_collection_if_not_exists=True,
)
