import type { GraphStructure, QueryResult, HistoryListResponse, HistoryListParams, QueryHistory, DataSource, ActiveDataSourceResponse, DataSourceListResponse } from '@/types'

// Use relative path - Vite proxy will forward to backend
const API_BASE = ''

/**
 * Execute a synchronous query
 */
export async function executeQuery(question: string): Promise<QueryResult> {
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  })

  if (!response.ok) {
    throw new Error(`Query failed: ${response.statusText}`)
  }

  const data = await response.json()
  return {
    question: data.question,
    sql: data.sql,
    columns: data.columns,
    rows: data.rows,
    attempt: data.attempt,
    executionError: data.execution_error,
  }
}

/**
 * Fetch the graph structure
 */
export async function fetchGraphStructure(): Promise<GraphStructure> {
  const response = await fetch(`${API_BASE}/graph/structure`)

  if (!response.ok) {
    throw new Error(`Failed to fetch graph structure: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Create an SSE connection for streaming query execution
 */
export function createStreamingConnection(
  question: string,
  onEvent: (event: string, data: unknown) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
  sessionId: number | null = null,
  datasourceId: number | null = null
): EventSource {
  const url = new URL(`${API_BASE}/stream`, window.location.origin)
  url.searchParams.set('question', question)
  if (sessionId !== null) {
    url.searchParams.set('session_id', String(sessionId))
  }
  if (datasourceId !== null) {
    url.searchParams.set('datasource_id', String(datasourceId))
  }

  const eventSource = new EventSource(url.toString())

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent(event.type || 'message', data)
    } catch (e) {
      console.error('Failed to parse SSE data:', e)
    }
  }

  eventSource.addEventListener('init', (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent('init', data)
    } catch (e) {
      console.error('Failed to parse init event:', e)
    }
  })

  eventSource.addEventListener('node_start', (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent('node_start', data)
    } catch (e) {
      console.error('Failed to parse node_start event:', e)
    }
  })

  eventSource.addEventListener('node_complete', (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent('node_complete', data)
    } catch (e) {
      console.error('Failed to parse node_complete event:', e)
    }
  })

  eventSource.addEventListener('node_error', (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent('node_error', data)
    } catch (e) {
      console.error('Failed to parse node_error event:', e)
    }
  })

  eventSource.addEventListener('result', (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent('result', data)
    } catch (e) {
      console.error('Failed to parse result event:', e)
    }
  })

  eventSource.addEventListener('error', (event) => {
    try {
      const data = JSON.parse((event as MessageEvent).data)
      eventSource.close() // Close connection on error
      onError(new Error(data.error || 'Unknown error'))
    } catch (e) {
      eventSource.close() // Close connection on error
      onError(new Error('Connection error'))
    }
  })

  // Track if we've already handled completion
  let isCompleted = false

  eventSource.onerror = () => {
    // If already completed, ignore error events from closing
    if (isCompleted) {
      return
    }
    isCompleted = true
    eventSource.close()
    // Only report error if we haven't received a result yet
    onError(new Error('SSE connection error'))
  }

  // Handle normal completion via result event
  eventSource.addEventListener('result', () => {
    if (!isCompleted) {
      isCompleted = true
      // Close connection after receiving result
      eventSource.close()
      onComplete()
    }
  })

  return eventSource
}

// ============ History API ============

/**
 * List query history with pagination and filters
 */
export async function listHistory(params: HistoryListParams = {}): Promise<HistoryListResponse> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.is_favorite !== undefined) searchParams.set('is_favorite', String(params.is_favorite))
  if (params.search) searchParams.set('search', params.search)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)

  const url = `${API_BASE}/history${searchParams.toString() ? '?' + searchParams.toString() : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch history: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get a single history record
 */
export async function getHistory(id: number): Promise<QueryHistory> {
  const response = await fetch(`${API_BASE}/history/${id}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch history: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Toggle favorite status
 */
export async function toggleFavorite(id: number, is_favorite: boolean): Promise<QueryHistory> {
  const response = await fetch(`${API_BASE}/history/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ is_favorite }),
  })

  if (!response.ok) {
    throw new Error(`Failed to update history: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Delete a history record
 */
export async function deleteHistory(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/history/${id}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`Failed to delete history: ${response.statusText}`)
  }
}

/**
 * Delete multiple history records
 */
export async function batchDeleteHistory(ids: number[]): Promise<{ deleted_count: number }> {
  const response = await fetch(`${API_BASE}/history/batch-delete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ids }),
  })

  if (!response.ok) {
    throw new Error(`Failed to batch delete history: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Clear all history
 */
export async function clearHistory(): Promise<{ deleted_count: number }> {
  const response = await fetch(`${API_BASE}/history/clear`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`Failed to clear history: ${response.statusText}`)
  }

  return response.json()
}

// ============ DataSource API ============

/**
 * Get the active datasource for query
 */
export async function getActiveDatasource(): Promise<ActiveDataSourceResponse> {
  const response = await fetch(`${API_BASE}/settings/datasource/active`)

  if (!response.ok) {
    throw new Error(`Failed to fetch active datasource: ${response.statusText}`)
  }

  return response.json()
}

/**
 * List all datasources
 */
export async function listDatasources(): Promise<DataSourceListResponse> {
  const response = await fetch(`${API_BASE}/settings/datasource`)

  if (!response.ok) {
    throw new Error(`Failed to fetch datasources: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Set datasource as query target
 */
export async function activateDatasource(dsId: number): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/settings/datasource/${dsId}/activate-query`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to activate datasource: ${response.statusText}`)
  }

  return response.json()
}
