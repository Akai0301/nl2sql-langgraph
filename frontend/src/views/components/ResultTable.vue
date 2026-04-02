<template>
  <div class="result-table bg-white rounded-lg shadow-sm overflow-hidden">
    <div class="flex items-center justify-between p-3 border-b bg-gray-50">
      <div class="flex items-center gap-2">
        <el-icon><Grid /></el-icon>
        <span class="text-sm font-medium text-gray-700">
          查询结果 ({{ rows.length }} 行)
        </span>
      </div>
      <el-button text size="small" @click="exportCsv">
        <el-icon><Download /></el-icon>
        导出 CSV
      </el-button>
    </div>

    <el-table
      :data="tableData"
      border
      stripe
      max-height="400"
      style="width: 100%"
    >
      <el-table-column
        v-for="col in columns"
        :key="col"
        :prop="col"
        :label="col"
        min-width="120"
        show-overflow-tooltip
      />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Grid, Download } from '@element-plus/icons-vue'
import { useQueryStore } from '@/stores/queryStore'

const props = defineProps<{
  columns?: string[]
  rows?: unknown[][]
}>()

const store = useQueryStore()

const columns = computed(() => props.columns || store.result?.columns || [])

const rows = computed(() => props.rows || store.result?.rows || [])

const tableData = computed(() => {
  const cols = columns.value
  const data = rows.value

  return data.map((row) => {
    const obj: Record<string, unknown> = {}
    cols.forEach((col, index) => {
      obj[col] = row[index]
    })
    return obj
  })
})

function exportCsv() {
  const cols = columns.value
  const data = rows.value

  if (cols.length === 0 || data.length === 0) return

  // Build CSV content
  const csvLines = [
    cols.join(','),
    ...data.map(row =>
      row.map(cell => {
        const str = String(cell ?? '')
        // Escape quotes and wrap in quotes if contains comma or newline
        if (str.includes(',') || str.includes('\n') || str.includes('"')) {
          return `"${str.replace(/"/g, '""')}"`
        }
        return str
      }).join(',')
    ),
  ]

  const csvContent = csvLines.join('\n')
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `query-result-${Date.now()}.csv`
  link.click()

  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.result-table {
  width: 100%;
}
</style>
