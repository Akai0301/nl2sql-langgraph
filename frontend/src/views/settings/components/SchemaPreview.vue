<template>
  <div class="schema-preview">
    <!-- 学习状态卡片 -->
    <el-card v-if="!schemaCache && !loading" class="mb-4">
      <div class="text-center py-8">
        <el-icon :size="48" color="#909399"><Document /></el-icon>
        <p class="mt-4 text-gray-500">尚未进行 Schema 学习</p>
        <p class="text-sm text-gray-400">点击下方按钮开始学习，自动提取表结构和语义描述</p>
        <el-button type="primary" class="mt-4" :loading="learning" @click="handleLearn">
          <el-icon><MagicStick /></el-icon>
          开始学习
        </el-button>
      </div>
    </el-card>

    <!-- 加载中 -->
    <el-card v-if="loading" class="mb-4">
      <div class="text-center py-8">
        <el-icon class="is-loading" :size="48" color="#409EFF"><Loading /></el-icon>
        <p class="mt-4 text-gray-500">正在加载 Schema...</p>
      </div>
    </el-card>

    <!-- Schema 概览 -->
    <el-card v-if="schemaCache" class="mb-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>Schema 概览</span>
          <div class="flex gap-2">
            <el-button size="small" :loading="learning" @click="handleLearn">
              <el-icon><Refresh /></el-icon>
              更新学习
            </el-button>
            <el-button size="small" type="danger" :loading="clearing" @click="handleClearAndRelearn">
              <el-icon><Delete /></el-icon>
              清空并重新学习
            </el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="表数量" :value="schemaCache.table_count">
            <template #suffix>张</template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="字段数量" :value="schemaCache.field_count">
            <template #suffix>个</template>
          </el-statistic>
        </el-col>
        <el-col :span="12">
          <div class="text-sm text-gray-500">学习时间</div>
          <div class="text-lg font-medium">{{ schemaCache.learned_at || '-' }}</div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 表列表 -->
    <el-card v-if="schemaCache">
      <template #header>
        <div class="flex justify-between items-center">
          <span>表结构</span>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索表名或字段"
            clearable
            style="width: 200px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </template>

      <el-table
        :data="filteredTables"
        v-loading="tablesLoading"
        row-key="name"
        @row-click="handleRowClick"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="p-4 bg-gray-50">
              <div class="text-sm font-medium mb-2">字段列表</div>
              <el-table :data="row.fields" size="small" border>
                <el-table-column prop="name" label="字段名" width="150" />
                <el-table-column prop="type" label="类型" width="120" />
                <el-table-column label="主键" width="60">
                  <template #default="{ row: field }">
                    <el-tag v-if="field.primary_key" type="success" size="small">PK</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="分类" width="100">
                  <template #default="{ row: field }">
                    <el-tag v-if="field.category" :type="getCategoryType(field.category)" size="small">
                      {{ field.category }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="维度/度量" width="100">
                  <template #default="{ row: field }">
                    <el-tag v-if="field.dim_or_meas" :type="field.dim_or_meas === 'Measure' ? 'warning' : 'info'" size="small">
                      {{ field.dim_or_meas === 'Measure' ? '度量' : '维度' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="comment" label="注释">
                  <template #default="{ row: field }">
                    <span class="text-gray-600">{{ field.comment || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="示例值" width="200">
                  <template #default="{ row: field }">
                    <span v-if="field.examples?.length" class="text-xs text-gray-500">
                      {{ field.examples.slice(0, 3).join(', ') }}
                    </span>
                    <span v-else class="text-gray-300">-</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="表名" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTableTypeType(row.table_type)" size="small">
              {{ getTableTypeLabel(row.table_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="注释">
          <template #default="{ row }">
            <span class="text-gray-600">{{ row.comment || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="field_count" label="字段数" width="80" />
      </el-table>
    </el-card>

    <!-- 清空确认弹窗 -->
    <el-dialog
      v-model="showClearConfirm"
      title="确认清空"
      width="400px"
    >
      <div class="text-center py-4">
        <el-icon :size="48" color="#E6A23C"><Warning /></el-icon>
        <p class="mt-4">确定要清空当前 Schema 学习内容并重新学习吗？</p>
        <p class="text-sm text-gray-400 mt-2">此操作将删除所有已学习的表结构、字段分类和语义描述</p>
      </div>
      <template #footer>
        <el-button @click="showClearConfirm = false">取消</el-button>
        <el-button type="danger" :loading="clearing" @click="confirmClearAndRelearn">
          确认清空并重新学习
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, MagicStick, Refresh, Search, Loading, Delete, Warning } from '@element-plus/icons-vue'
import type { SchemaCache, TableSchema } from '@/types/settings'
import { getSchemaCache, getSchemaTables, triggerSchemaLearning, relearnSchema } from '@/api/settings'

const props = defineProps<{
  datasourceId: number
}>()

const emit = defineEmits<{
  (e: 'learning-started', taskId: number): void
}>()

const loading = ref(false)
const learning = ref(false)
const clearing = ref(false)
const tablesLoading = ref(false)
const schemaCache = ref<SchemaCache | null>(null)
const tables = ref<TableSchema[]>([])
const searchKeyword = ref('')
const showClearConfirm = ref(false)

const filteredTables = computed(() => {
  if (!searchKeyword.value) return tables.value

  const keyword = searchKeyword.value.toLowerCase()
  return tables.value.filter(table => {
    // 匹配表名
    if (table.name.toLowerCase().includes(keyword)) return true
    // 匹配表注释
    if (table.comment?.toLowerCase().includes(keyword)) return true
    // 匹配字段名
    return table.fields.some(f => f.name.toLowerCase().includes(keyword))
  })
})

function getCategoryType(category: string) {
  const types: Record<string, string> = {
    DateTime: 'primary',
    Enum: 'warning',
    Code: 'info',
    Text: '',
    Measure: 'success',
  }
  return types[category] || ''
}

function getTableTypeType(type: string) {
  const types: Record<string, string> = {
    fact: 'danger',
    dimension: 'success',
    other: 'info',
  }
  return types[type] || 'info'
}

function getTableTypeLabel(type: string) {
  const labels: Record<string, string> = {
    fact: '事实表',
    dimension: '维度表',
    other: '其他',
  }
  return labels[type] || type
}

async function loadSchemaCache() {
  loading.value = true
  try {
    schemaCache.value = await getSchemaCache(props.datasourceId)
    if (schemaCache.value) {
      await loadTables()
    }
  } catch (e) {
    console.error('Failed to load schema cache:', e)
  } finally {
    loading.value = false
  }
}

async function loadTables() {
  tablesLoading.value = true
  try {
    const res = await getSchemaTables(props.datasourceId)
    tables.value = res.items
  } catch (e) {
    console.error('Failed to load tables:', e)
  } finally {
    tablesLoading.value = false
  }
}

async function handleLearn() {
  learning.value = true
  try {
    const result = await triggerSchemaLearning(props.datasourceId)
    if (result.success) {
      ElMessage.success('开始学习')
      emit('learning-started', result.task_id)
    } else {
      ElMessage.error(result.message || '启动学习失败')
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '启动学习失败')
  } finally {
    learning.value = false
  }
}

function handleClearAndRelearn() {
  showClearConfirm.value = true
}

async function confirmClearAndRelearn() {
  clearing.value = true
  try {
    const result = await relearnSchema(props.datasourceId)
    if (result.success) {
      ElMessage.success('已清空历史学习内容，正在重新学习')
      showClearConfirm.value = false
      // 清空当前显示
      schemaCache.value = null
      tables.value = []
      // 触发学习进度弹窗
      if (result.task_id) {
        emit('learning-started', result.task_id)
      }
      // 刷新数据
      await loadSchemaCache()
    } else {
      ElMessage.error(result.message || '清空失败')
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '清空并重新学习失败')
  } finally {
    clearing.value = false
  }
}

function handleRowClick(_row: TableSchema) {
  // 展开/折叠行
}

onMounted(() => {
  loadSchemaCache()
})
</script>

<style scoped>
.schema-preview :deep(.el-table__row) {
  cursor: pointer;
}
</style>