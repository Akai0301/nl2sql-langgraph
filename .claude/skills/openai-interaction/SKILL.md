---
name: openai-interaction
description: |
  基于 Python OpenAI SDK 的模型交互开发指南。支持对话、多模态、流式输出、函数调用、异步客户端等。

  触发场景：
  - 使用 OpenAI API 进行对话交互
  - 实现多模态输入（图片、音频）
  - 实现流式输出（Streaming）
  - 使用 Function Calling / Tool Use
  - 集成 OpenAI 兼容 API（如第三方代理、本地模型）
  - 异步调用 OpenAI 模型

  触发词：OpenAI、GPT、openai、ChatCompletion、流式输出、streaming、多模态、function calling、tool use、AI对话、模型交互、LLM调用

  核心警告：
  - 必须使用 openai>=2.0.0（v2.x 版本），v1.x 已停止维护
  - 异步客户端使用 AsyncOpenAI，同步客户端使用 OpenAI
  - 流式输出必须正确处理 chunk 迭代
  - API Key 禁止硬编码，必须使用环境变量
---

# OpenAI Python SDK 模型交互指南

> 适用版本：`openai>=2.0.0`（当前最新 v2.23.0）
> 官方仓库：https://github.com/openai/openai-python

## 快速索引

| 功能 | 章节 | 关键类/方法 |
|------|------|------------|
| 安装与版本 | 一 | `pip install openai>=2.0.0` |
| 客户端初始化 | 二 | `OpenAI()` / `AsyncOpenAI()` |
| 基础对话 | 三 | `client.chat.completions.create()` |
| 流式输出 | 四 | `stream=True` / `async for chunk` |
| 多模态输入 | 五 | `image_url` / `base64` 图片消息 |
| 函数调用 | 六 | `tools` / `tool_choice` |
| 异步集成 | 七 | `AsyncOpenAI` + FastAPI |
| 兼容 API | 八 | `base_url` 自定义端点 |
| 错误处理 | 九 | `openai.APIError` 异常体系 |
| 版本迁移 | 十 | v1→v2 破坏性变更 |

---

## 一、安装与版本要求

### 1.1 安装

```bash
# 安装最新版本（v2.x）
pip install openai>=2.0.0

# 指定精确版本
pip install openai==2.23.0

# 如果项目使用 requirements.txt
echo "openai>=2.0.0" >> requirements.txt
```

### 1.2 版本说明

| 版本范围 | 状态 | 说明 |
|---------|------|------|
| `v2.x` (>=2.0.0) | **当前版本** | 支持 Responses API、GPT-5 系列 |
| `v1.x` (1.0-1.109) | 维护中 | Chat Completions API、Assistants API |
| `v0.28.x` | **已废弃** | 旧版全局调用方式，禁止使用 |

### 1.3 Python 版本要求

```
Python >= 3.8（推荐 3.10+）
```

> **注意**：本项目使用 Python 3.9+，与 OpenAI SDK v2.x 完全兼容。

---

## 二、客户端初始化

### 2.1 同步客户端

```python
from openai import OpenAI

# 方式一：从环境变量读取（推荐）
# 自动读取 OPENAI_API_KEY 环境变量
client = OpenAI()

# 方式二：显式传入参数
client = OpenAI(
    api_key="sk-xxx",  # 仅用于示例，实际禁止硬编码
    timeout=30.0,       # 请求超时（秒）
    max_retries=3,      # 最大重试次数
)
```

### 2.2 异步客户端（FastAPI 项目推荐）

```python
from openai import AsyncOpenAI

# 异步客户端，适用于 FastAPI 异步环境
client = AsyncOpenAI()

# 显式参数
client = AsyncOpenAI(
    api_key="sk-xxx",
    timeout=60.0,
    max_retries=2,
)
```

### 2.3 自定义 base_url（兼容第三方 API）

```python
from openai import OpenAI, AsyncOpenAI

# 同步 - 使用第三方兼容 API
client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.example.com/v1",  # 自定义端点
)

# 异步 - 使用第三方兼容 API
client = AsyncOpenAI(
    api_key="your-api-key",
    base_url="https://api.example.com/v1",
)
```

