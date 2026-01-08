import time
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from enum import Enum
class UserTier(str,Enum):
    Free="free"
    Basic="basic"
    Premium="premium"
class ChatRequest(BaseModel):
    query: str
    user_id: str
    user_tier: UserTier = UserTier.Free
    max_tokens: int = 1000
    temperature: float = 0.0
class ChatResponse(BaseModel):
    text: str
    model: str
    cost: float
    latency: float
    intent: Optional[str] = None

class Candidate(BaseModel):
    name: str
    price_per_1k: float  # 每千tokens价格
    quality_score: float  # 质量评分 0-1
    supported_intents: List[str]  # 支持的意图
    max_rpm: int  # 最大请求数/分钟
class RouterRule(BaseModel):
    """路由规则（比 Dict 更安全）"""
    name: str
    condition: str
    pool: List[str]


class RouterConfig(BaseModel):
    """完整的路由配置（YAML 结构）"""
    models: Dict[str, Candidate]
    default_model: str
    fallback_chain: List[str] = Field(default_factory=list)
    rules: List[RouterRule] = Field(default_factory=list)

class CacheItem(BaseModel):
    values: Any
    expires_at: float
    created_at: float
    access_count: int=0

    def is_expired(self) -> bool:
        return self.expires_at < time.time()

    def time_until_expiration(self) -> float:
        return max(0, self.expire_at - time.time())
