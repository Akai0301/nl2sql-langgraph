---
name: http-client
description: |
  前端（frontend）HTTP 客户端指南。使用原生 fetch 进行 API 调用和 SSE 流式数据消费。

  触发场景：
  - 编写前端 API 调用函数
  - 消费 SSE 流式接口
  - 处理 API 错误响应
  - 调用后端查询接口

  触发词：fetch、API调用、SSE、流式、接口调用、HTTP请求

  适用目录：frontend/**
---

# 前端 HTTP 客户端指南

> **适用于**: `frontend/` 目录下的智能问数前端
> **技术栈**: 原生 fetch API + EventSource（SSE）

---

## API 文件位置

```
frontend/src/api/
└── query.ts    # 查询 API（同步 + SSE 流式）
```

---

## 一、同步查询接口

### 使用 fetch 调用 POST /query

```typescript
// api/query.ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export interface QueryResult {
  question: string
  sql: string
  columns: string[]
  rows: any[][]
  attempt: number
  execution_error: string | null
}

export async function submitQuery(question: string): Promise<QueryResult> {
  const response = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return response.json()
}
```

### 在组件中使用

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { submitQuery, type QueryResult } from '@/api/query'

const result = ref<QueryResult | null>(null)
const loading = ref(false)
const error = ref('')

async function handleSubmit(question: string) {
  loading.value = true
  error.value = ''
  try {
    result.value = await submitQuery(question)
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}
</script>
```

---

## 二、SSE 流式接口

### 使用 EventSource 消费 GET /stream

```typescript
// api/query.ts
export interface StreamEvent {
  type: 'init' | 'node_start' | 'node_complete' | 'result'
  data: any
}

export function streamQuery(
  question: string,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const url = `${BASE_URL}/stream?question=${encodeURIComponent(question)}`
  const eventSource = new EventSource(url)

  eventSource.addEventListener('init', (e) => {
    onEvent({ type: 'init', data: JSON.parse(e.data) })
  })

  eventSource.addEventListener('node_start', (e) => {
    onEvent({ type: 'node_start', data: JSON.parse(e.data) })
  })

  eventSource.addEventListener('node_complete', (e) => {
    onEvent({ type: 'node_complete', data: JSON.parse(e.data) })
  })

  eventSource.addEventListener('result', (e) => {
    onEvent({ type: 'result', data: JSON.parse(e.data) })
    eventSource.close()
  })

  eventSource.onerror = (e) => {
    onError?.(new Error('SSE connection error'))
    eventSource.close()
  }

  // 返回关闭函数
  return () => eventSource.close()
}
```

### 在组件中使用 SSE

```vue
<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { streamQuery, type StreamEvent } from '@/api/query'

const nodes = ref<any[]>([])
const result = ref<any>(null)
const loading = ref(false)

let closeStream: (() => void) | null = null

function handleStream(question: string) {
  loading.value = true
  nodes.value = []

  closeStream = streamQuery(
    question,
    (event: StreamEvent) => {
      switch (event.type) {
        case 'init':
          // 初始化图结构
          nodes.value = event.data.graph.nodes
          break
        case 'node_start':
          // 更新节点状态为 running
          updateNodeStatus(event.data.node, 'running')
          break
        case 'node_complete':
          // 更新节点状态为 completed
          updateNodeStatus(event.data.node, 'completed')
          break
        case 'result':
          // 显示最终结果
          result.value = event.data
          loading.value = false
          break
      }
    },
    (error) => {
      console.error('Stream error:', error)
      loading.value = false
    }
  )
}

function updateNodeStatus(nodeId: string, status: string) {
  const node = nodes.value.find(n => n.id === nodeId)
  if (node) {
    node.status = status
  }
}

onUnmounted(() => {
  closeStream?.()
})
</script>
```

---

## 三、历史记录 API

```typescript
// api/query.ts

export interface HistoryItem {
  id: number
  question: string
  generated_sql: string
  columns: string[]
  rows: any[][]
  is_favorite: boolean
  created_at: string
}

export interface HistoryListResponse {
  items: HistoryItem[]
  total: number
  page: number
  page_size: number
}

export async function getHistory(params: {
  page?: number
  page_size?: number
  is_favorite?: boolean
  search?: string
}): Promise<HistoryListResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.page_size) query.set('page_size', String(params.page_size))
  if (params.is_favorite !== undefined) query.set('is_favorite', String(params.is_favorite))
  if (params.search) query.set('search', params.search)

  const response = await fetch(`${BASE_URL}/history?${query}`)
  return response.json()
}

export async function deleteHistory(id: number): Promise<void> {
  await fetch(`${BASE_URL}/history/${id}`, { method: 'DELETE' })
}

export async function toggleFavorite(id: number, is_favorite: boolean): Promise<void> {
  await fetch(`${BASE_URL}/history/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_favorite }),
  })
}
```

---

## 四、错误处理

### 统一错误处理

```typescript
async function apiCall<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new ApiError(response.status, errorData.detail || 'Request failed')
  }

  return response.json()
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}
```

---

## 参考文件

| 用途 | 路径 |
|------|------|
| 查询 API | `frontend/src/api/query.ts` |
| 类型定义 | `frontend/src/types/index.ts` |