### 2.4 环境变量配置

```bash
# .env 文件
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_BASE_URL=http://aiserver.hisi.huawei.com/v1   # 可选，默认官方地址
OPENAI_TIMEOUT=30                             # 可选，超时秒数
```

```python
import os
from openai import AsyncOpenAI

# 从项目配置读取
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://aiserver.hisi.huawei.com/v1"),
    timeout=float(os.getenv("OPENAI_TIMEOUT", "30")),
)
```

---

## 三、基础对话（Chat Completions）

### 3.1 同步调用

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个有用的助手。"},
        {"role": "user", "content": "你好，请介绍一下你自己。"},
    ],
    temperature=0.7,      # 创造性（0-2，默认1）
    max_tokens=1000,       # 最大输出 token 数
    top_p=1.0,             # 核采样
)

# 获取回复内容
reply = response.choices[0].message.content
print(reply)

# 获取 token 使用量
print(f"输入: {response.usage.prompt_tokens}")
print(f"输出: {response.usage.completion_tokens}")
print(f"总计: {response.usage.total_tokens}")
```

### 3.2 异步调用（FastAPI 项目推荐）

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def chat(user_message: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content
```

### 3.3 多轮对话

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def multi_turn_chat(history: list[dict], user_message: str) -> tuple[str, list[dict]]:
    """
    多轮对话，维护消息历史

    :param history: 消息历史列表
    :param user_message: 用户新消息
    :return: (AI回复, 更新后的历史)
    """
    # 添加用户消息
    history.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=history,
    )

    assistant_message = response.choices[0].message.content

    # 添加助手回复到历史
    history.append({"role": "assistant", "content": assistant_message})

    return assistant_message, history


# 使用示例
async def example():
    history = [{"role": "system", "content": "你是一个有用的助手。"}]
    reply, history = await multi_turn_chat(history, "你好")
    reply, history = await multi_turn_chat(history, "刚才我说了什么？")
```

### 3.4 常用参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | str | 必填 | 模型名称（gpt-4o, gpt-4o-mini, gpt-5 等） |
| `messages` | list | 必填 | 消息列表 |
| `temperature` | float | 1.0 | 创造性，0=确定性，2=最随机 |
| `max_tokens` | int | 模型默认 | 最大输出 token 数 |
| `top_p` | float | 1.0 | 核采样阈值 |
| `stream` | bool | False | 是否流式输出 |
| `tools` | list | None | 函数调用工具定义 |
| `tool_choice` | str/dict | "auto" | 工具选择策略 |
| `response_format` | dict | None | 响应格式（如 JSON mode） |
| `n` | int | 1 | 生成候选数量 |
| `stop` | str/list | None | 停止序列 |
| `seed` | int | None | 随机种子（可复现） |

---

## 四、流式输出（Streaming）

### 4.1 同步流式

```python
from openai import OpenAI

client = OpenAI()

stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "写一首关于春天的诗"},
    ],
    stream=True,
)

# 逐块输出
for chunk in stream:
    content = chunk.choices[0].delta.content
    if content is not None:
        print(content, end="", flush=True)
print()  # 换行
```

### 4.2 异步流式（FastAPI 推荐）

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def stream_chat(user_message: str):
    """异步流式对话"""
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    full_response = ""
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content is not None:
            full_response += content
            yield content  # 逐块返回

    return full_response
```

### 4.3 FastAPI SSE 流式接口

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

client = AsyncOpenAI()
chatController = APIRouter(prefix='/ai/chat')


