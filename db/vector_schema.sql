-- ============================================
-- pgvector 扩展安装与向量字段添加
-- 用于混合检索 + RRF 融合
-- ============================================
--
-- 前置条件：
-- 1. PostgreSQL 版本 >= 16（推荐）
-- 2. 已安装 pgvector 扩展
--    Windows 预编译版下载：
--    https://github.com/andreiramani/pgvector_pgsql_windows/releases
--    解压后复制到 PostgreSQL 目录：
--    - vector.dll → C:\Program Files\PostgreSQL\18\lib\
--    - vector.control, vector--*.sql → C:\Program Files\PostgreSQL\18\share\extension\
--
-- 使用说明：
-- 1. 先执行此脚本添加 vector 字段
-- 2. 再运行 scripts/init_embeddings.py 生成并填充 embedding 数据
-- ============================================

-- ============================================
-- Step 1: 启用 pgvector 扩展
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证扩展是否安装成功
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- ============================================
-- Step 2: enterprise_kb 添加向量字段
-- ============================================
-- 为关键词同义词添加 embedding（用于语义匹配关键词）
ALTER TABLE enterprise_kb
  ADD COLUMN IF NOT EXISTS keyword_embedding vector(1024);

-- 为业务含义添加 embedding（用于语义匹配业务概念）
ALTER TABLE enterprise_kb
  ADD COLUMN IF NOT EXISTS business_embedding vector(1024);

-- 创建 HNSW 索引（余弦距离，高性能）
-- 参数说明：
-- m = 16: 每个节点的连接数（影响召回率和构建时间）
-- ef_construction = 64: 构建时的动态候选列表大小
CREATE INDEX IF NOT EXISTS idx_enterprise_kb_keyword_emb
  ON enterprise_kb USING hnsw (keyword_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_enterprise_kb_business_emb
  ON enterprise_kb USING hnsw (business_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ============================================
-- Step 3: metrics_catalog 添加向量字段
-- ============================================
-- 为指标名称添加 embedding
ALTER TABLE metrics_catalog
  ADD COLUMN IF NOT EXISTS metric_embedding vector(1024);

-- 为指标同义词添加 embedding（用于匹配多种表述）
ALTER TABLE metrics_catalog
  ADD COLUMN IF NOT EXISTS synonym_embedding vector(1024);

-- 创建 HNSW 索引
CREATE INDEX IF NOT EXISTS idx_metrics_catalog_metric_emb
  ON metrics_catalog USING hnsw (metric_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_metrics_catalog_synonym_emb
  ON metrics_catalog USING hnsw (synonym_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ============================================
-- Step 4: lake_table_metadata 添加向量字段
-- ============================================
-- 为主题添加 embedding
ALTER TABLE lake_table_metadata
  ADD COLUMN IF NOT EXISTS topic_embedding vector(1024);

-- 为指标名称添加 embedding（便于关联 metrics_catalog）
ALTER TABLE lake_table_metadata
  ADD COLUMN IF NOT EXISTS metric_embedding vector(1024);

-- 创建 HNSW 索引
CREATE INDEX IF NOT EXISTS idx_lake_table_metadata_topic_emb
  ON lake_table_metadata USING hnsw (topic_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_lake_table_metadata_metric_emb
  ON lake_table_metadata USING hnsw (metric_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ============================================
-- Step 5: 添加注释说明
-- ============================================
COMMENT ON COLUMN enterprise_kb.keyword_embedding IS '关键词同义词的向量嵌入（通义千问 text-embedding-v3, 1024维）';
COMMENT ON COLUMN enterprise_kb.business_embedding IS '业务含义的向量嵌入（通义千问 text-embedding-v3, 1024维）';
COMMENT ON COLUMN metrics_catalog.metric_embedding IS '指标名称的向量嵌入（通义千问 text-embedding-v3, 1024维）';
COMMENT ON COLUMN metrics_catalog.synonym_embedding IS '指标同义词的向量嵌入（通义千问 text-embedding-v3, 1024维）';
COMMENT ON COLUMN lake_table_metadata.topic_embedding IS '主题的向量嵌入（通义千问 text-embedding-v3, 1024维）';
COMMENT ON COLUMN lake_table_metadata.metric_embedding IS '指标名称的向量嵌入（通义千问 text-embedding-v3, 1024维）';

-- ============================================
-- Step 6: 验证向量索引创建成功
-- ============================================
-- SELECT
--   indexname,
--   indexdef
-- FROM pg_indexes
-- WHERE tablename IN ('enterprise_kb', 'metrics_catalog', 'lake_table_metadata')
--   AND indexname LIKE '%emb%';

-- ============================================
-- 使用示例（查询时）
-- ============================================
-- 向量检索示例：
-- SELECT id, topic, business_meaning,
--        keyword_embedding <=> '[0.1,0.2,...]'::vector AS cosine_distance
-- FROM enterprise_kb
-- WHERE keyword_embedding IS NOT NULL
-- ORDER BY cosine_distance ASC
-- LIMIT 20;
--
-- 混合检索（LIKE + 向量）需要在应用层调用 hybrid_search 函数
-- 见 app/pipeline/tools.py
-- ============================================