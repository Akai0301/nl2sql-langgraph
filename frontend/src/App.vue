<template>
  <div class="app-container h-screen flex">
    <!-- Sidebar -->
    <Sidebar
      :history="store.history"
      :active-id="activeHistoryId"
      @new-chat="handleNewChat"
      @select-history="handleSelectHistory"
      @toggle-favorite="store.toggleFavorite"
      @remove-history="store.removeFromHistory"
      @clear-history="handleClearHistory"
    />

    <!-- Main Content -->
    <div class="main-content flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="bg-white border-b px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <el-icon :size="24" class="text-blue-500">
              <DataAnalysis />
            </el-icon>
            <h1 class="text-lg font-semibold text-gray-800">NL2SQL 智能问数</h1>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-sm text-gray-400">
              基于 LangGraph 的自然语言查询
            </div>
            <!-- User Avatar Placeholder (SSO Ready) -->
            <el-tooltip content="企业级登录（即将推出）" placement="bottom">
              <div class="user-avatar-placeholder">
                <el-icon :size="20"><User /></el-icon>
              </div>
            </el-tooltip>
          </div>
        </div>
      </header>

      <!-- Conversation Area -->
      <div ref="conversationRef" class="conversation-area flex-1 overflow-auto bg-gray-50">
        <!-- Empty State with Examples -->
        <div v-if="store.conversations.length === 0" class="empty-state">
          <div class="empty-icon">
            <el-icon :size="64"><ChatLineRound /></el-icon>
          </div>
          <h2 class="empty-title">开始智能问数</h2>
          <p class="empty-desc">输入自然语言问题，系统将自动分析、检索并生成 SQL 查询</p>
          <ExampleQuestions @select="handleExampleSelect" />
        </div>

        <!-- Conversation Messages -->
        <div v-else class="messages-container">
          <MessageCard
            v-for="message in store.conversations"
            :key="message.id"
            :message="message"
            @edit-sql="handleEditSql"
            @retry="handleRetry"
          />
        </div>
      </div>

      <!-- Input Box -->
      <InputBox
        :is-executing="store.isExecuting"
        @submit="handleSubmit"
        @stop="handleStop"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { DataAnalysis, ChatLineRound, User } from '@element-plus/icons-vue'
import { useQueryStore } from '@/stores/queryStore'
import type { QueryHistory } from '@/types'
import Sidebar from '@/views/components/Sidebar.vue'
import ExampleQuestions from '@/views/components/ExampleQuestions.vue'
import MessageCard from '@/views/components/MessageCard.vue'
import InputBox from '@/views/components/InputBox.vue'

const store = useQueryStore()
const conversationRef = ref<HTMLElement | null>(null)
const activeHistoryId = ref<number | undefined>()

// Auto-scroll to bottom when new messages arrive
watch(
  () => store.conversations.length,
  () => {
    nextTick(() => {
      if (conversationRef.value) {
        conversationRef.value.scrollTop = conversationRef.value.scrollHeight
      }
    })
  }
)

function handleSubmit(question: string) {
  activeHistoryId.value = undefined
  store.executeQuery(question)
}

function handleStop() {
  store.cancelQuery()
}

function handleExampleSelect(question: string) {
  store.executeQuery(question)
}

function handleNewChat() {
  store.clearConversations()
  activeHistoryId.value = undefined
}

function handleSelectHistory(item: QueryHistory) {
  activeHistoryId.value = item.id
  // Load history result without re-executing
  if (item.question) {
    store.clearConversations()
    store.loadHistoryResult(item)
  }
}

async function handleClearHistory() {
  try {
    await ElMessageBox.confirm('确定要清空所有历史记录吗？', '确认', {
      type: 'warning',
    })
    store.clearAllHistory()
  } catch {
    // Cancelled
  }
}

function handleEditSql(sql: string) {
  // Add a new message with edited SQL
  store.executeEditedSql(sql)
}

function handleRetry(question: string) {
  // Re-execute the question with current session_id
  store.executeQuery(question)
}
</script>

<style>
/* Global styles */
* {
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}

.app-container {
  background: #f5f7fa;
}

.main-content {
  background: white;
}

.conversation-area {
  scroll-behavior: smooth;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 40px 20px;
}

.empty-icon {
  color: #d1d5db;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 32px;
  text-align: center;
}

.messages-container {
  padding: 20px;
}

.user-avatar-placeholder {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f3f4f6;
  border: 2px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s;
}

.user-avatar-placeholder:hover {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #3b82f6;
}
</style>
