-- ============================================
-- 维度表定义
-- ============================================

-- 地区维度表
CREATE TABLE IF NOT EXISTS dim_region (
  region_id SERIAL PRIMARY KEY,
  region_code TEXT NOT NULL UNIQUE,
  region_name TEXT NOT NULL,
  province TEXT,
  city TEXT,
  region_level TEXT NOT NULL,  -- 省/市/区
  parent_region_id INTEGER REFERENCES dim_region(region_id)
);

CREATE INDEX IF NOT EXISTS idx_dim_region_code ON dim_region(region_code);
CREATE INDEX IF NOT EXISTS idx_dim_region_province ON dim_region(province);

-- 产品维度表
CREATE TABLE IF NOT EXISTS dim_product (
  product_id SERIAL PRIMARY KEY,
  product_code TEXT NOT NULL UNIQUE,
  product_name TEXT NOT NULL,
  category_l1 TEXT NOT NULL,      -- 一级品类
  category_l2 TEXT,               -- 二级品类
  brand TEXT,                     -- 品牌
  unit_price NUMERIC(10,2),       -- 单价
  status TEXT DEFAULT 'active'    -- 状态
);

CREATE INDEX IF NOT EXISTS idx_dim_product_category ON dim_product(category_l1, category_l2);
CREATE INDEX IF NOT EXISTS idx_dim_product_brand ON dim_product(brand);

-- 客户维度表
CREATE TABLE IF NOT EXISTS dim_customer (
  customer_id SERIAL PRIMARY KEY,
  customer_code TEXT NOT NULL UNIQUE,
  customer_name TEXT NOT NULL,
  gender TEXT,                    -- 性别
  age_group TEXT,                 -- 年龄段
  member_level TEXT,              -- 会员等级：普通/银卡/金卡/钻石
  register_date DATE,             -- 注册日期
  city TEXT                       -- 所在城市
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_level ON dim_customer(member_level);
CREATE INDEX IF NOT EXISTS idx_dim_customer_city ON dim_customer(city);

-- 渠道维度表
CREATE TABLE IF NOT EXISTS dim_channel (
  channel_id SERIAL PRIMARY KEY,
  channel_code TEXT NOT NULL UNIQUE,
  channel_name TEXT NOT NULL,
  channel_type TEXT NOT NULL,     -- 线上/线下
  platform TEXT                   -- 平台：APP/小程序/门店等
);

-- ============================================
-- 事实表定义
-- ============================================

-- 订单事实表（增强版）
DROP TABLE IF EXISTS fact_orders CASCADE;
CREATE TABLE fact_orders (
  order_id BIGINT PRIMARY KEY,
  order_date DATE NOT NULL,
  order_time TIMESTAMP,           -- 下单时间
  customer_id INTEGER,            -- 客户ID（关联 dim_customer.customer_id）
  product_code TEXT,              -- 产品编码
  region_code TEXT,               -- 地区编码
  channel_id INTEGER,             -- 渠道ID（关联 dim_channel.channel_id）
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price NUMERIC(10,2) NOT NULL,
  order_amount NUMERIC(18,2) NOT NULL,    -- 订单金额
  discount_amount NUMERIC(18,2) DEFAULT 0, -- 优惠金额
  actual_amount NUMERIC(18,2) NOT NULL,   -- 实付金额
  profit_amount NUMERIC(18,2),            -- 利润金额
  order_status TEXT DEFAULT 'completed'   -- 订单状态
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON fact_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_product ON fact_orders(product_code);
CREATE INDEX IF NOT EXISTS idx_fact_orders_region ON fact_orders(region_code);
CREATE INDEX IF NOT EXISTS idx_fact_orders_channel ON fact_orders(channel_id);

-- ============================================
-- 知识库和元数据表
-- ============================================

-- 企业知识黑话/标准示例 Q&A
CREATE TABLE IF NOT EXISTS enterprise_kb (
  id SERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  keyword_synonyms TEXT NOT NULL,
  business_meaning TEXT NOT NULL,
  example_question TEXT,
  example_sql_template TEXT
);

-- 指标口径目录（聚合规则/目标列）
CREATE TABLE IF NOT EXISTS metrics_catalog (
  id SERIAL PRIMARY KEY,
  metric_name TEXT NOT NULL,
  metric_synonyms TEXT NOT NULL,
  business_definition TEXT,
  aggregation_rule TEXT NOT NULL,
  target_column TEXT NOT NULL
);

-- 湖表业务元数据（从数据湖表抽取的"主题表/字段映射"）
CREATE TABLE IF NOT EXISTS lake_table_metadata (
  id SERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  fact_table TEXT NOT NULL,
  fact_time_column TEXT NOT NULL,
  fact_region_column TEXT,
  dimension_table TEXT,
  dimension_join_key TEXT,
  dimension_region_key TEXT,
  measure_column TEXT,
  measure_sql_expression TEXT NOT NULL,
  grain TEXT,
  -- 扩展字段（Schema 学习）
  table_type VARCHAR(20),           -- 表类型：fact/dimension/other
  table_comment TEXT,               -- 表注释
  field_type VARCHAR(20),           -- 字段类型：DateTime/Enum/Code/Text/Measure
  is_dimension BOOLEAN DEFAULT TRUE, -- 是否为维度字段
  date_granularity VARCHAR(20),     -- 时间颗粒度：YEAR/MONTH/DAY/HOUR/MINUTE/SECOND
  examples JSONB,                   -- 示例值列表
  llm_description TEXT              -- LLM 生成的中文描述
);

-- 字段级元数据表（新增，用于 Schema 学习结果存储）
CREATE TABLE IF NOT EXISTS field_metadata (
  id SERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  column_name TEXT NOT NULL,
  data_type TEXT NOT NULL,
  is_primary_key BOOLEAN DEFAULT FALSE,
  is_nullable BOOLEAN DEFAULT TRUE,
  column_default TEXT,
  column_comment TEXT,
  -- Schema 学习扩展
  field_category VARCHAR(20),       -- DateTime/Enum/Code/Text/Measure
  dim_or_meas VARCHAR(20),          -- Dimension/Measure
  date_granularity VARCHAR(20),     -- 时间颗粒度
  examples JSONB,                   -- 示例值列表
  llm_description TEXT,             -- LLM 描述
  -- 业务语义
  business_term TEXT,               -- 业务术语
  synonym TEXT,                     -- 同义词
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(table_name, column_name)
);

CREATE INDEX IF NOT EXISTS idx_field_metadata_table ON field_metadata(table_name);
CREATE INDEX IF NOT EXISTS idx_field_metadata_category ON field_metadata(field_category);
