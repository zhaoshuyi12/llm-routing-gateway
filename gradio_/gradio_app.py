# gradio_app.py
import gradio as gr
import requests
BACKEND_URL = "http://localhost:8000/v1/chat"
BASE_URL = "http://localhost:8000"

def route_query(query: str, user_tier: str):
    """
    调用你的 FastAPI 路由网关，返回结构化结果。
    """
    if not query.strip():
        return "请输入问题", "", "", "", ""

    try:
        payload = {
            "query": query.strip(),
            "user_id": "gradio_demo_user",
            "user_tier": user_tier.lower(),
            "temperature": 0.0,
            "max_tokens": 1000
        }

        response = requests.post(BACKEND_URL, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            answer = data.get("text", "无回答")
            model_used = data.get("model", "N/A")
            intent = data.get("intent", "unknown")
            cost = f"${data.get('cost', 0):.6f}"
            latency = f"{data.get('latency', 0):.3f} 秒"

            # 构建详细信息（用于展示）
            details = (
                f"**使用模型**: {model_used}\n"
                f"**识别意图**: {intent}\n"
                f"**调用成本**: {cost}\n"
                f"**响应延迟**: {latency}"
            )

            return answer, details, model_used, intent, cost
        else:
            error_msg = response.json().get("detail", "未知错误")
            return f"❌ 调用失败: {error_msg}", "", "", "", ""

    except requests.exceptions.ConnectionError:
        return "❌ 无法连接到后端服务，请确保 FastAPI 正在运行！", "", "", "", ""
    except Exception as e:
        return f"❌ 发生错误: {str(e)}", "", "", "", ""


def route_query_stream(query: str, user_tier: str):
    """
    流式读取后端结果并更新 UI
    """
    if not query.strip():
        # 返回默认占位符，保持输出长度与 outputs 列表一致
        yield "请输入问题", "N/A", "N/A", "N/A", "N/A"
        return

    payload = {
        "query": query.strip(),
        "user_tier": user_tier.lower(),
        "temperature": 0.0,
        "max_tokens": 1000
    }

    try:
        # 注意：这里调用的是我们上一阶段在 FastAPI 中新增的 /v1/stream_chat 接口
        with requests.post(f"{BASE_URL}/v1/stream_chat", json=payload, stream=True, timeout=60) as r:
            if r.status_code != 200:
                yield f"❌ 错误: {r.text}", "N/A", "N/A", "N/A", "N/A"
                return

            partial_text = ""
            # 这里的逻辑是逐块获取 AI 返回的文字并立即 yield 给 Gradio
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    decoded_chunk = chunk.decode("utf-8")
                    partial_text += decoded_chunk
                    # 依次对应 UI 中的 outputs：回答, 路由详情, 模型, 意图, 成本
                    yield partial_text, "⏳ 正在生成详情...", "正在确定...", "分析中...", "计算中..."

            # 生成结束后，最后可以发一次完整的状态（可选）
            yield partial_text, "✅ 生成完成", "已锁定", "已锁定", "已计算"

    except Exception as e:
        yield f"❌ 请求异常: {str(e)}", "N/A", "N/A", "N/A", "N/A"

# 自定义 CSS（可选：让界面更美观）
custom_css = """
.gradio-container { 
    max-width: 800px !important; 
    margin: auto;
}
#title {
    text-align: center;
    color: #4F46E5;
    font-weight: bold;
}
"""

with gr.Blocks(css=custom_css, title="LLM 路由网关") as demo:
    gr.Markdown(
        """
        # 🧠 智能 LLM 路由网关演示
        根据**用户等级**与**问题意图**，自动选择最优大语言模型（如 GPT-4、Claude、Kimi 等）。
        """,
        elem_id="title"
    )

    with gr.Row():
        with gr.Column(scale=3):
            query_input = gr.Textbox(
                label="📝 输入你的问题",
                placeholder="例如：'写一个二分查找算法' 或 '高血压吃什么药？'",
                lines=3
            )
            tier_input = gr.Radio(
                choices=["free", "basic", "premium"],
                value="premium",
                label="👤 用户等级"
            )
            submit_btn = gr.Button("🚀 发送查询", variant="primary")

        with gr.Column(scale=2):
            model_badge = gr.Textbox(label="🎯 使用的模型", interactive=False)
            intent_badge = gr.Textbox(label="🔍 识别意图", interactive=False)
            cost_badge = gr.Textbox(label="💰 成本", interactive=False)

    answer_output = gr.Textbox(label="💬 模型回答", interactive=False, lines=6)
    details_output = gr.Markdown(label="📊 路由详情")

    # 绑定事件
    submit_btn.click(
        fn=route_query_stream,
        inputs=[query_input, tier_input],
        outputs=[answer_output, details_output, model_badge, intent_badge, cost_badge]
    )

    # 支持回车发送
    query_input.submit(
        fn=route_query_stream,
        inputs=[query_input, tier_input],
        outputs=[answer_output, details_output, model_badge, intent_badge, cost_badge]
    )

    gr.Markdown(
        """
        ---
        💡 **提示**：  
        - **Free 用户** 可能被路由到低成本模型（如 DeepSeek）  
        - **Premium 用户** 优先使用高性能模型（如 GPT-4、Claude 3.5）  
        - 系统会根据问题类型（代码、医疗、通用等）智能选择最合适的模型
        """
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",  # 允许局域网访问（可选）
        server_port=6006,  # 默认端口
        share=False
    )