@chatController.post('/stream')
async def stream_chat_api(request: dict):
    """流式对话接口，返回 SSE 格式"""
    user_message = request.get("message", "")

    async def generate():
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一个有用的助手。"},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield f"data: {content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

### 4.4 流式输出数据结构

```python
# 每个 chunk 的结构：
# ChatCompletionChunk(
#     id='chatcmpl-xxx',
#     choices=[
#         Choice(
#             delta=ChoiceDelta(
#                 content='你',      # 增量文本内容（可能为 None）
#                 role='assistant',  # 仅第一个 chunk 有
#                 tool_calls=None,   # 函数调用增量
#             ),
#             finish_reason=None,    # 最后一个 chunk 为 'stop'
#             index=0,
#         )
#     ],
#     model='gpt-4o',
# )
```

### 4.5 流式输出完整收集

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def stream_and_collect(messages: list[dict]) -> str:
    """流式输出并收集完整响应"""
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        stream=True,
    )

    collected_content = []
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content is not None:
            collected_content.append(delta.content)

        # 检查是否结束
        if chunk.choices[0].finish_reason == "stop":
            break

    return "".join(collected_content)
```

---

## 五、多模态输入

### 5.1 图片 URL 输入

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def analyze_image_url(image_url: str, question: str) -> str:
    """通过 URL 分析图片"""
    response = await client.chat.completions.create(
        model="gpt-4o",  # 必须使用支持视觉的模型
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": "high",  # low / high / auto
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content
```

### 5.2 Base64 图片输入

```python
import base64
from pathlib import Path
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def analyze_local_image(image_path: str, question: str) -> str:
    """分析本地图片文件"""
    # 读取图片并转为 base64
    image_data = Path(image_path).read_bytes()
    base64_image = base64.b64encode(image_data).decode("utf-8")

    # 根据文件后缀确定 MIME 类型
    suffix = Path(image_path).suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/png")

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content
```

### 5.3 多图片输入

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def compare_images(image_urls: list[str], question: str) -> str:
    """多图片对比分析"""
    content = [{"type": "text", "text": question}]

    for url in image_urls:
        content.append({
            "type": "image_url",
            "image_url": {"url": url, "detail": "high"},
        })

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=2000,
    )
    return response.choices[0].message.content
```

### 5.4 图片 detail 参数说明

| 值 | 说明 | Token 消耗 |
|----|------|-----------|
| `low` | 低分辨率（512x512） | 固定 85 tokens |
| `high` | 高分辨率（原图） | 按图片尺寸计算 |
| `auto` | 自动选择 | 模型自行决定 |

---

## 六、函数调用（Function Calling / Tool Use）

### 6.1 定义工具

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位",
                    },
                },
                "required": ["city"],
            },
        },
    }
]
```

### 6.2 处理工具调用

```python
import json
from openai import AsyncOpenAI

client = AsyncOpenAI()


# 实际的函数实现
async def get_weather(city: str, unit: str = "celsius") -> dict:
    """模拟获取天气（实际项目中调用真实 API）"""
    return {"city": city, "temperature": 22, "unit": unit, "condition": "晴天"}


async def chat_with_tools(user_message: str) -> str:
    """带函数调用的对话"""
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以查询天气。"},
        {"role": "user", "content": user_message},
    ]

    # 第一次调用：模型决定是否调用工具
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto / none / required / {"type": "function", "function": {"name": "xxx"}}
    )

    assistant_message = response.choices[0].message

    # 检查是否需要调用工具
    if assistant_message.tool_calls:
        # 将助手消息添加到历史
        messages.append(assistant_message)

        # 逐个执行工具调用
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # 根据函数名分发调用
            if function_name == "get_weather":
                result = await get_weather(**function_args)
            else:
                result = {"error": f"未知函数: {function_name}"}

            # 将工具结果添加到消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        # 第二次调用：模型根据工具结果生成最终回复
        final_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return final_response.choices[0].message.content

    # 不需要工具调用，直接返回
    return assistant_message.content
```

### 6.3 tool_choice 参数

| 值 | 说明 |
|----|------|
| `"auto"` | 模型自行决定是否调用工具（默认） |
| `"none"` | 禁止调用工具 |
| `"required"` | 强制至少调用一个工具 |
| `{"type": "function", "function": {"name": "xxx"}}` | 强制调用指定函数 |

### 6.4 并行工具调用

