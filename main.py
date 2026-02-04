# main.py
import time
from fastapi import FastAPI, HTTPException

# -------------------- 内部模块 --------------------
from router.models import UserTier, Candidate, ChatResponse, ChatRequest
from router.intent_classifier import IntentRouter
from router.engine import RouterEngine
from router.model_service import ModelService
from router.cache import SmartCache, CacheKeyGenerator
from fastapi.responses import StreamingResponse

from router.semantic_utils import SemanticMatcherFAISS

# -------------------- 初始化 --------------------
app = FastAPI(title="智能大模型路由网关（YAML价格+真调用）", version="2.0")

engine        = RouterEngine()                       # 读 YAML
intent_cls    = IntentRouter()
model_svc     = ModelService(engine.get_all_candidates(), engine)  # 注入引擎→读价格
cache         = SmartCache(max_size=5000, default_ttl=1800)
cache.start_cleanup_task(interval=600)               # 后台 10 分钟清一次
# 初始化语义匹配器
semantic_matcher = SemanticMatcherFAISS(threshold=0.95)
@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.time()

    # 1. 意图识别
    intent = intent_cls.predict(req.query)

    # 2. 缓存键
    cache_key=None
    if req.temperature==0.0:
        cache_key = CacheKeyGenerator.generate_key(
           query=req.query,temperature=req.temperature,user_tier=req.user_tier)
        hit = cache.get(cache_key)
        if hit is not None:
            return ChatResponse(
                text=hit, model="cache", cost=0.0,
                latency=round(time.time() - start, 3), intent=intent)
    semantic_hit=semantic_matcher.afind_match(req.query)
    if semantic_hit:
        return ChatResponse(
            text=semantic_hit, model="SemanticCache", cost=0.0,latency=round(time.time() - start, 3))
    # 3. 选模型（读 YAML 价格 & 规则）
    primary = engine.select_model(
        model_svc.get_available(), req.user_tier, intent)
    all_candidates = [primary] + [
        m for m in engine.select_fallback_model()
        if m != primary  # 避免重复
    ]
    # 4. 真调用 + 成本（价格来自 YAML）
    actual_model=None
    text=None
    print(all_candidates)   
    for  model_name in all_candidates:
        try:
            text    =  await model_svc.call(model_name, req.query, req.max_tokens)
            actual_model = model_name
            break
        except:
            continue
    print(actual_model)
    cost    = model_svc.calc_cost(actual_model, req.max_tokens)
    latency = time.time() - start

    # 5. 回写缓存
    if cache_key:
        #根据意图设置缓存过期时间
        cache.set_with_intent(cache_key, text, intent)
    cache.set(cache_key, text)
    await semantic_matcher.aadd(req.query,text)
    return ChatResponse(
        text=text, model=actual_model, cost=round(cost, 6),
        latency=round(latency, 3), intent=intent)

# -------------------- 调试/管理接口 --------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "available_models": len(model_svc.get_available()),
        "cache_stats": cache.get_stats()
    }

@app.get("/debug/route")
async def debug_route(query: str, user_tier: UserTier = UserTier.Free):
    intent = intent_cls.predict(query)
    scored = [(c.name, engine.caculation_score(c,user_tier, intent))
              for c in model_svc.get_available()]
    scored.sort(key=lambda x: x[1], reverse=True)
    return {"query": query, "intent": intent, "scored": scored}

@app.post("/admin/set_health")
async def set_health(model: str, healthy: bool):
    model_svc.set_health(model, healthy)
    return {"message": f"{model} health set to {healthy}"}

@app.post("/cache/clear")
async def cache_clear():
    cache.clear()
    return {"message": "cache cleared"}
@app.get("/v1/steam_chat")
async def steam_chat(query: str, user_tier: UserTier = UserTier.Free):
    intent=intent_cls.predict(query)
    target_model=engine.select_model(model_svc.get_available(), user_tier, intent)
    return StreamingResponse(model_svc.steam_call(target_model, query, 1000),
                             media_type='text/event-stream')
# -------------------- 启动 --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)