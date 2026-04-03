<template>
  <div class="datasource-chat">
    <el-card class="chat-container">
      <template #header>
        <div class="flex items-center justify-between">
          <span>针对该数据源的问数对话</span>
          <el-button size="small" @click="clearChat">清空对话</el-button>
        </div>
      </template>

      <!-- 对话区域 -->
      <div ref="chatRef" class="chat-messages overflow-auto" style="height: 400px;">
        <div v-if="messages.length === 0" class="empty-chat">
          <el-icon :size="48" class="text-gray-300"><ChatLineRound /></el-icon>
          <p class="text-gray-400 mt-2">开始针对该数据源的问数对话</p>
        </div>

        <div v-for="msg in messages" :key="msg.id" class="message" :class="msg.role">
          <div class="message-content">
            <div v-if="msg.role === 'user'" class="user-message">
              {{ msg.content }}
            </div>
            <div v-else class="assistant-message">
              <div v-if="msg.sql" class="sql-block">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs text-gray-500">生成的 SQL</span>
                  <el-button text type="primary" size="small" @click="copySql(msg.sql)">
                    复制
                  </el-button>
                </div>
                <pre class="text-xs">{{ msg.sql }}</pre>
              </div>
              <div v-if="msg.error" class="error-text">
                <el-icon><WarningFilled /></el-icon>
                {{ msg.error }}
              </div>
              <div v-if="msg.columns && msg.rows" class="result-preview">
                <span class="text-xs text-gray-500">
                  返回 {{ msg.rows.length }} 行数据
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="assistant-message">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span class="ml-2">正在处理...</span>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="chat-input mt-4 flex gap-2">
        <el-input
          v-model="inputText"
          placeholder="输入自然语言问题..."
          @keyup.enter="handleSubmit"
          :disabled="loading"
        />
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          发送
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatLineRound, WarningFilled, Loading } from '@element-plus/icons-vue'
import { useQueryStore } from '@/stores/queryStore'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sql?: string
  columns?: string[]
  rows?: unknown[][]
  error?: string
}

const props = defineProps<{
  datasourceId: number
}>()

const store = useQueryStore()
const chatRef = ref<HTMLElement | null>(null)
const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
let messageId = 0

async function handleSubmit() {
  const question = inputText.value.trim()
  if (!question || loading.value) return

  inputText.value = ''
  messages.value.push({
    id: ++messageId,
    role: 'user',
    content: question,
  })

  loading.value = true
  scrollToBottom()

  try {
    // 使用指定数据源执行查询
    const result = await store.executeQueryWithDatasource(question, props.datasourceId)

    messages.value.push({
      id: ++messageId,
      role: 'assistant',
      content: '',
      sql: result.sql || undefined,
      columns: result.columns,
      rows: result.rows,
      error: result.executionError || undefined,
    })
  } catch (e: unknown) {
    messages.value.push({
      id: ++messageId,
      role: 'assistant',
      content: '',
      error: (e as Error).message || '查询失败',
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

function copySql(sql: string) {
  navigator.clipboard.writeText(sql)
  ElMessage.success('已复制到剪贴板')
}

function clearChat() {
  messages.value = []
}
</script>

<style scoped>
.chat-messages {
  scroll-behavior: smooth;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.message {
  margin-bottom: 16px;
}

.message.user {
  text-align: right;
}

.user-message {
  display: inline-block;
  background: #3b82f6;
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 80%;
  text-align: left;
}

.assistant-message {
  background: #f3f4f6;
  padding: 12px;
  border-radius: 8px;
  max-width: 100%;
}

.sql-block {
  background: #1e293b;
  color: #e2e8f0;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.sql-block pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.error-text {
  color: #ef4444;
  display: flex;
  align-items: center;
  gap: 4px;
}

.result-preview {
  color: #10b981;
  font-size: 12px;
}
</style>