```python
# 模型可能同时返回多个 tool_calls
# 例如用户说"查北京和上海的天气"
# assistant_message.tool_calls 会包含两个调用：
# [
#   ToolCall(id="call_1", function=Function(name="get_weather", arguments='{"city":"北京"}')),
#   ToolCall(id="call_2", function=Function(name="get_weather", arguments='{"city":"上海"}')),
# ]
# 必须为每个 tool_call 都返回结果（role="tool", tool_call_id 必须匹配）
```

---

## 七、异步集成到 FastAPI

### 7.1 Service 层封装

```python
"""
OpenAI 交互服务层
位置建议：module_xxx/service/openai_service.py
"""
import os
import json
from openai import AsyncOpenAI
from utils.log_util import logger


class OpenAIService:
    """OpenAI 模型交互服务"""

    # 客户端单例（模块级别初始化）
    _client: AsyncOpenAI = None

    @classmethod
    def get_client(cls) -> AsyncOpenAI:
        """获取或创建 AsyncOpenAI 客户端（单例）"""
        if cls._client is None:
            cls._client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "http://aiserver.hisi.huawei.com/v1"),
                timeout=float(os.getenv("OPENAI_TIMEOUT", "60")),
                max_retries=2,
            )
        return cls._client

    @classmethod
    async def chat(cls, messages: list[dict], model: str = "gpt-4o", **kwargs) -> str:
        """
        基础对话

        :param messages: 消息列表
        :param model: 模型名称
        :return: AI 回复内容
        """
        client = cls.get_client()
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI 调用失败: {e}")
            raise

    @classmethod
    async def stream_chat(cls, messages: list[dict], model: str = "gpt-4o", **kwargs):
        """
        流式对话（异步生成器）

        :param messages: 消息列表
        :param model: 模型名称
        :yield: 增量文本内容
        """
        client = cls.get_client()
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
        except Exception as e:
            logger.error(f"OpenAI 流式调用失败: {e}")
            raise
```

### 7.2 Controller 层接口

```python
"""
OpenAI 对话控制器
位置建议：module_xxx/controller/openai_controller.py
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from module_xxx.service.openai_service import OpenAIService
from utils.response_util import ResponseUtil


openaiController = APIRouter(prefix='/ai/openai')


class ChatRequest(BaseModel):
    """对话请求模型"""
    message: str = Field(description="用户消息")
    model: str = Field(default="gpt-4o", description="模型名称")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    history: Optional[list[dict]] = Field(default=None, description="对话历史")


@openaiController.post('/chat')
async def chat(request: ChatRequest):
    """普通对话接口"""
    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    if request.history:
        messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})

    reply = await OpenAIService.chat(messages, model=request.model)
    return ResponseUtil.success(data={"reply": reply})


@openaiController.post('/chat/stream')
async def stream_chat(request: ChatRequest):
    """流式对话接口（SSE）"""
    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    if request.history:
        messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})

    async def generate():
        async for content in OpenAIService.stream_chat(messages, model=request.model):
            yield f"data: {content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

---

## 八、兼容第三方 API

### 8.1 兼容 API 列表

OpenAI Python SDK 可通过 `base_url` 连接任何 OpenAI 兼容的 API：

| 提供商 | base_url 示例 | 说明 |
|--------|--------------|------|
| OpenAI 官方 | `http://aiserver.hisi.huawei.com/v1` | 默认 |
| Azure OpenAI | `https://{endpoint}.openai.azure.com/openai/deployments/{model}/` | 需额外 api-version |
| 第三方代理 | `https://api.proxy.com/v1` | API Key 格式可能不同 |
| 本地模型 | `http://localhost:8000/v1` | Ollama、vLLM、LM Studio 等 |

### 8.2 连接本地模型（Ollama）

```python
from openai import AsyncOpenAI

# Ollama 本地服务（默认端口 11434）
client = AsyncOpenAI(
    api_key="ollama",               # Ollama 不需要真实 key
    base_url="http://localhost:11434/v1",
)

async def local_chat(message: str) -> str:
    response = await client.chat.completions.create(
        model="llama3.1",  # Ollama 中的模型名称
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content
```

