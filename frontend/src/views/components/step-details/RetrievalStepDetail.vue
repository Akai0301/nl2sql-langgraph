<template>
  <div class="retrieval-detail">
    <div class="detail-header">
      <el-icon class="mr-2"><Collection /></el-icon>
      <span>智能检索结果</span>
      <!-- 混合检索状态指示 -->
      <div v-if="hasHybridResults" class="hybrid-status-badge">
        <el-icon><Connection /></el-icon>
        <span>混合检索已激活</span>
      </div>
    </div>

    <!-- 检索方法统计 -->
    <div v-if="hasHybridResults" class="method-stats">
      <span class="stat-item hybrid">
        混合: {{ hybridCount }}
      </span>
      <span class="stat-item like">
        关键词: {{ likeOnlyCount }}
      </span>
      <span class="stat-item vector">
        向量: {{ vectorOnlyCount }}
      </span>
    </div>

    <div class="retrieval-tabs">
      <el-tabs v-model="activeTab" type="card" size="small">
        <el-tab-pane label="知识库" name="knowledge">
          <RetrievalList
            :items="knowledgeItems"
            :fields="knowledgeFields"
            empty-text="未检索到相关知识"
          />
        </el-tab-pane>
        <el-tab-pane label="指标" name="metrics">
          <RetrievalList
            :items="metricsItems"
            :fields="metricsFields"
            empty-text="未检索到相关指标"
          />
        </el-tab-pane>
        <el-tab-pane label="元数据" name="metadata">
          <RetrievalList
            :items="metadataItems"
            :fields="metadataFields"
            empty-text="未检索到相关元数据"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="retrieval-summary">
      <span class="summary-item">
        <el-icon><Reading /></el-icon>
        知识: {{ knowledgeItems.length }} 条
      </span>
      <span class="summary-item">
        <el-icon><TrendCharts /></el-icon>
        指标: {{ metricsItems.length }} 条
      </span>
      <span class="summary-item">
        <el-icon><Grid /></el-icon>
        元数据: {{ metadataItems.length }} 条
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Collection, Reading, TrendCharts, Grid, Connection } from '@element-plus/icons-vue'
import RetrievalList from './RetrievalList.vue'

const props = defineProps<{
  nodeId: string
  output?: Record<string, unknown>
  allRetrievalOutputs?: Record<string, unknown>
}>()

const activeTab = ref('knowledge')

const knowledgeItems = computed(() => {
  const output = props.allRetrievalOutputs?.knowledge_retrieval as Record<string, unknown> | undefined
  if (!output?.knowledge_hits) return []
  const hits = output.knowledge_hits
  return Array.isArray(hits) ? hits : []
})

const metricsItems = computed(() => {
  const output = props.allRetrievalOutputs?.metrics_retrieval as Record<string, unknown> | undefined
  if (!output?.metrics_hits) return []
  const hits = output.metrics_hits
  return Array.isArray(hits) ? hits : []
})

const metadataItems = computed(() => {
  const output = props.allRetrievalOutputs?.metadata_retrieval as Record<string, unknown> | undefined
  if (!output?.metadata_hits) return []
  const hits = output.metadata_hits
  return Array.isArray(hits) ? hits : []
})

// 检测是否启用了混合检索
const hasHybridResults = computed(() => {
  const allItems = [...knowledgeItems.value, ...metricsItems.value, ...metadataItems.value]
  return allItems.some(item => item['_retrieval_method'] !== undefined)
})

// 统计各检索方法数量
const hybridCount = computed(() => {
  const allItems = [...knowledgeItems.value, ...metricsItems.value, ...metadataItems.value]
  return allItems.filter(item => item['_retrieval_method'] === 'hybrid').length
})

const likeOnlyCount = computed(() => {
  const allItems = [...knowledgeItems.value, ...metricsItems.value, ...metadataItems.value]
  return allItems.filter(item => item['_retrieval_method'] === 'like_only').length
})

const vectorOnlyCount = computed(() => {
  const allItems = [...knowledgeItems.value, ...metricsItems.value, ...metadataItems.value]
  return allItems.filter(item => item['_retrieval_method'] === 'vector_only').length
})

const knowledgeFields = [
  { key: 'topic', label: '主题' },
  { key: 'business_meaning', label: '业务含义' },
]

const metricsFields = [
  { key: 'metric_name', label: '指标名称' },
  { key: 'business_definition', label: '业务定义' },
  { key: 'aggregation_rule', label: '聚合规则' },
]

const metadataFields = [
  { key: 'metric_name', label: '指标名称' },
  { key: 'fact_table', label: '事实表' },
  { key: 'measure_sql_expression', label: '度量表达式' },
]
</script>

<style scoped>
.retrieval-detail {
  min-width: 500px;
}

.detail-header {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #374151;
  margin-bottom: 12px;
}

.hybrid-status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 12px;
  padding: 4px 8px;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 6px;
  font-size: 12px;
}

.method-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
}

.stat-item {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.stat-item.hybrid {
  background: #dbeafe;
  color: #1d4ed8;
}

.stat-item.like {
  background: #fef3c7;
  color: #b45309;
}

.stat-item.vector {
  background: #d1fae5;
  color: #047857;
}

.retrieval-tabs {
  margin-bottom: 12px;
}

.retrieval-summary {
  display: flex;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #6b7280;
}

.summary-item .el-icon {
  color: #9ca3af;
}
</style>
