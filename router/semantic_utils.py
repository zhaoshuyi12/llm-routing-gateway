# semantic_cache.py
import asyncio
from typing import Optional, List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()

class SemanticMatcherFAISS:
    """
    基于 FAISS 的语义缓存器
    - 使用 query 作为检索 key
    - 缓存 result 作为返回值
    - 相似度 >= threshold 时命中
    """

    def __init__(
            self,
            embeddings: Optional[Embeddings] = None,
            threshold: float = 0.92,
    ):
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.threshold = threshold
        self._vectorstore: Optional[FAISS] = None
        self._lock = asyncio.Lock()  # 防止并发写冲突

    async def aadd(self, query: str, result: str) -> None:
        """异步添加 (query, result) 到语义缓存"""
        async with self._lock:
            doc = Document(
                page_content=result,
                metadata={"original_query": query}
            )
            if self._vectorstore is None:
                # 首次创建
                self._vectorstore = await FAISS.afrom_documents(
                    [doc], self.embeddings
                )
            else:
                # 增量添加
                self._vectorstore.add_documents([doc])

    async def afind_match(self, query: str) -> Optional[str]:
        """异步查找语义最相似的缓存结果"""
        if self._vectorstore is None:
            return None

        # 使用 similarity_search_with_relevance_scores
        # 返回 [(doc, score), ...]，score 是余弦相似度（0~1）
        docs_and_scores = await self._vectorstore.asimilarity_search_with_relevance_scores(
            query,
            k=1,
            score_threshold=self.threshold  # 只返回 >= threshold 的结果
        )

        if docs_and_scores:
            best_doc, best_score = docs_and_scores[0]
            print(f"🎯 语义缓存命中！相似度: {best_score:.4f}")
            return best_doc.page_content

        return None

    async def ainvoke(self, query: str, generate_func) -> str:
        """
        智能调用：先查缓存，未命中则调用 generate_func 并自动缓存

        Args:
            query: 用户查询文本
            generate_func: 异步函数，用于生成结果（当缓存未命中时调用）

        Returns:
            缓存结果 或 新生成的结果
        """
        cached = await self.afind_match(query)
        if cached is not None:
            return cached

        # 未命中，生成新结果
        result = await generate_func()
        await self.aadd(query, result)
        return result