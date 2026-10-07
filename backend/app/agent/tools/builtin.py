from langchain_core.tools import tool

from core.config import settings
from infrastructure.rag import hand_book_vector_store


@tool
async def search_handbook(query: str) -> str:
    """查询员工手册及公司制度，每个请求最多调用一次。"""
    try:
        result = hand_book_vector_store.similarity_search(query, k=10)
    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        if any(marker in lowered for marker in ("ollama", "11434", "model_not_found", "no available channel", "embedding")):
            return ("知识库暂时不可用：当前配置的向量模型 "
                    f"“{settings.OLLAMA_EMBEDDING_MODEL}”在 Ollama 中不可用，"
                    "请确认 Ollama 已启动并执行 ollama pull bge-m3。")
        raise
    if not result:
        return "未找到相关内容"
    return "\n\n".join(doc.page_content for doc in result)
