from typing import List, Dict
from config.llm_config import MODEL_MAP
from router.engine import RouterEngine
from router.models import Candidate

class ModelService:
    def __init__(self, candidates: List[Candidate],engine: RouterEngine):
        self.candidates = candidates
        self.health: Dict[str, bool] = {c.name: True for c in candidates}
        self.engine=engine
    # -------------------- 1. 健康列表 --------------------
    def get_available(self) -> List[Candidate]:
        return [c for c in self.candidates if self.health.get(c.name, True)]

    def set_health(self, name: str, healthy: bool):
        if name in self.health:
            self.health[name] = healthy

    # -------------------- 2. 真调用 --------------------
    def call(self, name: str, query: str, max_tokens: int) -> str:
        """
        直接返回模型文本，失败抛 RuntimeError（供降级链捕获）
        """
        client = MODEL_MAP[name]
        try:

            response=client.invoke(query, max_tokens=max_tokens).content
            if hasattr(response, "text"):
                text=response.text
            else:
                text=response
            if not text:
                raise RuntimeError(f"Model {name} returned empty response")


            return text
        except Exception as e:
            error_msg = f"Model '{name}' call failed: {str(e)}"

            raise RuntimeError(error_msg) from e

    # -------------------- 3. 真价格（2025-07 官网）--------------------
    def calc_cost(self, name: str, tokens: int) -> float:
        price_per_1k = self.engine.get_price(model_name= name)  # ← 读 YAML！
        return price_per_1k * tokens / 1000