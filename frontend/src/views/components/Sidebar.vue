<template>
  <div class="sidebar h-full flex flex-col bg-gray-50 border-r">
    <!-- Header -->
    <div class="p-4 border-b bg-white">
      <button
        class="w-full btn-new-chat"
        @click="$emit('newChat')"
      >
        <el-icon class="mr-2"><Plus /></el-icon>
        新建对话
      </button>
    </div>

    <!-- Search -->
    <div class="p-3 border-b">
      <el-input
        v-model="searchQuery"
        placeholder="搜索历史记录..."
        :prefix-icon="Search"
        size="small"
        clearable
      />
    </div>

    <!-- Favorites -->
    <div v-if="favoriteItems.length > 0" class="p-3 border-b">
      <div class="text-xs font-medium text-gray-500 mb-2 flex items-center">
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
          <span class="truncate">{{ item.question }}</span>
          <el-icon class="star-icon" @click.stop="$emit('toggleFavorite', item.id)">
            <StarFilled />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- History List -->
    <div class="flex-1 overflow-auto p-3">
      <div class="text-xs font-medium text-gray-500 mb-2">历史记录</div>
      <div v-if="filteredHistory.length === 0" class="text-center text-gray-400 py-8 text-sm">
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
          <el-icon class="mr-2 text-gray-400"><ChatDotRound /></el-icon>
          <span class="flex-1 truncate">{{ item.question }}</span>
          <div class="history-actions">
            <el-icon
              v-if="item.is_favorite"
              class="text-yellow-500"
              @click.stop="$emit('toggleFavorite', item.id)"
            >
              <StarFilled />
            </el-icon>
            <el-icon
              v-else
              class="text-gray-300 hover:text-yellow-500"
              @click.stop="$emit('toggleFavorite', item.id)"
            >
              <Star />
            </el-icon>
            <el-icon
              class="text-gray-300 hover:text-red-500"
              @click.stop="$emit('removeHistory', item.id)"
            >
              <Delete />
            </el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="p-3 border-t text-center">
      <el-button text size="small" @click="$emit('clearHistory')">
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
.sidebar {
  width: 260px;
  min-width: 260px;
}

.btn-new-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  color: #374151;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-new-chat:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.15s;
}

.history-item:hover {
  background: #e5e7eb;
}

.history-item.active {
  background: #dbeafe;
  color: #1d4ed8;
}

.history-item.favorite {
  background: #fef9c3;
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
</style>
