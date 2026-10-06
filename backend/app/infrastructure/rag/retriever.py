import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from core.config import settings

client = chromadb.PersistentClient(path=settings.CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
embeddings = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
hand_book_vector_store = Chroma(
    collection_name="handbook", persist_directory=settings.CHROMA_PATH,
    embedding_function=embeddings, client=client, create_collection_if_not_exists=True,
)
