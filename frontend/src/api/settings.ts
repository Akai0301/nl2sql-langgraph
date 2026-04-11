import type {
  AIConfig,
  DataSourceConfig,
  TableInfo,
  ColumnInfo,
  KnowledgeConfig,
  KnowledgeType,
  APIResponse,
  TestConnectionResult,
  LearningProgress,
  SchemaCache,
  TableSchema,
} from '@/types/settings'

const API_BASE = ''

// ============ AI 配置 API ============

export async function listAIConfigs(): Promise<{ items: AIConfig[]; active: AIConfig | null }> {
  const response = await fetch(`${API_BASE}/settings/ai`)
  if (!response.ok) throw new Error('Failed to fetch AI configs')
  return response.json()
}

export async function createAIConfig(data: Partial<AIConfig>): Promise<AIConfig> {
  const response = await fetch(`${API_BASE}/settings/ai`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create AI config')
  }
  return response.json()
}

export async function updateAIConfig(id: number, data: Partial<AIConfig>): Promise<AIConfig> {
  const response = await fetch(`${API_BASE}/settings/ai/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('Failed to update AI config')
  return response.json()
}

export async function deleteAIConfig(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/ai/${id}`, { method: 'DELETE' })
  if (!response.ok) throw new Error('Failed to delete AI config')
}

export async function activateAIConfig(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/ai/${id}/activate`, { method: 'POST' })
  if (!response.ok) throw new Error('Failed to activate AI config')
}

/**
 * 获取 AI 配置的 API Key（用于前端显示已保存的密钥）
 */
export async function getAIConfigApiKey(id: number): Promise<{ api_key: string }> {
  const response = await fetch(`${API_BASE}/settings/ai/${id}/api-key`)
  if (!response.ok) throw new Error('Failed to get API key')
  return response.json()
}

export interface AITestRequest {
  base_url?: string
  api_key?: string
  model_name?: string
}

export interface AITestResult {
  success: boolean
  message: string
  provider: string
  model?: string
  base_url?: string
  latency_ms: number
  response_preview?: string
  tokens_used?: {
    prompt: number
    completion: number
    total: number
  }
}

/**
 * 测试 AI 配置连接
 * 可选参数覆盖数据库配置，用于保存前预测试
 */
export async function testAIConfig(
  id: number,
  overrides?: AITestRequest
): Promise<AITestResult> {
  const response = await fetch(`${API_BASE}/settings/ai/${id}/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(overrides || {}),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to test AI config')
  }
  return response.json()
}

// ============ 数据源 API ============

export async function listDatasources(): Promise<{ items: DataSourceConfig[] }> {
  const response = await fetch(`${API_BASE}/settings/datasource`)
  if (!response.ok) throw new Error('Failed to fetch datasources')
  return response.json()
}

export async function getDatasource(id: number): Promise<DataSourceConfig> {
  const response = await fetch(`${API_BASE}/settings/datasource/${id}`)
  if (!response.ok) throw new Error('Failed to fetch datasource')
  return response.json()
}

export async function createDatasource(data: Partial<DataSourceConfig>): Promise<DataSourceConfig> {
  const response = await fetch(`${API_BASE}/settings/datasource`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create datasource')
  }
  return response.json()
}

export async function updateDatasource(id: number, data: Partial<DataSourceConfig>): Promise<DataSourceConfig> {
  const response = await fetch(`${API_BASE}/settings/datasource/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('Failed to update datasource')
  return response.json()
}

export async function deleteDatasource(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/datasource/${id}`, { method: 'DELETE' })
  if (!response.ok) throw new Error('Failed to delete datasource')
}

export async function testDatasource(id: number): Promise<TestConnectionResult> {
  const response = await fetch(`${API_BASE}/settings/datasource/${id}/test`, { method: 'POST' })
  if (!response.ok) throw new Error('Failed to test datasource')
  return response.json()
}

export async function setQueryDatasource(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/datasource/${id}/activate-query`, { method: 'POST' })
  if (!response.ok) throw new Error('Failed to set query datasource')
}

export async function getDatasourceTables(id: number): Promise<{ items: TableInfo[]; total: number }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${id}/tables`)
  if (!response.ok) throw new Error('Failed to fetch tables')
  return response.json()
}

