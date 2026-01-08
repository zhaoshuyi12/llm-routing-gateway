# 智能大模型路由网关 (Intelligent LLM Routing Gateway)

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)

这是一个基于 **YAML 配置驱动**的智能大模型路由网关。它能够根据用户等级、查询意图和成本效益，动态地从多个大语言模型（LLM）中选择最优模型进行调用，并内置了智能缓存机制以提升性能和降低成本。

## 🌟 核心特性

- **意图识别**: 自动分析用户查询的意图（如 `code`, `medical`, `chinese` 等），并据此路由到最合适的模型。
- **动态模型路由**: 基于 YAML 配置文件，结合用户等级（Free, Basic, Premium）、意图和模型画像（价格、质量、支持意图）进行智能打分和选择。
- **降级策略**: 当首选模型不可用时，自动按预设的降级链（Fallback Chain）尝试其他模型，保障服务高可用。
- **智能缓存**: 对确定性请求（`temperature=0.0`）进行缓存，并根据意图设置不同的TTL（例如，代码问题缓存24小时，医疗问题不缓存）。
- **真实成本计算**: 调用后根据实际使用的模型和Token数量，返回精确的成本（价格来源于YAML配置）。
- **健康检查与管理**: 提供 `/health` 端点监控服务状态，并可通过管理接口动态调整模型健康状况。
- **交互式演示**: 内置 **Gradio Web UI**，可直观体验路由逻辑与模型效果。
## 📦 技术栈

- **框架**: FastAPI
- **配置**: Pydantic + YAML
- **缓存**: 自定义线程安全的 `SmartCache`
- **意图分类**: 基于正则表达式的轻量级 `IntentRouter`

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn pydantic pyyaml langchain-openai gradio
