#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
批量 Embedding 初始化脚本

功能：
- 从 PostgreSQL 读取 enterprise_kb, metrics_catalog, lake_table_metadata 表数据
- 使用通义千问 Embedding API（text-embedding-v3）生成向量
- 批量 UPDATE 表记录，填充 embedding 字段

运行方式：
  # 1. 编辑 .env 文件（如果尚未配置）

  # 填入 QWEN_API_KEY 和 POSTGRES_DSN

  # 2. 直接运行（自动加载 .env 文件）
  python scripts/init_embeddings.py

  # 3. 仅统计待处理数量（不执行 embedding 生成）
  python scripts/init_embeddings.py --dry-run

  # 4. 仅初始化指定表
  python scripts/init_embeddings.py --tables enterprise_kb,metrics_catalog

  # 5. 强制重新生成所有（包括已有 embedding 的记录）
  python scripts/init_embeddings.py --force

  # 6. 查看帮助
  python scripts/init_embeddings.py --help

环境变量（从 .env 文件读取）：
  POSTGRES_DSN: PostgreSQL 连接串（必填）
  QWEN_API_KEY: 通义千问 API Key（必填）
  QWEN_API_BASE: API 地址（可选，默认 DashScope）
  QWEN_EMBEDDING_MODEL: 模型名称（可选，默认 text-embedding-v3）
  QWEN_EMBEDDING_DIM: 向量维度（可选，默认 1024）

注意：
  系统环境变量优先级高于 .env 文件，可通过命令行临时覆盖：
  Windows PowerShell:
    $env:QWEN_API_KEY = "your-api-key"
    python scripts/init_embeddings.py
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from loguru import logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载项目根目录的 .env 文件（优先级：系统环境变量 > .env 文件）
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.core.embedding_service import EmbeddingService, format_vector


# ============================================
# 配置
# ============================================

# 批处理配置
BATCH_SIZE = 10  # 每批处理记录数（通义千问 API 实际限制单次最多 10 个文本）
MAX_RETRIES = 3  # API 调用重试次数
RETRY_DELAY = 2  # 重试间隔（秒）

# Embedding 字段映射配置
# 格式: {表名: [(embedding字段, 源字段), ...]}
EMBEDDING_CONFIG = {
    "enterprise_kb": [
        ("keyword_embedding", "keyword_synonyms"),
        ("business_embedding", "business_meaning"),
    ],
    "metrics_catalog": [
        ("metric_embedding", "metric_name"),
        ("synonym_embedding", "metric_synonyms"),
    ],
    "lake_table_metadata": [
        ("topic_embedding", "topic"),
        ("metric_embedding", "metric_name"),
    ],
}


# ============================================
# 数据库操作
# ============================================

def get_postgres_dsn() -> str:
    """获取 PostgreSQL 连接串"""
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("缺少环境变量：POSTGRES_DSN")
    return dsn


