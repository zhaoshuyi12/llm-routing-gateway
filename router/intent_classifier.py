import re
from typing import Dict


class IntentRouter:
    def __init__(self):
        self.intent_patterns = {
            "medical": [
                r'诊断|治疗|症状|医院|医生|手术|药品|疾病|疫情|头疼|发热|痛|难受',
                r'medical|diagnosis|treatment|symptom|hospital|doctor'
            ],
            "code": [
                r'代码|编程|程序|python|java|C\+\+|函数|算法|bug|调试|报错',
                r'code|programming|function|algorithm|debug|API',
                r'```[\s\S]*?```|def\s+\w+\(|class\s+\w+'
            ],
            "chinese": [
                r'翻译|你好|中文|帮助',
                r'[\u4e00-\u9fff]{5,}'
            ],
            "emergency": [
                r'紧急|救命|危险|火灾|地震|急救|报警|火'
            ]
        }
        # 预编译加速
        self._cache = {k: [p.split('|') for p in v]
                       for k, v in self.intent_patterns.items()}

    def predict(self, text: str) -> str:
        text_lower = text.lower()
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.I):
                    return intent
        return "general"
