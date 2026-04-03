<template>
  <div class="query-view h-full flex">
    <!-- 左侧：导航 + 历史记录 -->
    <QuerySidebar
      :history="store.history"
      :active-id="activeHistoryId"
      @newChat="handleNewChat"
      @selectHistory="handleSelectHistory"
      @toggleFavorite="handleToggleFavorite"
      @removeHistory="handleRemoveHistory"
      @clearHistory="handleClearHistory"
    />

    <!-- 右侧：消息流 + 输入框 -->
    <div class="flex-1 flex flex-col overflow-hidden bg-gray-50">
      <!-- 消息流区域 -->
      <div class="flex-1 overflow-auto" ref="messageContainer">
        <!-- 空状态 -->
        <div v-if="store.conversations.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400">
          <el-icon :size="64"><Document /></el-icon>
          <p class="mt-4 text-lg">开始您的智能问数之旅</p>
          <p class="mt-2 text-sm">输入自然语言问题，自动生成 SQL 并查询数据</p>
          <div class="mt-6 flex gap-2 flex-wrap justify-center max-w-lg">
            <el-tag
              v-for="example in examples"
              :key="example"
              size="large"
              class="cursor-pointer hover:bg-blue-100 transition-all"
              @click="handleExampleClick(example)"
            >
              {{ example }}
            </el-tag>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-else class="max-w-4xl mx-auto py-6 px-4 space-y-6">
          <MessageCard
            v-for="msg in store.conversations"
            :key="msg.id"
            :message="msg"
            @retry="handleRetry"
          />
        </div>

        <!-- 加载指示器 -->
        <div v-if="store.isExecuting && store.conversations.length > 0" class="max-w-4xl mx-auto pb-6 px-4">
          <div class="bg-white rounded-lg shadow-sm p-4 flex items-center gap-3">
            <el-icon class="is-loading text-2xl text-blue-500"><Loading /></el-icon>
            <div>
              <p class="text-sm font-medium text-gray-700">正在处理您的查询...</p>
              <div class="mt-2 flex gap-2">
                <el-tag v-for="step in store.orderedSteps" :key="step.id" :type="getStepType(step.status)" size="small">
                  {{ step.label }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入框 -->
      <div class="border-t bg-white p-4">
        <div class="max-w-4xl mx-auto">
          <div class="flex gap-3 items-end">
            <div class="flex-1 relative">
              <el-input
                v-model="question"
                type="textarea"
                :rows="1"
                :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="输入您的问题，例如：查询过去30天按地区的订单金额"
                size="large"
                :disabled="store.isExecuting"
                resize="none"
                @keyup.enter.exact="handleSubmit"
              />
            </div>
            <el-button
              type="primary"
              size="large"
              :loading="store.isExecuting"
              :disabled="!question.trim()"
              @click="handleSubmit"
            >
              <el-icon v-if="!store.isExecuting"><Promotion /></el-icon>
              {{ store.isExecuting ? '查询中' : '发送' }}
            </el-button>
            <el-button
              v-if="store.isExecuting"
              size="large"
              @click="store.cancelQuery"
            >
              取消
            </el-button>
          </div>
          <div class="mt-2 text-xs text-gray-400 text-center">
            按 Enter 发送，Shift + Enter 换行
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { Document, Loading, Promotion } from '@element-plus/icons-vue'
import { useQueryStore } from '@/stores/queryStore'
import QuerySidebar from './components/QuerySidebar.vue'
import MessageCard from './components/MessageCard.vue'
import type { QueryHistory, StepState } from '@/types'

const store = useQueryStore()
const question = ref('')
const activeHistoryId = ref<number | undefined>()
const messageContainer = ref<HTMLElement | null>(null)

const examples = [
  '查询最近30天的订单金额',
  '按月统计销售额',
  '查询各地区的订单数量',
  '过去7天按地区的GMV',
  '各会员等级的消费金额分布',
]

function getStepType(status: StepState['status']): '' | 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'running': return 'info'
    case 'completed': return 'success'
    case 'error': return 'danger'
    default: return ''
  }
}

async function handleSubmit() {
  const q = question.value.trim()
  if (!q || store.isExecuting) return

  question.value = ''
  activeHistoryId.value = undefined

  try {
    await store.executeQuery(q)
    scrollToBottom()
  } catch (e) {
    console.error('Query failed:', e)
  }
}

function handleExampleClick(example: string) {
  question.value = example
  handleSubmit()
}

function handleNewChat() {
  store.clearConversations()
  activeHistoryId.value = undefined
  question.value = ''
}

function handleSelectHistory(item: QueryHistory) {
  activeHistoryId.value = item.id
  store.loadHistoryResult(item)
}

async function handleToggleFavorite(id: number) {
  await store.toggleFavorite(id)
}

async function handleRemoveHistory(id: number) {
  await store.removeFromHistory(id)
}

async function handleClearHistory() {
  await store.clearAllHistory()
}

function handleRetry() {
  if (store.currentQuestion) {
    store.executeQuery(store.currentQuestion)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight
    }
  })
}

// 滚动到底部当新消息添加
watch(() => store.conversations.length, () => {
  scrollToBottom()
})
</script>

<style scoped>
.query-view {
  background: #f5f7fa;
}

.el-textarea__inner {
  font-size: 15px;
}
</style>