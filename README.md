# 智能大模型路由网关 (Intelligent LLM Routing Gateway)

> 一个轻量级、高性能、可配置的大模型智能调度系统，解决多模型调用中的 **成本高、供应商单点故障、重复请求浪费** 三大痛点。

通过 **用户等级感知 + 意图识别 + 语义缓存 + 自动降级**，实现“该贵时贵，该省时省”的智能调度策略。

[![Demo](https://img.shields.io/badge/Demo-Gradio_Interface-blue?logo=gradio)](#-在线演示)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)

---

## 🔑 核心特性

### 1. **智能路由引擎**
- 基于 **用户等级**（Free / Basic / Premium）和 **业务意图**（Code / Medical / General）动态选择模型
- 三维度加权评分：**质量分 × 权重 + 成本效益 × 权重 + 意图匹配**
- 支持 YAML 配置模型画像（价格、质量、支持意图、RPM 限制）

### 2. **语义缓存（Semantic Caching）**
- 使用 OpenAI Embedding 生成查询向量
- 基于 NumPy 计算余弦相似度（默认阈值 `0.92`）
- 对“字面不同但语义相近”请求（如“怎么退款？” vs “如何退钱？”）自动复用历史结果
- ⚠️ **仅缓存公共意图查询**，避免跨用户数据泄露

### 3. **容错与降级**
- 配置静态 `fallback_chain`（如 `["kimi-k2-0711-preview", "gpt-4.1", "claude-3-7-sonnet-20250219","qwen-max-2025-01-25"]`）
- 主模型失败（429/5xx）时自动切换备选，保障服务可用性

### 4. **流式响应 & 异步架构**
- 基于 FastAPI + `StreamingResponse` 实现 **首字毫秒级返回**
- 全链路异步处理，避免大模型长 IO 阻塞

```bash
pip install -r requirements.txt
