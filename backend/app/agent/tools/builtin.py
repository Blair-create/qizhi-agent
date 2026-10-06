from langchain_core.tools import tool

from infrastructure.rag import hand_book_vector_store


@tool
async def search_handbook(query: str) -> str:
    """查询员工手册及公司制度，每个请求最多调用一次。"""
    try:
        result = hand_book_vector_store.similarity_search(query, k=10)
    except Exception as exc:
        message = str(exc)
        if "ollama" in message.lower() or "11434" in message:
            return "知识库暂时不可用：请检查模型网关、模型配置和网络连接后重试。"
        raise
    if not result:
        return "未找到相关内容"
    return "\n\n".join(doc.page_content for doc in result)
