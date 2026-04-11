<template>
  <div class="retrieval-list">
    <div v-if="items.length === 0" class="empty-text">
      {{ emptyText }}
    </div>
    <div v-else class="items-container">
      <div
        v-for="(item, index) in items"
        :key="index"
        class="retrieval-item"
      >
        <!-- 混合检索状态指示器 -->
        <div class="retrieval-method-badge">
          <span :class="getMethodClass(item)" class="method-tag">
            {{ getMethodLabel(item) }}
          </span>
          <span v-if="item.rrf_score" class="rrf-score">
            RRF: {{ formatRrfScore(item.rrf_score) }}
          </span>
        </div>
        <div
          v-for="field in fields"
          :key="field.key"
          class="item-field"
        >
          <span class="field-label">{{ field.label }}:</span>
          <span class="field-value">{{ getItemValue(item, field.key) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  items: Record<string, unknown>[]
  fields: { key: string; label: string }[]
  emptyText: string
}>()

function getItemValue(item: Record<string, unknown>, key: string): string {
  const value = item[key]
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function getMethodLabel(item: Record<string, unknown>): string {
  const method = item['_retrieval_method'] as string | undefined
  switch (method) {
    case 'hybrid':
      return '混合'
    case 'like_only':
      return '关键词'
    case 'vector_only':
      return '向量'
    default:
      return '未知'
  }
}

function getMethodClass(item: Record<string, unknown>): string {
  const method = item['_retrieval_method'] as string | undefined
  switch (method) {
    case 'hybrid':
      return 'method-hybrid'
    case 'like_only':
      return 'method-like'
    case 'vector_only':
      return 'method-vector'
    default:
      return 'method-unknown'
  }
}

function formatRrfScore(score: unknown): string {
  if (typeof score === 'number') {
    return score.toFixed(4)
  }
  return String(score)
}
</script>

<style scoped>
.retrieval-list {
  max-height: 300px;
  overflow-y: auto;
}

.empty-text {
  color: #9ca3af;
  text-align: center;
  padding: 24px;
  font-size: 14px;
}

.items-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.retrieval-item {
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 13px;
}

.retrieval-method-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.method-tag {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.method-hybrid {
  background: #dbeafe;
  color: #1d4ed8;
}

.method-like {
  background: #fef3c7;
  color: #b45309;
}

.method-vector {
  background: #d1fae5;
  color: #047857;
}

.method-unknown {
  background: #e5e7eb;
  color: #6b7280;
}

.rrf-score {
  color: #6b7280;
  font-size: 11px;
}

.item-field {
  margin-bottom: 4px;
}

.item-field:last-child {
  margin-bottom: 0;
}

.field-label {
  color: #6b7280;
  margin-right: 4px;
}

.field-value {
  color: #1f2937;
}
</style>
