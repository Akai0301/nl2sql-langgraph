<template>
  <div class="history-panel h-full flex flex-col">
    <div class="p-4 border-b">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-medium text-gray-700">查询历史</h3>
        <el-button
          v-if="store.history.length > 0"
          text
          size="small"
          type="danger"
          @click="handleClearAll"
        >
          清空
        </el-button>
      </div>

      <!-- Search and filter -->
      <div class="space-y-2">
        <el-input
          v-model="searchText"
          placeholder="搜索问题或SQL..."
          size="small"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <div class="flex gap-2">
          <el-checkbox v-model="favoriteOnly" @change="handleFilter">
            仅收藏
          </el-checkbox>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            size="small"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="handleFilter"
          />
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto">
      <div v-if="store.historyLoading" class="p-4 text-center text-gray-400 text-sm">
        加载中...
      </div>
      <div v-else-if="store.history.length === 0" class="p-4 text-center text-gray-400 text-sm">
        暂无查询历史
      </div>

      <div v-else>
        <div
          v-for="item in store.history"
          :key="item.id"
          class="p-3 border-b hover:bg-gray-50 cursor-pointer transition-colors"
          @click="showHistory(item)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <p class="text-sm text-gray-800 truncate">{{ item.question }}</p>
              <p class="text-xs text-gray-400 mt-1">{{ formatTime(item.created_at) }}</p>
            </div>
            <div class="flex items-center gap-1">
              <el-button
                text
                size="small"
                :class="{ 'text-yellow-500': item.is_favorite }"
                @click.stop="store.toggleFavorite(item.id)"
              >
                <el-icon>
                  <StarFilled v-if="item.is_favorite" />
                  <Star v-else />
                </el-icon>
              </el-button>
              <el-button text size="small" @click.stop="store.removeFromHistory(item.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>

          <!-- Quick result preview -->
          <div v-if="item.rows?.length" class="mt-2 text-xs text-gray-500">
            <span class="bg-gray-100 px-2 py-0.5 rounded">
              {{ item.rows.length }} 行
            </span>
            <span v-if="item.execution_error" class="ml-2 text-red-500">
              执行出错
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="store.historyTotal > store.historyPageSize" class="p-2 border-t">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="store.historyPageSize"
        :total="store.historyTotal"
        layout="prev, pager, next"
        small
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Star, StarFilled, Delete, Search } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useQueryStore } from '@/stores/queryStore'
import type { QueryHistory } from '@/types'

const store = useQueryStore()

const searchText = ref('')
const favoriteOnly = ref(false)
const dateRange = ref<[string, string] | null>(null)
const currentPage = ref(1)

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`

  return date.toLocaleDateString('zh-CN')
}

function showHistory(item: QueryHistory) {
  store.loadHistoryResult(item)
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function handleSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadHistory()
  }, 300)
}

function handleFilter() {
  currentPage.value = 1
  loadHistory()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadHistory()
}

function loadHistory() {
  store.loadHistory({
    page: currentPage.value,
    search: searchText.value || undefined,
    is_favorite: favoriteOnly.value ? true : undefined,
    start_date: dateRange.value?.[0],
    end_date: dateRange.value?.[1],
  })
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有历史记录吗？', '确认清空', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.clearAllHistory()
  } catch {
    // User cancelled
  }
}

onMounted(() => {
  // History is already loaded in store initialization
  // Only reload if needed (e.g., after navigation)
})
</script>

<style scoped>
.history-panel {
  background: #fff;
}
</style>
