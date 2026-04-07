<template>
  <div class="message-card" :class="message.role">
    <!-- User message -->
    <div v-if="message.role === 'user'" class="user-message">
      <div class="avatar user-avatar">
        <el-icon><User /></el-icon>
      </div>
      <div class="message-content">
        <div class="message-text">{{ message.content }}</div>
        <div class="message-time">{{ formatTime(message.timestamp) }}</div>
      </div>
    </div>

    <!-- Assistant message -->
    <div v-else class="assistant-message">
      <div class="avatar assistant-avatar">
        <el-icon><Monitor /></el-icon>
      </div>
      <div class="message-content">
        <!-- Steps progress -->
        <StepProgressBar
          v-if="message.steps && message.steps.length > 0"
          :steps="message.steps"
          :result="message.result"
          @edit-sql="handleEditSql"
        />

        <!-- Error -->
        <el-alert
          v-if="message.error"
          type="error"
          :closable="false"
          class="mb-4"
        >
          {{ message.error }}
        </el-alert>

        <!-- Result -->
        <div v-if="message.result && !message.error" class="result-section">
          <!-- SQL Display -->
          <div v-if="message.result.sql" class="sql-section">
            <div class="result-header">
              <span>生成的 SQL</span>
              <el-button text size="small" @click="copySql">
                <el-icon><CopyDocument /></el-icon>
                复制
              </el-button>
            </div>
            <pre class="sql-code">{{ message.result.sql }}</pre>
          </div>

          <!-- Data Table -->
          <div v-if="message.result.rows && message.result.rows.length > 0" class="data-section">
            <el-tabs v-model="activeTab" type="border-card">
              <el-tab-pane label="数据表格" name="table">
                <ResultTable
                  :columns="message.result.columns"
                  :rows="message.result.rows"
                />
              </el-tab-pane>
              <el-tab-pane label="数据可视化" name="chart">
                <ChartPanel
                  :columns="message.result.columns"
                  :rows="message.result.rows"
                />
              </el-tab-pane>
            </el-tabs>
          </div>

          <!-- Empty result -->
          <div v-else-if="message.result.columns && message.result.rows?.length === 0" class="empty-result">
            <el-empty description="查询结果为空" :image-size="60" />
          </div>
        </div>

        <!-- Footer with retry button and time -->
        <div v-if="message.result || message.error" class="message-footer">
          <el-button
            type="primary"
            size="small"
            :icon="RefreshRight"
            @click="handleRetry"
            :loading="isRetrying"
          >
            重新回答
          </el-button>
          <!-- Stats display -->
          <div class="message-stats">
            <span v-if="totalDuration" class="stat-item">
              <el-icon><Timer /></el-icon>
              {{ totalDuration }}
            </span>
            <span v-if="tokenCount" class="stat-item">
              <el-icon><Coin /></el-icon>
              {{ tokenCount }} tokens
            </span>
          </div>
          <div class="message-time">{{ formatTime(message.timestamp) }}</div>
        </div>
        <div v-else class="message-time">{{ formatTime(message.timestamp) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { User, Monitor, CopyDocument, RefreshRight, Timer, Coin } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { ConversationMessage } from '@/types'
import StepProgressBar from './StepProgressBar.vue'
import ResultTable from './ResultTable.vue'
import ChartPanel from './ChartPanel.vue'

const props = defineProps<{
  message: ConversationMessage
}>()

const emit = defineEmits<{
  editSql: [sql: string]
  retry: [question: string]
}>()

const activeTab = ref('table')
const isRetrying = ref(false)

// Format total duration
const totalDuration = computed(() => {
  const ms = props.message.result?.totalDurationMs
  if (!ms) return null
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.round((ms % 60000) / 1000)
  return `${minutes}m${seconds}s`
})

// Format token count
const tokenCount = computed(() => {
  const usage = props.message.result?.tokenUsage
  if (!usage || usage.total_tokens === 0) return null
  return usage.total_tokens
})

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function copySql() {
  if (props.message.result?.sql) {
    navigator.clipboard.writeText(props.message.result.sql)
    ElMessage.success('SQL 已复制到剪贴板')
  }
}

function handleEditSql(sql: string) {
  emit('editSql', sql)
}

function handleRetry() {
  // Find the user question from the conversation
  // The question is stored in the result or we need to get it from parent
  if (props.message.result?.question) {
    isRetrying.value = true
    emit('retry', props.message.result.question)
    // Reset loading state after a delay (parent will handle the actual retry)
    setTimeout(() => {
      isRetrying.value = false
    }, 1000)
  }
}
</script>

<style scoped>
.message-card {
  margin-bottom: 24px;
}

.user-message,
.assistant-message {
  display: flex;
  gap: 12px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
}

.user-avatar {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
}

.assistant-avatar {
  background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
  color: white;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.user-message .message-text {
  background: #eff6ff;
  color: #1e40af;
}

.assistant-message .message-content {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
}

.message-time {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 6px;
  text-align: right;
}

.result-section {
  margin-top: 16px;
}

.sql-section {
  margin-bottom: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.sql-code {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px 16px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  overflow-x: auto;
  margin: 0;
}

.data-section {
  margin-top: 12px;
}

.empty-result {
  padding: 24px;
}

.message-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.message-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  margin-left: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.stat-item .el-icon {
  font-size: 14px;
}

.message-footer .message-time {
  margin-top: 0;
}
</style>
