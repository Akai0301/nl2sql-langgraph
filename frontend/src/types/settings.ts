// AI 模型配置类型
export interface AIConfig {
  id: number
  config_name: string
  provider: 'openai' | 'anthropic' | 'deepseek' | 'custom'
  base_url: string | null
  api_key: string | null
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