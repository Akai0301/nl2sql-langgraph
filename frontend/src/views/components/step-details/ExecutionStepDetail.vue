<template>
  <div class="execution-detail">
    <div class="detail-header">
      <el-icon class="mr-2"><CircleCheck /></el-icon>
      <span>执行结果</span>
      <el-tag v-if="status" :type="statusType" size="small" class="ml-2">
        {{ status }}
      </el-tag>
    </div>

    <div class="detail-content">
      <!-- Success -->
      <div v-if="!error" class="success-info">
        <div class="info-row">
          <span class="info-label">返回行数</span>
          <span class="info-value">{{ rowCount }} 行</span>
        </div>
        <div v-if="columns.length > 0" class="columns-preview">
          <span class="info-label">列</span>
          <div class="columns-list">
            <el-tag
              v-for="col in columns.slice(0, 5)"
              :key="col"
              size="small"
              type="info"
            >
              {{ col }}
            </el-tag>
            <span v-if="columns.length > 5" class="more-cols">
              +{{ columns.length - 5 }} 列
            </span>
          </div>
        </div>
        <!-- Preview rows -->
        <div v-if="previewRows.length > 0" class="rows-preview">
          <span class="info-label">数据预览</span>
          <div class="preview-table">
            <table>
              <thead>
                <tr>
                  <th v-for="col in columns.slice(0, 4)" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in previewRows" :key="idx">
                  <td v-for="(val, vIdx) in row.slice(0, 4)" :key="vIdx">{{ formatValue(val) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-else class="error-info">
        <el-alert type="error" :closable="false">
          <template #title>执行失败</template>
          <div class="error-message">{{ error }}</div>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck } from '@element-plus/icons-vue'
import type { QueryResult } from '@/types'

const props = defineProps<{
  output?: Record<string, unknown>
  result?: QueryResult | null
}>()

const status = computed(() => {
  if (error.value) return '失败'
  return '成功'
})

const statusType = computed(() => {
  return error.value ? 'danger' : 'success'
})

const error = computed(() => {
  if (props.result?.executionError) return props.result.executionError
  const execError = props.output?.execution_error as string | undefined
  if (execError) return execError
  return null
})

const columns = computed(() => {
  if (props.result?.columns) return props.result.columns
  const result = props.output?.result as Record<string, unknown> | undefined
  if (result?.columns) return result.columns as string[]
  return []
})

const rows = computed(() => {
  if (props.result?.rows) return props.result.rows
  const result = props.output?.result as Record<string, unknown> | undefined
  if (result?.rows) return result.rows as unknown[][]
  return []
})

const rowCount = computed(() => rows.value.length)

const previewRows = computed(() => rows.value.slice(0, 3))

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'number') {
    return val.toLocaleString()
  }
  return String(val)
}
</script>

<style scoped>
.execution-detail {
  min-width: 400px;
}

.detail-header {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #374151;
  margin-bottom: 12px;
}

.detail-content {
  font-size: 14px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.info-label {
  color: #6b7280;
  font-size: 13px;
}

.info-value {
  color: #1f2937;
  font-weight: 500;
}

.columns-preview {
  margin-bottom: 12px;
}

.columns-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.more-cols {
  color: #9ca3af;
  font-size: 12px;
}

.rows-preview {
  margin-top: 12px;
}

.preview-table {
  margin-top: 8px;
  overflow-x: auto;
}

.preview-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.preview-table th,
.preview-table td {
  padding: 6px 10px;
  text-align: left;
  border: 1px solid #e5e7eb;
}

.preview-table th {
  background: #f9fafb;
  color: #6b7280;
  font-weight: 500;
}

.preview-table td {
  color: #1f2937;
}

.error-info {
  margin-top: 8px;
}

.error-message {
  font-family: monospace;
  font-size: 12px;
  margin-top: 8px;
  word-break: break-all;
}
</style>
