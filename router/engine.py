from typing import List

import yaml

from router.models import Candidate, UserTier, RouterRule, RouterConfig
import os
#获取当前所在文件路径
dir_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RouterEngine:
    def __init__(self,config_file:str="/config/router_config.yaml"):
        self.config_file=dir_path+config_file
        self.config: RouterConfig = self.load_config()
        self.candidates = self.get_all_candidates()

    def load_config(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return RouterConfig(**data)

    def get_all_candidates(self) -> List[Candidate]:
        """返回所有模型画像（来自 YAML）"""
        return list(self.config.models.values())


    def build_candidates_from_config(self)-> List[Candidate]:
        candidate=[]
        model_config=self.config.get('models',{})
        for model_name,model_info in model_config.items():
            candidate.append(Candidate(
                name=model_name,
                price_per_1k=model_info.get('price_per_1k',0),
                quality_score=model_info.get('quality_score',0),
                supported_intents=model_info.get('supported_intents',[]),
                max_rpm=model_info.get('max_rpm',0)
            ))
        return candidate

    def caculation_score(self,candidate:Candidate,user_tier:UserTier,intent:str)->float:
        quality_score = candidate.quality_score
        cost_score = 1 / (candidate.price_per_1k + 0.001)
        intent_score = 2.0 if intent in candidate.supported_intents else 0.
        weights={UserTier.Premium:(0.6,0.2,0.2),
                 UserTier.Basic:(0.4,0.4,0.2),
                 UserTier.Free:(0.3,0.5,0.2)}
        q_w,c_w,i_w=weights.get(user_tier)
        score=quality_score*q_w+cost_score*c_w+intent_score*i_w
        return score

    def _evaluate_rule(self, rule: RouterRule, intent: str, user_tier: UserTier) -> bool:
        cond = rule.condition
        if "intent == 'medical'" in cond and intent == "medical":
            return True
        if "intent == 'code'" in cond and intent == "code":
            return True
        if "user_tier == 'free'" in cond and user_tier == UserTier.Free:  # ← 关键！
            return True
        return False

    def select_model(self, candidates: List[Candidate], user_tier: UserTier, intent: str) -> str:
        # 1. 先走规则池
        for rule in self.config.rules:
            if self._evaluate_rule(rule, intent, user_tier):
                pool_names = rule.pool or [c.name for c in candidates]
                available = [c for c in candidates if c.name in pool_names]
                if available:
                    scored = [(c, self.caculation_score(c, user_tier, intent)) for c in available]
                    return max(scored, key=lambda x: x[1])[0].name

        # 2. 无规则命中 → 全局打分
        scored = [(c, self.caculation_score(c, user_tier, intent)) for c in candidates]
        return max(scored, key=lambda x: x[1])[0].name

    def select_fallback_model(self)->list[str]:
        print("fallback_chain",self.config.fallback_chain)
        fallback_chain=self.config.fallback_chain
        return fallback_chain

    def  get_price(self,model_name:str)->float:
        return self.config.models[model_name].price_per_1k