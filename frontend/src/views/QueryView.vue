<template>
  <div class="query-view h-full flex">
    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Query Input -->
      <QueryInput class="p-4 bg-white border-b" />

      <!-- Flow Graph -->
      <div class="h-64 bg-white border-b">
        <FlowGraph />
      </div>

      <!-- Results Area -->
      <div class="flex-1 overflow-auto p-4">
        <div v-if="store.isExecuting" class="flex items-center justify-center h-full">
          <el-icon class="is-loading text-4xl text-blue-500">
            <Loading />
          </el-icon>
          <span class="ml-3 text-gray-500">正在处理您的查询...</span>
        </div>

        <div v-else-if="store.hasError" class="flex items-center justify-center h-full">
          <el-result icon="error" :title="store.error || '查询失败'">
            <template #extra>
              <el-button type="primary" @click="retryQuery" :loading="store.isExecuting">
                <el-icon><RefreshRight /></el-icon>
                重新回答
              </el-button>
            </template>
          </el-result>
        </div>

        <div v-else-if="store.hasResult" class="space-y-4">
          <!-- SQL Display -->
          <div v-if="store.result?.sql" class="bg-white rounded-lg shadow-sm p-4">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm font-medium text-gray-700">生成的 SQL</h3>
              <el-button text type="primary" @click="copySql">
                <el-icon><CopyDocument /></el-icon>
                复制
              </el-button>
            </div>
            <pre class="code-block text-sm overflow-x-auto">{{ store.result.sql }}</pre>
          </div>

          <!-- Error Info -->
          <div v-if="store.result?.executionError" class="bg-red-50 rounded-lg p-4">
            <div class="flex items-center text-red-600">
              <el-icon class="mr-2"><WarningFilled /></el-icon>
              <span>{{ store.result.executionError }}</span>
            </div>
          </div>

          <!-- Results Tabs -->
          <el-tabs v-if="store.result?.rows?.length" v-model="activeTab">
            <el-tab-pane label="数据表格" name="table">
              <ResultTable />
            </el-tab-pane>
            <el-tab-pane label="数据可视化" name="chart">
              <ChartPanel />
            </el-tab-pane>
          </el-tabs>

          <!-- Retry Button Footer -->
          <div class="result-footer">
            <el-button type="primary" @click="retryQuery" :loading="store.isExecuting">
              <el-icon><RefreshRight /></el-icon>
              重新回答
            </el-button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="flex flex-col items-center justify-center h-full text-gray-400">
          <el-icon :size="64"><Document /></el-icon>
          <p class="mt-4 text-lg">输入问题开始查询</p>
          <p class="mt-2 text-sm">支持自然语言描述的数据查询需求</p>
        </div>
      </div>
    </div>

    <!-- History Panel -->
    <HistoryPanel class="w-80 bg-white border-l" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, CopyDocument, WarningFilled, Document, RefreshRight } from '@element-plus/icons-vue'
import { useQueryStore } from '@/stores/queryStore'
import QueryInput from './components/QueryInput.vue'
import FlowGraph from './components/FlowGraph.vue'
import ResultTable from './components/ResultTable.vue'
import ChartPanel from './components/ChartPanel.vue'
import HistoryPanel from './components/HistoryPanel.vue'

const store = useQueryStore()
const activeTab = ref('table')

function copySql() {
  if (store.result?.sql) {
    navigator.clipboard.writeText(store.result.sql)
    ElMessage.success('SQL 已复制到剪贴板')
  }
}

function retryQuery() {
  if (store.currentQuestion) {
    store.executeQuery(store.currentQuestion)
  }
}
</script>

<style scoped>
.query-view {
  background: #f5f7fa;
}

.result-footer {
  display: flex;
  justify-content: flex-start;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid #e5e7eb;
}
</style>