def fetch_records_without_embedding(
    dsn: str,
    table: str,
    embedding_column: str,
    source_column: str,
    limit: Optional[int] = None,
    force: bool = False,
) -> List[dict]:
    """
    获取未填充 embedding 的记录

    Args:
        dsn: PostgreSQL 连接串
        table: 表名
        embedding_column: embedding 字段名
        source_column: 源字段名
        limit: 返回数量限制
        force: 是否强制获取所有记录（包括已有 embedding）

    Returns:
        记录列表，包含 id 和 source_column 值
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if force:
                # 强制重新生成所有
                where_clause = f"{source_column} IS NOT NULL AND {source_column} != ''"
            else:
                # 仅获取未填充的
                where_clause = f"{embedding_column} IS NULL AND {source_column} IS NOT NULL AND {source_column} != ''"

            sql = f"""
                SELECT id, {source_column}
                FROM {table}
                WHERE {where_clause}
                ORDER BY id
            """
            if limit:
                sql += f" LIMIT {limit}"

            cur.execute(sql)
            return cur.fetchall()


def count_records_without_embedding(
    dsn: str,
    table: str,
    embedding_column: str,
    source_column: str,
    force: bool = False,
) -> int:
    """统计未填充 embedding 的记录数"""
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            if force:
                where_clause = f"{source_column} IS NOT NULL AND {source_column} != ''"
            else:
                where_clause = f"{embedding_column} IS NULL AND {source_column} IS NOT NULL AND {source_column} != ''"

            sql = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
            cur.execute(sql)
            return cur.fetchone()[0]


def update_embedding(
    dsn: str,
    table: str,
    embedding_column: str,
    record_id: int,
    embedding: List[float],
) -> bool:
    """
    更新单条记录的 embedding

    Args:
        dsn: PostgreSQL 连接串
        table: 表名
        embedding_column: embedding 字段名
        record_id: 记录 ID
        embedding: embedding 向量

    Returns:
        是否更新成功
    """
    # 格式化向量为 PostgreSQL 格式
    vector_str = format_vector(embedding)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            sql = f"""
                UPDATE {table}
                SET {embedding_column} = '{vector_str}'::vector
                WHERE id = %s
            """
            cur.execute(sql, (record_id,))
            conn.commit()
            return cur.rowcount > 0


def batch_update_embeddings(
    dsn: str,
    table: str,
    embedding_column: str,
    updates: List[tuple[int, List[float]]],
) -> int:
    """
    批量更新 embedding

    Args:
        dsn: PostgreSQL 连接串
        table: 表名
        embedding_column: embedding 字段名
        updates: [(record_id, embedding), ...]

    Returns:
        更新成功的记录数
    """
    success_count = 0

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for record_id, embedding in updates:
                vector_str = format_vector(embedding)
                sql = f"""
                    UPDATE {table}
                    SET {embedding_column} = '{vector_str}'::vector
                    WHERE id = %s
                """
                cur.execute(sql, (record_id,))
                if cur.rowcount > 0:
                    success_count += 1

            conn.commit()

    return success_count


# ============================================
# Embedding 生成
# ============================================

async def generate_embeddings_batch(
    embedding_service: EmbeddingService,
    texts: List[str],
) -> List[List[float]]:
    """
    批量生成 embedding（带重试）

    Args:
        embedding_service: Embedding 服务实例
        texts: 文本列表

    Returns:
        embedding 向量列表
    """
    for attempt in range(MAX_RETRIES):
        try:
            embeddings = await embedding_service.embed_texts(texts)
            return embeddings
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Embedding API 调用失败，{wait_time}秒后重试 "
                    f"（第{attempt + 1}/{MAX_RETRIES}次）: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Embedding API 最终失败: {e}")
                raise


async def process_table_embeddings(
    dsn: str,
    table: str,
    embedding_service: EmbeddingService,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    处理单表的 embedding 初始化

    Args:
        dsn: PostgreSQL 连接串
        table: 表名
        embedding_service: Embedding 服务实例
        force: 是否强制重新生成
        dry_run: 是否仅统计不执行

    Returns:
        处理结果统计
    """
    config = EMBEDDING_CONFIG.get(table, [])
    if not config:
        logger.warning(f"表 {table} 未配置 embedding 字段映射，跳过")
        return {"table": table, "status": "skipped", "reason": "no_config"}

    results = {
        "table": table,
        "status": "success",
        "fields": [],
    }

    for embedding_column, source_column in config:
        logger.info(f"处理 {table}.{embedding_column}（源字段: {source_column}）")

        # 统计待处理记录数
        pending_count = count_records_without_embedding(
            dsn, table, embedding_column, source_column, force
        )

        if pending_count == 0:
            logger.info(f"  ✓ {table}.{embedding_column} 已全部填充，无需处理")
            results["fields"].append({
                "embedding_column": embedding_column,
                "source_column": source_column,
                "pending_count": 0,
                "processed_count": 0,
                "status": "already_filled",
            })
            continue

        logger.info(f"  待处理记录数: {pending_count}")

        if dry_run:
            results["fields"].append({
                "embedding_column": embedding_column,
                "source_column": source_column,
                "pending_count": pending_count,
                "processed_count": 0,
                "status": "dry_run",
            })
            continue

        # 分批处理
        processed_count = 0
        failed_count = 0

        # 获取记录
        records = fetch_records_without_embedding(
            dsn, table, embedding_column, source_column,
            limit=None, force=force
        )

        # 分批生成 embedding
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]

            # 提取文本
            texts = [r[source_column] for r in batch]

            # 生成 embedding
            try:
                embeddings = await generate_embeddings_batch(embedding_service, texts)
            except Exception as e:
                logger.error(f"  ✗ 批次 {i//BATCH_SIZE + 1} 处理失败: {e}")
                failed_count += len(batch)
                continue

            # 批量更新
            updates = [(r["id"], embeddings[j]) for j, r in enumerate(batch)]
            success_count = batch_update_embeddings(dsn, table, embedding_column, updates)

            processed_count += success_count
            failed_count += len(batch) - success_count

            logger.info(
                f"  批次 {i//BATCH_SIZE + 1}/{(len(records)-1)//BATCH_SIZE + 1}: "
                f"成功 {success_count}/{len(batch)}"
            )

            # API 速率限制：批次间短暂等待
            await asyncio.sleep(0.5)

        results["fields"].append({
            "embedding_column": embedding_column,
            "source_column": source_column,
            "pending_count": pending_count,
            "processed_count": processed_count,
            "failed_count": failed_count,
            "status": "processed",
        })

        logger.info(
            f"  ✓ 完成 {table}.{embedding_column}: "
            f"处理 {processed_count}/{pending_count}，失败 {failed_count}"
        )

    return results