export async function getTableInfo(dsId: number, tableName: string): Promise<{ table_name: string; columns: ColumnInfo[] }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/table/${encodeURIComponent(tableName)}`)
  if (!response.ok) throw new Error('Failed to fetch table info')
  return response.json()
}

export async function previewTable(dsId: number, tableName: string, limit = 100): Promise<{ columns: string[]; rows: unknown[][] }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/table/${encodeURIComponent(tableName)}/preview?limit=${limit}`)
  if (!response.ok) throw new Error('Failed to preview table')
  return response.json()
}

// ============ 知识库 API ============

export async function listKnowledgeTypes(): Promise<{ items: KnowledgeType[] }> {
  const response = await fetch(`${API_BASE}/settings/knowledge/types`)
  if (!response.ok) throw new Error('Failed to fetch knowledge types')
  return response.json()
}

export async function listKnowledge(
  dsId: number,
  kbType?: string,
  page = 1,
  pageSize = 50,
): Promise<APIResponse<KnowledgeConfig>> {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (kbType) params.set('kb_type', kbType)

  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/knowledge?${params}`)
  if (!response.ok) throw new Error('Failed to fetch knowledge')
  return response.json()
}

export async function createKnowledge(dsId: number, data: Partial<KnowledgeConfig>): Promise<KnowledgeConfig> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/knowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('Failed to create knowledge')
  return response.json()
}

export async function updateKnowledge(dsId: number, id: number, data: Partial<KnowledgeConfig>): Promise<KnowledgeConfig> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/knowledge/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('Failed to update knowledge')
  return response.json()
}

export async function deleteKnowledge(dsId: number, id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/knowledge/${id}`, { method: 'DELETE' })
  if (!response.ok) throw new Error('Failed to delete knowledge')
}

export async function importKnowledge(dsId: number, items: Partial<KnowledgeConfig>[]): Promise<{ success: number; failed: number; total: number }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/knowledge/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  if (!response.ok) throw new Error('Failed to import knowledge')
  return response.json()
}

// ============ Schema 学习 API（Phase 5 新增）============

/**
 * 触发数据源 Schema 学习
 */
export async function triggerSchemaLearning(dsId: number): Promise<{ success: boolean; task_id: number; status: string; message: string }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/learn`, {
    method: 'POST',
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to trigger learning')
  }
  return response.json()
}

/**
 * 查询学习进度
 */
export async function getLearningProgress(taskId: number): Promise<LearningProgress> {
  const response = await fetch(`${API_BASE}/settings/learning/${taskId}`)
  if (!response.ok) throw new Error('Failed to fetch learning progress')
  return response.json()
}

/**
 * 列出学习任务
 */
export async function listLearningTasks(datasourceId?: number): Promise<{ items: LearningProgress[] }> {
  const params = datasourceId ? `?datasource_id=${datasourceId}` : ''
  const response = await fetch(`${API_BASE}/settings/learning/tasks${params}`)
  if (!response.ok) throw new Error('Failed to fetch learning tasks')
  return response.json()
}

/**
 * 获取 Schema 缓存
 */
export async function getSchemaCache(dsId: number): Promise<SchemaCache | null> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/schema`)
  if (response.status === 404) return null
  if (!response.ok) throw new Error('Failed to fetch schema cache')
  return response.json()
}

/**
 * 获取表列表（从 Schema 缓存）
 */
export async function getSchemaTables(dsId: number): Promise<{ items: TableSchema[]; total: number }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/schema/tables`)
  if (!response.ok) throw new Error('Failed to fetch schema tables')
  return response.json()
}

/**
 * 获取单表 Schema
 */
export async function getTableSchema(dsId: number, tableName: string): Promise<TableSchema> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/schema/tables/${encodeURIComponent(tableName)}`)
  if (!response.ok) throw new Error('Failed to fetch table schema')
  return response.json()
}

/**
 * 清空 Schema 缓存
 */
export async function clearSchemaCache(dsId: number): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/schema/cache`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to clear schema cache')
  }
  return response.json()
}

/**
 * 清空并重新学习 Schema
 */
export async function relearnSchema(dsId: number): Promise<{ success: boolean; task_id?: number; message: string }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/schema/relearn`, {
    method: 'POST',
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to relearn schema')
  }
  return response.json()
}