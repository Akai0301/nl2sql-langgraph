---
name: ui-pc
description: |
  前端（frontend）组件开发指南。基于 Vue 3 + Vite + TypeScript + TailwindCSS + ECharts + Vue Flow。

  触发场景：
  - 开发前端问数界面
  - 使用 Vue 3 Composition API
  - 表格、图表、流程图等前端 UI
  - SSE 流式数据消费
  - ECharts 图表集成
  - Vue Flow 流程图可视化

  触发词：Vue、前端组件、ECharts、Vue Flow、TailwindCSS、流程图、图表、表格、SSE、流式

  适用目录：frontend/**
---

# 前端组件开发指南

> **适用于**: `frontend/` 目录下的智能问数前端开发
> **技术栈**: Vue 3.5 + Vite 6 + TypeScript 5 + TailwindCSS 3 + ECharts 5 + Vue Flow

---

## 目录结构

```
frontend/src/
├── api/                # API 接口定义
│   └── query.ts        # 查询 API（SSE 流式 + 同步）
├── assets/             # 静态资源
│   └── main.css        # 全局样式（TailwindCSS）
├── stores/             # Pinia Store
│   └── queryStore.ts   # 查询状态管理
├── types/              # TypeScript 类型定义
│   └── index.ts        # 共享类型
├── views/              # 页面视图
│   ├── QueryView.vue   # 主查询页面
│   └── components/     # 组件
│       ├── QueryInput.vue       # 查询输入框
│       ├── InputBox.vue         # 输入框组件
│       ├── FlowGraph.vue        # LangGraph 流程图（Vue Flow）
│       ├── StepProgressBar.vue  # 步骤进度条
│       ├── MessageCard.vue      # 消息卡片
│       ├── ResultTable.vue      # 结果表格
│       ├── ChartPanel.vue       # 图表面板（ECharts）
│       ├── HistoryPanel.vue     # 历史记录面板
│       ├── Sidebar.vue          # 侧边栏
│       ├── ExampleQuestions.vue # 示例问题
│       └── step-details/        # 步骤详情组件
├── App.vue             # 根组件
├── main.ts             # 入口文件
└── vite-env.d.ts       # Vite 类型声明
```

---

## 核心组件说明

### 1. QueryView.vue - 主查询页面

主页面组合了所有子组件，处理查询流程：

```vue
<script setup lang="ts">
import { useQueryStore } from '@/stores/queryStore'

const queryStore = useQueryStore()

// 提交查询
async function handleSubmit(question: string) {
  await queryStore.submitQuery(question)
}
</script>
```

### 2. FlowGraph.vue - LangGraph 流程图

使用 Vue Flow 可视化 LangGraph 执行流程：

```vue
<script setup lang="ts">
import { VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'

const { nodes, edges } = useVueFlow()

// 节点数据从后端 /graph/structure 接口获取
</script>
```

### 3. ChartPanel.vue - 图表面板

使用 ECharts 渲染查询结果图表：

```vue
<script setup lang="ts">
import * as echarts from 'echarts'
import { onMounted, ref } from 'vue'

const chartRef = ref<HTMLElement>()

onMounted(() => {
  const chart = echarts.init(chartRef.value)
  // 根据 columns 和 rows 数据生成图表配置
})
</script>
```

### 4. ResultTable.vue - 结果表格

展示 SQL 查询结果：

```vue
<template>
  <table class="min-w-full divide-y divide-gray-200">
    <thead>
      <tr>
        <th v-for="col in columns" :key="col">{{ col }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="idx">
        <td v-for="(cell, i) in row" :key="i">{{ cell }}</td>
      </tr>
    </tbody>
  </table>
</template>
```

### 5. StepProgressBar.vue - 步骤进度条

展示 LangGraph 节点执行进度：

```vue
<script setup lang="ts">
defineProps<{
  steps: { node: string; label: string; status: 'pending' | 'running' | 'completed' | 'error' }[]
}>()
</script>
```

---

## SSE 流式数据消费

### 使用 EventSource 消费流式接口

```typescript
// api/query.ts
export function streamQuery(question: string, onEvent: (event: MessageEvent) => void) {
  const url = `${BASE_URL}/stream?question=${encodeURIComponent(question)}`
  const eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    onEvent(event)
  }

  eventSource.onerror = () => {
    eventSource.close()
  }

  return () => eventSource.close()
}
```

### 在组件中使用

```vue
<script setup lang="ts">
import { streamQuery } from '@/api/query'

function handleStream(question: string) {
  const close = streamQuery(question, (event) => {
    const data = JSON.parse(event.data)

    switch (data.type) {
      case 'node_start':
        // 更新节点状态为 running
        break
      case 'node_complete':
        // 更新节点状态为 completed
        break
      case 'result':
        // 显示最终结果
        break
    }
  })
}
</script>
```

---

## Pinia Store 使用

### queryStore.ts

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useQueryStore = defineStore('query', () => {
  const question = ref('')
  const sql = ref('')
  const columns = ref<string[]>([])
  const rows = ref<any[]>([])
  const loading = ref(false)
  const error = ref('')

  async function submitQuery(q: string) {
    loading.value = true
    error.value = ''
    try {
      // 调用 API
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  return { question, sql, columns, rows, loading, error, submitQuery }
})
```

---

## TailwindCSS 使用

项目使用 TailwindCSS 进行样式管理：

```vue
<template>
  <div class="flex flex-col h-full">
    <div class="bg-white shadow-md p-4">
      <!-- 头部区域 -->
    </div>
    <div class="flex-1 overflow-auto p-4">
      <!-- 内容区域 -->
    </div>
  </div>
</template>
```

---

## 参考文件

| 用途 | 路径 |
|------|------|
| 主查询页面 | `frontend/src/views/QueryView.vue` |
| 查询 API | `frontend/src/api/query.ts` |
| 状态管理 | `frontend/src/stores/queryStore.ts` |
| 类型定义 | `frontend/src/types/index.ts` |
| 流程图组件 | `frontend/src/views/components/FlowGraph.vue` |
| 图表组件 | `frontend/src/views/components/ChartPanel.vue` |