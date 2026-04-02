import type {
  AIConfig,
  DataSourceConfig,
  TableInfo,
  ColumnInfo,
  KnowledgeConfig,
  KnowledgeType,
  APIResponse,
  TestConnectionResult,
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