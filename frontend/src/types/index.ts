// Graph structure types
export interface GraphNode {
  id: string
  label: string
  type: 'start' | 'process' | 'parallel' | 'end'
}

export interface GraphEdge {
  source: string
  target: string
}

export interface GraphStructure {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Node status
export type NodeStatus = 'pending' | 'running' | 'completed' | 'error'

export interface NodeState {
  id: string
  label: string
  status: NodeStatus
  output?: Record<string, unknown>
  error?: string
}

// Query result types
export interface QueryResult {
  question: string
  sql: string | null
  columns: string[]
  rows: unknown[][]
  attempt: number
  executionError: string | null
}

// SSE event types
export type SSEEventType = 'init' | 'node_start' | 'node_complete' | 'node_error' | 'result' | 'error' | 'retry'

export interface SSEEvent {
  event: SSEEventType
  data: SSEEventData
}

export interface SSEInitData {
  graph: GraphStructure
  question: string
}

export interface SSENodeStartData {
  node: string
  label: string
  status: 'running'
}

export interface SSENodeCompleteData {
  node: string
  label: string
  status: 'completed'
  output: Record<string, unknown>
}

export interface SSENodeErrorData {
  node: string
  label: string
  status: 'error'
  error: string
}

export interface SSEResultData extends QueryResult {}

export interface SSEErrorData {
  error: string
}

export interface SSERetryData {
  attempt: number
  max_attempts: number
  error: string
}

export type SSEEventData =
  | SSEInitData
  | SSENodeStartData
  | SSENodeCompleteData
  | SSENodeErrorData
  | SSEResultData
  | SSEErrorData
  | SSERetryData

// History types (from MySQL backend)
export interface QueryHistory {
  id: number
  question: string
  generated_sql: string | null
  columns: string[]
  rows: unknown[][]
  execution_error: string | null
  is_favorite: boolean
  created_at: string
  updated_at: string
}

export interface HistoryListResponse {
  items: QueryHistory[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface HistoryListParams {
  page?: number
  page_size?: number
  is_favorite?: boolean
  search?: string
  start_date?: string
  end_date?: string
}

// Chart types
export interface ChartData {
  labels: string[]
  values: number[]
  series?: string[]
}

// Conversation types
export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  // For assistant messages
  steps?: StepState[]
  result?: QueryResult
  error?: string
}

// Step state for progress display
export interface StepState {
  id: string
  label: string
  status: NodeStatus
  output?: Record<string, unknown>
  error?: string
  expanded?: boolean
}

// Simplified step definitions for UI
export interface StepDefinition {
  id: string
  label: string
  icon: string
  description: string
  isParallel?: boolean
  parallelNodes?: string[]
}

// Example questions
export interface ExampleQuestion {
  id: string
  question: string
  category: string
}
