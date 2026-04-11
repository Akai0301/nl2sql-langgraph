"""
Embedding 服务：使用通义千问 Embedding API（兼容 OpenAI 协议）

API 文档：https://help.aliyun.com/document_detail/2712195.html
模型：text-embedding-v3（1024 维）

功能：
- 批量生成 embedding
- 单个查询 embedding
- 缓存优化（可选）
"""
from __future__ import annotations

import os
from typing import List, Optional

from openai import AsyncOpenAI
from loguru import logger


class EmbeddingService:
    """
    通义千问 Embedding 服务

    使用 OpenAI SDK 连接通义千问 DashScope API（兼容 OpenAI 协议）

    配置环境变量：
    - QWEN_API_KEY: DashScope API Key（必填）
    - QWEN_API_BASE: API 地址（默认：https://dashscope.aliyuncs.com/compatible-mode/v1）
    - QWEN_EMBEDDING_MODEL: 模型名称（默认：text-embedding-v3）
    - QWEN_EMBEDDING_DIM: 向量维度（默认：1024）
    """

    # 客户端单例
    _client: Optional[AsyncOpenAI] = None

    # 默认配置
    DEFAULT_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "text-embedding-v3"
    DEFAULT_DIMENSION = 1024

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        """
        初始化 Embedding 服务

        Args:
            api_key: DashScope API Key（可选，默认从环境变量读取）
            api_base: API 地址（可选，默认从环境变量读取）
            model: 模型名称（可选，默认 text-embedding-v3）
            dimension: 向量维度（可选，默认 1024）
        """
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.api_base = api_base or os.getenv("QWEN_API_BASE", self.DEFAULT_API_BASE)
        self.model = model or os.getenv("QWEN_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self.dimension = dimension or int(os.getenv("QWEN_EMBEDDING_DIM", str(self.DEFAULT_DIMENSION)))

        if not self.api_key:
            logger.warning("QWEN_API_KEY 未配置，Embedding 服务将不可用")

    @classmethod
    def get_client(cls) -> AsyncOpenAI:
        """
        获取或创建 AsyncOpenAI 客户端（单例模式）

        Returns:
            AsyncOpenAI 客户端实例
        """
        if cls._client is None:
            api_key = os.getenv("QWEN_API_KEY")
            if not api_key:
                raise RuntimeError("QWEN_API_KEY 未配置，无法创建 Embedding 客户端")

            cls._client = AsyncOpenAI(
                api_key=api_key,
                base_url=os.getenv("QWEN_API_BASE", cls.DEFAULT_API_BASE),
                timeout=60.0,
                max_retries=2,
            )
            logger.info(f"Embedding 客户端已初始化: base_url={cls._client.base_url}")

        return cls._client

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本的 embedding

        Args:
            texts: 文本列表（最多 25 个，每个最多 2048 tokens）

        Returns:
            embedding 向量列表（每个 1024 维）

        Raises:
            RuntimeError: API Key 未配置
            Exception: API 调用失败
        """
        if not texts:
            return []

        if not self.api_key:
            raise RuntimeError("QWEN_API_KEY 未配置")

        client = self.get_client()

        try:
            # 通义千问 embedding API（兼容 OpenAI 协议）
            response = await client.embeddings.create(
                input=texts,
                model=self.model,
                dimensions=self.dimension,
            )

            embeddings = [item.embedding for item in response.data]

            logger.debug(
                f"Embedding 生成成功: {len(texts)} 个文本, "
                f"model={self.model}, dim={self.dimension}, "
                f"usage={response.usage.total_tokens} tokens"
            )

            return embeddings

        except Exception as e:
            logger.error(f"Embedding 生成失败: {e}")
            raise

    async def embed_query(self, query: str) -> List[float]:
        """
        生成单个查询的 embedding

        Args:
            query: 用户查询文本

        Returns:
            embedding 向量（1024 维）
        """
        embeddings = await self.embed_texts([query])
        return embeddings[0] if embeddings else []

    async def embed_batch_with_retry(
        self,
        texts: List[str],
        batch_size: int = 10,  # 通义千问 API 限制为 10
        max_retries: int = 3,
    ) -> List[List[float]]:
        """
        批量生成 embedding（支持分批和重试）

        通义千问 API 单次最多支持 10 个文本（注意：官方文档说 25，但实际限制为 10）

        Args:
            texts: 文本列表
            batch_size: 每批数量（默认 10，通义千问实际限制）
            max_retries: 最大重试次数

        Returns:
            embedding 向量列表
        """
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            for attempt in range(max_retries):
                try:
                    embeddings = await self.embed_texts(batch)
                    all_embeddings.extend(embeddings)
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避
                        logger.warning(
                            f"Embedding 批次 {i//batch_size + 1} 失败，"
                            f"{wait_time}秒后重试（第{attempt + 1}次）: {e}"
                        )
                        import asyncio
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Embedding 批次 {i//batch_size + 1} 最终失败: {e}")
                        # 失败时返回空向量占位
                        all_embeddings.extend([[0.0] * self.dimension for _ in batch])

        return all_embeddings

    def format_embedding_for_sql(self, embedding: List[float]) -> str:
        """
        格式化 embedding 为 PostgreSQL vector 类型字符串

        Args:
            embedding: embedding 向量

        Returns:
            PostgreSQL vector 格式字符串（如 '[0.1,0.2,...]'）
        """
        return "[" + ",".join(str(x) for x in embedding) + "]"


# ============ 全局单例 ============

_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取全局 Embedding 服务实例（单例）

    Returns:
        EmbeddingService 实例
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service


# ============ 辅助函数 ============

async def embed_query(query: str) -> List[float]:
    """
    快捷函数：生成单个查询的 embedding

    Args:
        query: 查询文本

    Returns:
        embedding 向量
    """
    service = get_embedding_service()
    return await service.embed_query(query)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    快捷函数：批量生成 embedding

    Args:
        texts: 文本列表

    Returns:
        embedding 向量列表
    """
    service = get_embedding_service()
    return await service.embed_texts(texts)


def format_vector(embedding: List[float]) -> str:
    """
    快捷函数：格式化 embedding 为 SQL 字符串

    Args:
        embedding: embedding 向量

    Returns:
        PostgreSQL vector 格式字符串
    """
    service = get_embedding_service()
    return service.format_embedding_for_sql(embedding)