"""
LLM 提供商适配器：统一封装 OpenAI、Anthropic、DeepSeek 等不同 SDK。
"""
from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from .config_service import AIModelConfig


def create_llm(config: AIModelConfig) -> BaseChatModel:
    """
    根据配置创建对应的 LLM 实例。

    支持的提供商：
    - openai: 使用 langchain_openai.ChatOpenAI
    - anthropic: 使用 langchain_anthropic.ChatAnthropic
    - deepseek: 使用 ChatOpenAI（兼容 OpenAI 接口）
    - custom: 使用 ChatOpenAI（用户自定义 base_url）
    - mock: 返回 None（使用规则引擎）
    """
    provider = config.provider.lower()

    if provider == "mock":
        # Mock 模式，不创建 LLM，由调用方使用规则引擎
        return None

    if provider == "openai":
        return _create_openai(config)

    elif provider == "anthropic":
        return _create_anthropic(config)

    elif provider == "deepseek":
        return _create_deepseek(config)

    elif provider == "custom":
        return _create_custom(config)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_openai(config: AIModelConfig) -> BaseChatModel:
    """创建 OpenAI LLM 实例"""
    from langchain_openai import ChatOpenAI

    extra_params = config.extra_params or {}
    return ChatOpenAI(
        model=config.model_name,
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=extra_params.get("temperature", 0),
        max_tokens=extra_params.get("max_tokens"),
        **{k: v for k, v in extra_params.items()
           if k not in ("temperature", "max_tokens")},
    )


def _create_anthropic(config: AIModelConfig) -> BaseChatModel:
    """创建 Anthropic LLM 实例"""
    from langchain_anthropic import ChatAnthropic

    extra_params = config.extra_params or {}
    # Anthropic 不支持自定义 base_url
    return ChatAnthropic(
        model=config.model_name,
        api_key=config.api_key,
        temperature=extra_params.get("temperature", 0),
        max_tokens=extra_params.get("max_tokens"),
        **{k: v for k, v in extra_params.items()
           if k not in ("temperature", "max_tokens")},
    )


def _create_deepseek(config: AIModelConfig) -> BaseChatModel:
    """创建 DeepSeek LLM 实例（兼容 OpenAI SDK）"""
    from langchain_openai import ChatOpenAI

    extra_params = config.extra_params or {}
    # DeepSeek 默认 base_url
    base_url = config.base_url or "https://api.deepseek.com/v1"

    return ChatOpenAI(
        model=config.model_name,
        base_url=base_url,
        api_key=config.api_key,
        temperature=extra_params.get("temperature", 0),
        max_tokens=extra_params.get("max_tokens"),
        **{k: v for k, v in extra_params.items()
           if k not in ("temperature", "max_tokens")},
    )


def _create_custom(config: AIModelConfig) -> BaseChatModel:
    """创建自定义提供商 LLM 实例（使用 OpenAI 兼容接口）"""
    from langchain_openai import ChatOpenAI

    if not config.base_url:
        raise ValueError("Custom provider requires base_url")

    extra_params = config.extra_params or {}
    return ChatOpenAI(
        model=config.model_name,
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=extra_params.get("temperature", 0),
        max_tokens=extra_params.get("max_tokens"),
        **{k: v for k, v in extra_params.items()
           if k not in ("temperature", "max_tokens")},
    )


def get_provider_default_base_url(provider: str) -> str | None:
    """获取提供商默认 base_url"""
    defaults = {
        "openai": "https://api.openai.com/v1",
        "anthropic": None,  # Anthropic 不支持自定义
        "deepseek": "https://api.deepseek.com/v1",
        "custom": None,
    }
    return defaults.get(provider.lower())


def get_provider_recommended_models(provider: str) -> list[str]:
    """获取提供商推荐模型列表"""
    recommendations = {
        "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
        "deepseek": ["deepseek-chat", "deepseek-coder"],
        "custom": [],
    }
    return recommendations.get(provider.lower(), [])