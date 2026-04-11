---
name: thinking-mode-llm-fix
description: 修复思考模式模型 tool_choice 不兼容问题，增加 thinking_mode 配置属性
type: feedback
---

## 修复内容

**规则**: 思考模式模型不支持 tool_choice，需使用 JSON 格式输出

**Why**: DashScope Anthropic 兼容端点默认启用 thinking mode，不支持 `with_structured_output()` 内部使用的 `tool_choice` 参数

**How to apply**:
- 检测 `config.thinking_mode` 或 `provider=anthropic` 或 DashScope 端点
- 使用普通 `llm.invoke()` + JSON 格式 prompt + 手动解析
- 非思考模式模型继续使用 `with_structured_output()`

## 影响文件
- `app/core/config_service.py`: 增加 `thinking_mode` 属性
- `app/pipeline/nodes.py`: 条件分支处理思考模式

## 配置优先级
MySQL 配置表 > .env 文件 > 硬编码默认值