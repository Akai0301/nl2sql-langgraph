// AI 模型配置类型
export interface AIConfig {
  id: number
  config_name: string
  provider: 'openai' | 'anthropic' | 'deepseek' | 'custom'
  base_url: string | null
  api_key: string | null
  has_api_key?: boolean  // 标记是否已配置 API Key
  model_name: string
  is_active: boolean
  extra_params: Record<string, unknown>
}

// 数据源配置类型
export interface DataSourceConfig {
  id: number
  ds_name: string
  ds_type: 'postgresql' | 'mysql' | 'sqlite'
  host: string | null
  port: number | null
  database: string | null
  username: string | null
  is_query_target: boolean
  extra_params: Record<string, unknown>
}

// 表信息类型
export interface TableInfo {
  table_name: string
  table_type: string
}

// 字段信息类型
export interface ColumnInfo {
  column_name: string
  data_type: string
  is_nullable: string
  column_default: string | null
}

// 知识库配置类型
export interface KnowledgeConfig {
  id: number
  datasource_id: number
  kb_type: 'term' | 'qa' | 'metric' | 'table_desc'
  kb_name: string
  kb_content: string | null
  kb_metadata: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

// 知识类型定义
export interface KnowledgeType {
  type: string
  name: string
  description: string
  content_template: string
}

// API 响应类型
export interface APIResponse<T> {
  items?: T[]
  total?: number
  page?: number
  page_size?: number
  total_pages?: number
}

// 测试连接结果
export interface TestConnectionResult {
  success: boolean
  message: string
}

// ============ Schema 学习相关类型（Phase 5 新增）============

// 学习任务状态
export type LearningStatus = 'pending' | 'running' | 'completed' | 'failed'

// 学习进度
export interface LearningProgress {
  task_id: number
  datasource_id: number
  status: LearningStatus
  progress: number  // 0-100
  current_step: string
  message: string
  error: string | null
}

// Schema 缓存
export interface SchemaCache {
  id: number
  datasource_id: number
  schema_json: Record<string, unknown>
  mschema_text: string
  table_count: number
  field_count: number
  learned_at: string | null
}

// 表 Schema 详情
export interface TableSchema {
  name: string
  comment: string | null
  table_type: 'fact' | 'dimension' | 'other'
  primary_keys: string[]
  field_count: number
  fields: FieldSchema[]
}

// 字段 Schema 详情
export interface FieldSchema {
  name: string
  type: string
  primary_key: boolean
  nullable: boolean
  comment: string | null
  category: 'DateTime' | 'Enum' | 'Code' | 'Text' | 'Measure' | null
  dim_or_meas: 'Dimension' | 'Measure' | null
  date_min_gran: string | null
  examples: string[]
}