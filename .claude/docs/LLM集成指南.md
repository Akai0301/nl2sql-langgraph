# LLM 集成指南

> **版本**：v1.0.0
> **最后更新**：2026-04-01
> **适用项目**：nl2sql-langgraph

---

## 概述

nl2sql-langgraph 支持两种 SQL 生成模式：
- **Mock 模式**：基于规则引擎，无需 LLM API
- **LLM 模式**：调用 OpenAI API，支持自然语言理解

---

## 模式对比

| 特性 | Mock 模式 | LLM 模式 |
|------|----------|----------|
| 配置复杂度 | 简单 | 需配置 API Key |
| 响应速度 | 快（< 100ms） | 较慢（1-3s） |
| 语义理解 | 仅支持预定义模板 | 支持自然语言 |
| 适用场景 | 开发测试、Demo | 生产环境 |
| 成本 | 无 | API 调用费用 |

---

## Mock 模式配置

### 启用 Mock 模式

```env
USE_MOCK_LLM=true
```

### 工作原理

Mock 模式通过关键词匹配和模板生成 SQL：

1. **问题分析节点**：提取关键词（时间范围、地区、指标）
2. **模板匹配**：根据关键词选择预定义 SQL 模板
3. **参数填充**：将提取的参数填入模板

### 支持的问题模板

| 模板类型 | 示例问题 |
|---------|---------|
| 时间范围查询 | 查询过去30天的订单金额 |
| 地区分析 | 按地区统计订单金额 |
| 指标聚合 | 查询订单总额、订单数量 |
| 组合查询 | 查询过去7天按地区的订单金额 |

---

## LLM 模式配置

### 启用 LLM 模式

```env
USE_MOCK_LLM=false
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### OpenAI 兼容 API

支持所有 OpenAI 兼容的 API 服务：

| 服务商 | OPENAI_API_BASE | 说明 |
|--------|-----------------|------|
| OpenAI | `https://api.openai.com/v1` | 官方 API |
| Azure | `https://your-resource.openai.azure.com` | Azure OpenAI |
| 国内代理 | `https://api.proxy.com/v1` | 第三方代理 |
| 本地模型 | `http://localhost:8000/v1` | Ollama / vLLM |

### 模型选择建议

| 模型 | 成本 | 质量 | 适用场景 |
|------|------|------|---------|
| `gpt-4o-mini` | 低 | 中 | 日常使用（推荐） |
| `gpt-4o` | 中 | 高 | 复杂问题 |
| `gpt-3.5-turbo` | 极低 | 低 | 简单查询 |
| `claude-3-haiku` | 低 | 中 | Anthropic 用户 |

---

## Prompt 模板

### 系统提示词

```
你是一个专业的 SQL 生成助手。根据用户的问题和数据库元数据，生成准确的 PostgreSQL 查询语句。

## 数据库表结构
{schema_info}

## 检索到的相关知识
{knowledge_context}

## 指标定义
{metrics_context}

## 输出要求
1. 只输出 SELECT 语句
2. 使用 PostgreSQL 语法
3. 确保字段名与表结构一致
4. 添加适当的 LIMIT 限制
```

### 用户提示词模板

```python
# app/prompt_templates.py

SYSTEM_PROMPT = """你是 NL2SQL 专家..."""

USER_PROMPT_TEMPLATE = """
用户问题：{question}

## 相关表
{tables}

## 检索到的指标
{metrics}

## 知识库参考
{knowledge}

请生成 SQL 查询语句。
"""
```

---

## 代码实现

### LLM 调用入口

```python
# app/nodes.py 中的 sql_generation_node

import os
from openai import OpenAI

def sql_generation_node(state: NL2SQLState) -> dict:
    if os.getenv("USE_MOCK_LLM", "true").lower() == "true":
        # Mock 模式：规则生成
        return generate_sql_by_rules(state)
    else:
        # LLM 模式：调用 API
        return generate_sql_by_llm(state)

def generate_sql_by_llm(state: NL2SQLState) -> dict:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": format_user_prompt(state)},
        ],
        temperature=0.1,
    )

    sql = response.choices[0].message.content
    return {"generated_sql": sql}
```

---

## 错误处理

### API 调用失败

```python
from openai import APIError, RateLimitError

try:
    response = client.chat.completions.create(...)
except RateLimitError:
    # 速率限制，等待重试
    time.sleep(60)
    return generate_sql_by_llm(state)
except APIError as e:
    # API 错误，降级到 Mock 模式
    return generate_sql_by_rules(state)
```

### Token 超限

```python
# 截断过长的上下文
def truncate_context(context: str, max_tokens: int = 4000) -> str:
    # 简单估算：1 token ≈ 4 字符
    max_chars = max_tokens * 4
    if len(context) > max_chars:
        return context[:max_chars] + "..."
    return context
```

---

## 成本优化

### 1. 使用较小的模型

```env
OPENAI_MODEL=gpt-4o-mini  # 比 gpt-4o 便宜 10 倍
```

### 2. 缓存检索结果

```python
# 对相同的 question 缓存检索结果
@lru_cache(maxsize=100)
def cached_retrieve(question: str) -> dict:
    return retrieve_context(question)
```

### 3. 精简 Prompt

- 只传递相关的表结构
- 限制知识库条目数量（Top 5）
- 移除不必要的字段说明

---

## 调试技巧

### 打印完整 Prompt

```python
# 调试模式下打印 Prompt
if os.getenv("DEBUG_LLM") == "true":
    print(f"System: {SYSTEM_PROMPT}")
    print(f"User: {format_user_prompt(state)}")
```

### 记录 API 调用

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("openai").setLevel(logging.DEBUG)
```