### 8.3 连接 vLLM

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
)

async def vllm_chat(message: str) -> str:
    response = await client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content
```

### 8.4 Azure OpenAI

```python
from openai import AsyncAzureOpenAI

# Azure OpenAI 使用专用客户端
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  # https://xxx.openai.azure.com/
)

async def azure_chat(message: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o",  # Azure 中的部署名称
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content
```

---

## 九、错误处理

### 9.1 异常类型

```python
import openai

# 异常继承体系：
# openai.APIError（基类）
#   ├── openai.APIConnectionError      # 网络连接错误
#   ├── openai.RateLimitError          # 速率限制（429）
#   ├── openai.APIStatusError（基类）
#   │   ├── openai.AuthenticationError  # 认证失败（401）
#   │   ├── openai.PermissionDeniedError # 权限不足（403）
#   │   ├── openai.NotFoundError       # 资源不存在（404）
#   │   ├── openai.UnprocessableEntityError # 参数错误（422）
#   │   ├── openai.ConflictError       # 冲突（409）
#   │   └── openai.InternalServerError # 服务器错误（500）
#   └── openai.APITimeoutError         # 请求超时
```

### 9.2 错误处理最佳实践

```python
import openai
from openai import AsyncOpenAI
from utils.log_util import logger

client = AsyncOpenAI()


async def safe_chat(messages: list[dict]) -> str:
    """带完整错误处理的对话"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return response.choices[0].message.content

    except openai.AuthenticationError:
        logger.error("OpenAI API Key 无效或已过期")
        raise ServiceException(message="AI 服务认证失败，请联系管理员")

    except openai.RateLimitError:
        logger.warning("OpenAI API 速率限制，请稍后重试")
        raise ServiceException(message="AI 服务繁忙，请稍后重试")

    except openai.APIConnectionError:
        logger.error("无法连接到 OpenAI API")
        raise ServiceException(message="AI 服务连接失败，请检查网络")

    except openai.APITimeoutError:
        logger.error("OpenAI API 请求超时")
        raise ServiceException(message="AI 服务响应超时，请重试")

    except openai.APIStatusError as e:
        logger.error(f"OpenAI API 错误: {e.status_code} - {e.message}")
        raise ServiceException(message=f"AI 服务异常: {e.message}")

    except Exception as e:
        logger.error(f"OpenAI 调用异常: {e}")
        raise
```

### 9.3 重试策略

```python
from openai import AsyncOpenAI

# SDK 内置重试（推荐）
client = AsyncOpenAI(
    max_retries=3,  # 自动重试 3 次（针对 429、5xx 错误）
    timeout=60.0,
)

# 如需自定义重试逻辑
import asyncio


async def chat_with_retry(messages: list[dict], max_attempts: int = 3) -> str:
    """自定义重试逻辑"""
    for attempt in range(max_attempts):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
            return response.choices[0].message.content
        except openai.RateLimitError:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                logger.warning(f"速率限制，{wait_time}秒后重试（第{attempt + 1}次）")
                await asyncio.sleep(wait_time)
            else:
                raise
```

---

## 十、版本迁移注意事项

### 10.1 v0.28 → v1.x（大版本迁移）

```python
# ❌ v0.28 旧写法（已废弃，禁止使用）
import openai
openai.api_key = "sk-xxx"
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "hello"}],
)

# ✅ v1.x+ 新写法
from openai import OpenAI
client = OpenAI(api_key="sk-xxx")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "hello"}],
)
```

### 10.2 v1.x → v2.x（破坏性变更）

v2.0.0 的主要破坏性变更：

1. **Tool Call 输出类型变化**：`ResponseFunctionToolCallOutputItem.output` 从 `string` 变为 `string | Array<ResponseInputText | ResponseInputImage | ResponseInputFile>`

```python
# ❌ v1.x 假设 output 总是字符串
output_text = tool_call_output.output  # 可能不再是纯字符串

# ✅ v2.x 安全处理
if isinstance(tool_call_output.output, str):
    output_text = tool_call_output.output
else:
    # 处理多模态输出
    output_text = str(tool_call_output.output)
```

2. **Agents SDK 要求**：OpenAI Agents SDK 现在要求 `openai>=2.0.0`

### 10.3 模型名称变化

| 旧模型 | 新模型 | 说明 |
|--------|--------|------|
| `gpt-4-turbo` | `gpt-4o` | 更快更便宜的多模态模型 |
| `gpt-3.5-turbo` | `gpt-4o-mini` | 轻量级模型替代品 |
| - | `gpt-5` / `gpt-5-mini` | 2025 年发布的新模型 |

---

## 十一、JSON Mode 与结构化输出

### 11.1 JSON Mode

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def json_output(prompt: str) -> dict:
    """要求模型输出 JSON 格式"""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一个助手，请始终返回 JSON 格式。"},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},  # 强制 JSON 输出
    )
    import json
    return json.loads(response.choices[0].message.content)
```

### 11.2 结构化输出（Structured Outputs）

```python
from pydantic import BaseModel
from openai import AsyncOpenAI

client = AsyncOpenAI()


class WeatherInfo(BaseModel):
    city: str
    temperature: float
    condition: str
    humidity: int


async def structured_output(prompt: str) -> WeatherInfo:
    """使用 Pydantic 模型约束输出结构"""
    response = await client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "提取天气信息。"},
            {"role": "user", "content": prompt},
        ],
        response_format=WeatherInfo,
    )
    return response.choices[0].message.parsed
```

---

## 十二、常见错误与正确写法

### 12.1 客户端初始化

```python
# ❌ 错误：使用 v0.28 全局方式
import openai
openai.api_key = "sk-xxx"

# ❌ 错误：硬编码 API Key
client = OpenAI(api_key="sk-xxx-real-key")

# ❌ 错误：在 FastAPI 中使用同步客户端
from openai import OpenAI
client = OpenAI()  # 会阻塞事件循环！

# ✅ 正确：异步客户端 + 环境变量
from openai import AsyncOpenAI
client = AsyncOpenAI()  # 自动读取 OPENAI_API_KEY 环境变量
```

### 12.2 流式输出

```python
# ❌ 错误：忘记 await 异步流
stream = client.chat.completions.create(model="gpt-4o", messages=messages, stream=True)
for chunk in stream:  # 错误！异步调用未 await

# ❌ 错误：未检查 content 是否为 None
async for chunk in stream:
    print(chunk.choices[0].delta.content)  # 可能打印 None

# ✅ 正确
stream = await client.chat.completions.create(model="gpt-4o", messages=messages, stream=True)
async for chunk in stream:
    content = chunk.choices[0].delta.content
    if content is not None:
        print(content, end="")
```

### 12.3 函数调用

```python
# ❌ 错误：忘记处理 tool_calls
response = await client.chat.completions.create(
    model="gpt-4o", messages=messages, tools=tools,
)
return response.choices[0].message.content  # tool_calls 时 content 可能为 None

# ✅ 正确：检查是否有工具调用
message = response.choices[0].message
if message.tool_calls:
    # 处理工具调用...
    pass
elif message.content:
    return message.content
```

### 12.4 多模态

```python
# ❌ 错误：直接传图片路径
messages = [{"role": "user", "content": "/path/to/image.png"}]

# ❌ 错误：content 格式错误
messages = [{"role": "user", "content": {"text": "描述图片", "image": "url"}}]

# ✅ 正确：使用 content 数组格式
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这张图片"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
    ],
}]
```

---

## 注意

- 如果是使用 Claude/Anthropic API，请使用 `claude-developer-platform` 技能
- 如果是 AI 图片生成（Gemini），请使用 `banana-image` 技能
- 如果是与 Codex CLI 协同开发，请使用 `collaborating-with-codex` 技能
- 如果涉及 WebSocket/SSE 实时推送架构，请配合 `websocket-sse` 技能
- 如果涉及 Redis 缓存（缓存 AI 结果），请配合 `redis-cache` 技能
