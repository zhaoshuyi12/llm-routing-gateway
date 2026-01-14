from typing import Tuple, List, Optional
import numpy as np
from langchain_community.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()


class SemanticMatcher:

    def __init__(self,threshold:float=0.92):
        self.embeddings_model = OpenAIEmbeddings()
        self.threshold=threshold
        self.vector_store:List[Tuple[np.ndarray,str]]=[]
    async def get_embeddings(self,text:str)->np.ndarray:
        #将文本转成向量
        return  np.array(await self.embeddings_model.aembed_query(text))#异步将文本转成向量

    def find_match(self, query_vector: np.ndarray) -> Optional[str]:
        if not self.vector_store:
            return None

        # 计算余弦相似度
        best_score = -1
        best_result = None

        for vec, res in self.vector_store:
            # 余弦相似度公式: (A·B) / (||A||*||B||)
            score = np.dot(query_vector, vec) / (np.linalg.norm(query_vector) * np.linalg.norm(vec))
            if score > best_score:
                best_score = score
                best_result = res

        if best_score >= self.threshold:
            print(f"🎯 语义缓存命中！相似度: {best_score:.4f}")
            return best_result
        return None

    def add(self, vector: np.ndarray, result: str):
        self.vector_store.append((vector, result))