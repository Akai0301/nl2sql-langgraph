import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GraphStructure, NodeState, QueryResult, QueryHistory, ConversationMessage, StepState, HistoryListParams } from '@/types'
import { createStreamingConnection, listHistory, toggleFavorite as apiToggleFavorite, deleteHistory as apiDeleteHistory, batchDeleteHistory, clearHistory as apiClearHistory } from '@/api/query'

// Node label mapping
const NODE_LABELS: Record<string, string> = {
  analyze_question: '问题分析',
  knowledge_retrieval: '知识检索',
  metrics_retrieval: '指标检索',
  metadata_retrieval: '元数据检索',
  merge_context: '上下文合并',
  metadata_analysis: '元数据分析',
  sql_generation: 'SQL生成',
  sql_execution: 'SQL执行',
}

// Step order for display
const STEP_ORDER = [
  'analyze_question',
  'knowledge_retrieval',
  'metrics_retrieval',
  'metadata_retrieval',
  'merge_context',
  'metadata_analysis',
  'sql_generation',
  'sql_execution',
]

export const useQueryStore = defineStore('query', () => {
  // State
  const isExecuting = ref(false)
  const currentQuestion = ref('')
  const currentSessionId = ref<number | null>(null)
  const graphStructure = ref<GraphStructure | null>(null)
  const nodeStates = ref<Map<string, NodeState>>(new Map())
  const result = ref<QueryResult | null>(null)
  const error = ref<string | null>(null)
  const eventSource = ref<EventSource | null>(null)

  // History state (from API)
  const history = ref<QueryHistory[]>([])
  const historyTotal = ref(0)
  const historyPage = ref(1)
  const historyPageSize = ref(20)
  const historyLoading = ref(false)

  // Conversation state
  const conversations = ref<ConversationMessage[]>([])

  // Current executing message
  const currentSteps = ref<Map<string, StepState>>(new Map())

  // Computed
  const hasResult = computed(() => result.value !== null)
  const hasError = computed(() => error.value !== null)

  // Get ordered steps for current execution
  const orderedSteps = computed(() => {
    const steps: StepState[] = []
    for (const nodeId of STEP_ORDER) {
      const step = currentSteps.value.get(nodeId)
      if (step) {
        steps.push(step)
      }
    }
    return steps
  })

  // Load history from API
  async function loadHistory(params: HistoryListParams = {}) {
    historyLoading.value = true
    try {
      const response = await listHistory({
        page: params.page ?? historyPage.value,
        page_size: params.page_size ?? historyPageSize.value,
        is_favorite: params.is_favorite,
        search: params.search,
        start_date: params.start_date,
        end_date: params.end_date,
      })
      history.value = response.items
      historyTotal.value = response.total
      historyPage.value = response.page
      historyPageSize.value = response.page_size
    } catch (e) {
      console.error('Failed to load history:', e)
    } finally {
      historyLoading.value = false
    }
  }

  // Actions
  function initializeGraph(structure: GraphStructure) {
    graphStructure.value = structure
    nodeStates.value.clear()

    for (const node of structure.nodes) {
      nodeStates.value.set(node.id, {
        id: node.id,
        label: node.label,
        status: 'pending',
      })
    }
  }

  function updateNodeStatus(nodeId: string, status: NodeState['status'], output?: Record<string, unknown>, errorMsg?: string) {
    const existing = nodeStates.value.get(nodeId)
    if (existing) {
      nodeStates.value.set(nodeId, {
        ...existing,
        status,
        output,
        error: errorMsg,
      })
    }

    // Also update current steps
    const label = NODE_LABELS[nodeId] || nodeId
    currentSteps.value.set(nodeId, {
      id: nodeId,
      label,
      status,
      output,
      error: errorMsg,
    })
  }

  function resetAllNodes() {
    nodeStates.value.forEach((state, id) => {
      nodeStates.value.set(id, {
        ...state,
        status: 'pending',
        output: undefined,
        error: undefined,
      })
    })
    currentSteps.value.clear()
  }

  // Add user message to conversation
  function addUserMessage(content: string): string {
    const id = `msg-${Date.now()}`
    conversations.value.push({
      id,
      role: 'user',
      content,
      timestamp: Date.now(),
    })
    return id
  }

  // Add/update assistant message
  function updateAssistantMessage(messageId: string, updates: Partial<ConversationMessage>) {
    const idx = conversations.value.findIndex(m => m.id === messageId)
    if (idx >= 0) {
      conversations.value[idx] = {
        ...conversations.value[idx],
        ...updates,
      }
    }
  }

  async function executeQuery(question: string) {
    if (isExecuting.value) return

    // Reset state
    isExecuting.value = true
    currentQuestion.value = question
    result.value = null
    error.value = null
    resetAllNodes()

    // Add user message
    addUserMessage(question)

    // Create assistant message placeholder
    const assistantId = `msg-${Date.now()}-assistant`
    conversations.value.push({
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      steps: [],
    })

    return new Promise<void>((resolve, reject) => {
      const es = createStreamingConnection(
        question,
        (eventType, data) => {
          switch (eventType) {
            case 'init':
              initializeGraph((data as { graph: GraphStructure }).graph)
              break

            case 'node_start':
              const startData = data as { node: string; label: string }
              updateNodeStatus(startData.node, 'running')
              break

            case 'node_complete':
              const completeData = data as { node: string; status: string; output?: Record<string, unknown> }
              updateNodeStatus(completeData.node, 'completed', completeData.output)
              // Update assistant message steps
              updateAssistantMessage(assistantId, {
                steps: [...orderedSteps.value],
              })
              break

            case 'node_error':
              const errorData = data as { node: string; label: string; error: string }
              updateNodeStatus(errorData.node, 'error', undefined, errorData.error)
              updateAssistantMessage(assistantId, {
                steps: [...orderedSteps.value],
                error: errorData.error,
              })
              break

            case 'result':
              const resultData = data as QueryResult & { session_id?: number }
              result.value = {
                question: resultData.question,
                sql: resultData.sql,
                columns: resultData.columns || [],
                rows: resultData.rows || [],
                attempt: resultData.attempt || 1,
                executionError: resultData.executionError || null,
              }
              // Update session_id if returned
              if (resultData.session_id) {
                currentSessionId.value = resultData.session_id
              }
              // Update assistant message with result
              updateAssistantMessage(assistantId, {
                steps: [...orderedSteps.value],
                result: result.value,
              })
              // Reload history after query completes
              loadHistory()
              break

            case 'error':
              const errData = data as { error: string }
              error.value = errData.error
              updateAssistantMessage(assistantId, {
                error: errData.error,
              })
              break
          }
        },
        (err) => {
          error.value = err.message
          isExecuting.value = false
          updateAssistantMessage(assistantId, {
            error: err.message,
          })
          reject(err)
        },
        () => {
          isExecuting.value = false
          resolve()
        },
        currentSessionId.value  // Pass session_id for retry
      )

      eventSource.value = es
    })
  }

  // Re-execute with edited SQL
  async function executeEditedSql(sql: string) {
    if (isExecuting.value) return

    // This would need a new backend endpoint to execute SQL directly
    // For now, we'll just show the SQL
    const assistantId = `msg-${Date.now()}-assistant`
    conversations.value.push({
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      result: {
        question: '编辑后的 SQL',
        sql,
        columns: [],
        rows: [],
        attempt: 1,
        executionError: null,
      },
    })
  }

  function cancelQuery() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    isExecuting.value = false
  }

  async function toggleFavorite(id: number) {
    const item = history.value.find(h => h.id === id)
    if (item) {
      try {
        const updated = await apiToggleFavorite(id, !item.is_favorite)
        item.is_favorite = updated.is_favorite
      } catch (e) {
        console.error('Failed to toggle favorite:', e)
      }
    }
  }

  async function removeFromHistory(id: number) {
    try {
      await apiDeleteHistory(id)
      await loadHistory()
    } catch (e) {
      console.error('Failed to delete history:', e)
    }
  }

  async function batchRemoveFromHistory(ids: number[]) {
    try {
      await batchDeleteHistory(ids)
      await loadHistory()
    } catch (e) {
      console.error('Failed to batch delete history:', e)
    }
  }

  async function clearAllHistory() {
    try {
      await apiClearHistory()
      await loadHistory()
    } catch (e) {
      console.error('Failed to clear history:', e)
    }
  }

  function clearConversations() {
    conversations.value = []
    currentSteps.value.clear()
    result.value = null
    error.value = null
    currentSessionId.value = null
  }

  // Load a history item as the current result (without re-executing)
  function loadHistoryResult(item: QueryHistory) {
    // Reset state
    currentQuestion.value = item.question
    result.value = {
      question: item.question,
      sql: item.generated_sql || '',
      columns: item.columns || [],
      rows: item.rows || [],
      attempt: 1,
      executionError: item.execution_error || null,
    }
    error.value = item.execution_error || null

    // Add user message
    addUserMessage(item.question)

    // Add assistant message with result
    conversations.value.push({
      id: `msg-${Date.now()}-assistant`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      result: result.value,
    })
  }

  // Execute query with specific datasource
  async function executeQueryWithDatasource(question: string, datasourceId: number): Promise<QueryResult> {
    if (isExecuting.value) {
      throw new Error('Already executing')
    }

    // Reset state
    isExecuting.value = true
    currentQuestion.value = question
    result.value = null
    error.value = null
    resetAllNodes()

    return new Promise<QueryResult>((resolve, reject) => {
      const es = createStreamingConnection(
        question,
        (eventType, data) => {
          switch (eventType) {
            case 'init':
              initializeGraph((data as { graph: GraphStructure }).graph)
              break

            case 'node_start':
              const startData = data as { node: string; label: string }
              updateNodeStatus(startData.node, 'running')
              break

            case 'node_complete':
              const completeData = data as { node: string; status: string; output?: Record<string, unknown> }
              updateNodeStatus(completeData.node, 'completed', completeData.output)
              break

            case 'node_error':
              const errorData = data as { node: string; label: string; error: string }
              updateNodeStatus(errorData.node, 'error', undefined, errorData.error)
              break

            case 'result':
              const resultData = data as QueryResult & { session_id?: number }
              result.value = {
                question: resultData.question,
                sql: resultData.sql,
                columns: resultData.columns || [],
                rows: resultData.rows || [],
                attempt: resultData.attempt || 1,
                executionError: resultData.executionError || null,
              }
              resolve(result.value)
              break

            case 'error':
              const errData = data as { error: string }
              error.value = errData.error
              reject(new Error(errData.error))
              break
          }
        },
        (err) => {
          error.value = err.message
          isExecuting.value = false
          reject(err)
        },
        () => {
          isExecuting.value = false
        },
        null,  // session_id
        datasourceId
      )

      eventSource.value = es
    })
  }

  // Load history on init
  loadHistory()

  return {
    // State
    isExecuting,
    currentQuestion,
    currentSessionId,
    graphStructure,
    nodeStates,
    result,
    error,
    history,
    historyTotal,
    historyPage,
    historyPageSize,
    historyLoading,
    conversations,
    orderedSteps,
    // Computed
    hasResult,
    hasError,
    // Actions
    executeQuery,
    executeQueryWithDatasource,
    executeEditedSql,
    cancelQuery,
    initializeGraph,
    updateNodeStatus,
    loadHistory,
    toggleFavorite,
    removeFromHistory,
    batchRemoveFromHistory,
    clearAllHistory,
    clearConversations,
    loadHistoryResult,
  }
})
