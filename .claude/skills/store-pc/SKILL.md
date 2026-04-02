---
name: store-pc
description: |
  前端（frontend）状态管理指南。基于 Pinia 实现问数状态管理。

  触发场景：
  - 创建/使用 Pinia Store
  - 跨组件数据共享
  - 查询状态管理
  - 历史记录状态

  触发词：Pinia、defineStore、状态管理、Store、queryStore

  适用目录：frontend/**
---

# 前端状态管理指南

> **适用于**: `frontend/` 目录下的智能问数前端
> **技术栈**: Vue 3.5 + Pinia 3 + TypeScript

---

## Store 文件位置

```
frontend/src/stores/
└── queryStore.ts    # 查询状态管理
```

---

## queryStore.ts - 查询状态管理

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { QueryResult, GraphNode, HistoryItem } from '@/types'

export const useQueryStore = defineStore('query', () => {
  // 当前问题
  const question = ref('')

  // 生成的 SQL
  const sql = ref('')

  // 查询结果
  const columns = ref<string[]>([])
  const rows = ref<any[][]>([])

  // LangGraph 节点状态
  const nodes = ref<GraphNode[]>([])

  // 执行状态
  const loading = ref(false)
  const error = ref('')

  // 历史记录
  const history = ref<HistoryItem[]>([])

  // 提交查询
  async function submitQuery(q: string) {
    question.value = q
    loading.value = true
    error.value = ''
    try {
      // 调用 API 或 SSE 流式接口
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  // 更新节点状态
  function updateNodeStatus(nodeId: string, status: string) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.status = status
    }
  }

  // 添加历史记录
  function addHistory(item: HistoryItem) {
    history.value.unshift(item)
  }

  // 清空结果
  function clearResult() {
    question.value = ''
    sql.value = ''
    columns.value = []
    rows.value = []
    nodes.value = []
    error.value = ''
  }

  return {
    question, sql, columns, rows, nodes, loading, error, history,
    submitQuery, updateNodeStatus, addHistory, clearResult
  }
})
```

---

## 在组件中使用 Store

```vue
<script setup lang="ts">
import { useQueryStore } from '@/stores/queryStore'
import { storeToRefs } from 'pinia'

const queryStore = useQueryStore()

// 使用 storeToRefs 解构响应式状态
const { question, sql, columns, rows, loading, error } = storeToRefs(queryStore)

// 方法直接解构
const { submitQuery, clearResult } = queryStore
</script>

<template>
  <div v-if="loading">加载中...</div>
  <div v-else-if="error">{{ error }}</div>
  <div v-else>
    <pre>{{ sql }}</pre>
    <table>
      <thead>
        <tr><th v-for="col in columns" :key="col">{{ col }}</th></tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i">
          <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

---

## 最佳实践

### 1. 使用 Composition API 风格

```typescript
// ✅ 推荐：Composition API 风格
export const useQueryStore = defineStore('query', () => {
  const count = ref(0)
  const increment = () => count.value++
  return { count, increment }
})

// ❌ 不推荐：Options API 风格（本项目使用 Composition API）
export const useQueryStore = defineStore('query', {
  state: () => ({ count: 0 }),
  actions: {
    increment() { this.count++ }
  }
})
```

### 2. 响应式解构

```typescript
import { storeToRefs } from 'pinia'

const store = useQueryStore()

// ✅ 正确：状态用 storeToRefs
const { question, loading } = storeToRefs(store)

// ✅ 正确：方法直接解构
const { submitQuery, clearResult } = store

// ❌ 错误：直接解构状态会丢失响应式
const { question } = store  // 不会响应式更新
```

### 3. TypeScript 类型定义

```typescript
// types/index.ts
export interface QueryResult {
  question: string
  sql: string
  columns: string[]
  rows: any[][]
}

export interface GraphNode {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

export interface HistoryItem {
  id: number
  question: string
  sql: string
  created_at: string
  is_favorite: boolean
}
```

---

## 参考文件

| 用途 | 路径 |
|------|------|
| 查询状态管理 | `frontend/src/stores/queryStore.ts` |
| 类型定义 | `frontend/src/types/index.ts` |