# ============================================
# 主函数
# ============================================

async def main_async(
    tables: Optional[List[str]] = None,
    force: bool = False,
    dry_run: bool = False,
):
    """异步主函数"""
    # 检查环境变量
    dsn = get_postgres_dsn()
    api_key = os.getenv("QWEN_API_KEY")

    if not api_key:
        logger.error("缺少环境变量：QWEN_API_KEY")
        logger.info("请设置 QWEN_API_KEY 后重新运行")
        sys.exit(1)

    # 初始化 Embedding 服务
    embedding_service = EmbeddingService()
    logger.info(f"Embedding 服务已初始化: model={embedding_service.model}, dim={embedding_service.dimension}")

    # 确定要处理的表
    target_tables = tables if tables else list(EMBEDDING_CONFIG.keys())

    logger.info("=" * 60)
    logger.info("批量 Embedding 初始化")
    logger.info("=" * 60)
    logger.info(f"目标表: {', '.join(target_tables)}")
    logger.info(f"强制模式: {force}")
    logger.info(f"仅统计: {dry_run}")
    logger.info("=" * 60)

    # 处理每个表
    all_results = []
    for table in target_tables:
        result = await process_table_embeddings(
            dsn, table, embedding_service, force, dry_run
        )
        all_results.append(result)

    # 输出汇总
    logger.info("=" * 60)
    logger.info("处理汇总")
    logger.info("=" * 60)

    total_processed = 0
    total_failed = 0

    for result in all_results:
        logger.info(f"\n表: {result['table']}")
        for field in result.get("fields", []):
            status = field.get("status", "unknown")
            processed = field.get("processed_count", 0)
            failed = field.get("failed_count", 0)
            pending = field.get("pending_count", 0)

            if status == "already_filled":
                logger.info(f"  {field['embedding_column']}: 已全部填充 ✓")
            elif status == "dry_run":
                logger.info(f"  {field['embedding_column']}: 待处理 {pending} 条（仅统计）")
            elif status == "processed":
                logger.info(f"  {field['embedding_column']}: 处理 {processed}/{pending}, 失败 {failed}")
                total_processed += processed
                total_failed += failed
            else:
                logger.info(f"  {field['embedding_column']}: {status}")

    logger.info("=" * 60)
    logger.info(f"总计: 处理 {total_processed} 条，失败 {total_failed} 条")
    logger.info("=" * 60)


def main():
    """主函数入口"""
    parser = argparse.ArgumentParser(
        description="批量 Embedding 初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--tables",
        type=str,
        help="指定要处理的表（逗号分隔），默认处理全部",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成所有 embedding（包括已填充的）",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计待处理记录数，不执行 embedding 生成",
    )

    args = parser.parse_args()

    # 解析表列表
    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]

    # 运行
    asyncio.run(main_async(tables, args.force, args.dry_run))


if __name__ == "__main__":
    main()