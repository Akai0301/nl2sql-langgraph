<template>
  <div class="query-sidebar h-full flex flex-col bg-gray-900 text-white">
    <!-- 新建对话 -->
    <div class="p-3 border-b border-gray-700">
      <button class="w-full btn-new-chat" @click="$emit('newChat')">
        <el-icon class="mr-2"><Plus /></el-icon>
        新建对话
      </button>
    </div>

    <!-- 搜索 -->
    <div class="p-3 border-b border-gray-700">
      <el-input
        v-model="searchQuery"
        placeholder="搜索历史..."
        :prefix-icon="Search"
        size="small"
        clearable
        class="dark-input"
      />
    </div>

    <!-- 收藏 -->
    <div v-if="favoriteItems.length > 0" class="p-3 border-b border-gray-700">
      <div class="text-xs font-medium text-gray-400 mb-2 flex items-center">
        <el-icon class="mr-1"><Star /></el-icon>
        收藏
      </div>
      <div class="space-y-1">
        <div
          v-for="item in favoriteItems"
          :key="item.id"
          class="history-item favorite"
          @click="$emit('selectHistory', item)"
        >
          <span class="truncate text-sm">{{ item.question }}</span>
          <el-icon class="star-icon text-yellow-400" @click.stop="$emit('toggleFavorite', item.id)">
            <StarFilled />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="flex-1 overflow-auto p-3">
      <div class="text-xs font-medium text-gray-400 mb-2">历史记录</div>
      <div v-if="filteredHistory.length === 0" class="text-center text-gray-500 py-8 text-sm">
        暂无历史记录
      </div>
      <div v-else class="space-y-1">
        <div
          v-for="item in filteredHistory"
          :key="item.id"
          class="history-item"
          :class="{ active: item.id === activeId }"
          @click="$emit('selectHistory', item)"
        >
          <el-icon class="mr-2 text-gray-500"><ChatDotRound /></el-icon>
          <span class="flex-1 truncate text-sm">{{ item.question }}</span>
          <div class="history-actions">
            <el-icon
              v-if="item.is_favorite"
              class="text-yellow-400"
              @click.stop="$emit('toggleFavorite', item.id)"
            >
              <StarFilled />
            </el-icon>
            <el-icon
              v-else
              class="text-gray-600 hover:text-yellow-400"
              @click.stop="$emit('toggleFavorite', item.id)"
            >
              <Star />
            </el-icon>
            <el-icon
              class="text-gray-600 hover:text-red-400"
              @click.stop="$emit('removeHistory', item.id)"
            >
              <Delete />
            </el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <div class="p-3 border-t border-gray-700 text-center">
      <el-button text size="small" class="text-gray-400 hover:text-white" @click="$emit('clearHistory')">
        清空历史
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Plus, Search, Star, StarFilled, ChatDotRound, Delete } from '@element-plus/icons-vue'
import type { QueryHistory } from '@/types'

const props = defineProps<{
  history: QueryHistory[]
  activeId?: number
}>()

defineEmits<{
  newChat: []
  selectHistory: [item: QueryHistory]
  toggleFavorite: [id: number]
  removeHistory: [id: number]
  clearHistory: []
}>()

const searchQuery = ref('')

const favoriteItems = computed(() =>
  props.history.filter(h => h.is_favorite)
)

const filteredHistory = computed(() => {
  const items = props.history.filter(h => !h.is_favorite)
  if (!searchQuery.value) return items
  return items.filter(h =>
    h.question.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})
</script>

<style scoped>
.query-sidebar {
  width: 260px;
  min-width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.btn-new-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  border: 1px dashed #4b5563;
  border-radius: 8px;
  color: #d1d5db;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.btn-new-chat:hover {
  border-color: #3b82f6;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.1);
}

.history-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  color: #d1d5db;
  cursor: pointer;
  transition: all 0.15s;
}

.history-item:hover {
  background: #374151;
}

.history-item.active {
  background: #3b82f6;
  color: white;
}

.history-item.favorite {
  background: rgba(250, 204, 21, 0.1);
}

.history-actions {
  display: none;
  align-items: center;
  gap: 4px;
}

.history-item:hover .history-actions {
  display: flex;
}

.history-actions .el-icon {
  font-size: 14px;
  cursor: pointer;
}

.dark-input .el-input__wrapper {
  background: #374151 !important;
  border-color: #4b5563 !important;
  box-shadow: none !important;
}

.dark-input .el-input__inner {
  color: #d1d5db !important;
}

.dark-input .el-input__inner::placeholder {
  color: #6b7280 !important;
}
</style>