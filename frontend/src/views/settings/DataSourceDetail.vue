<template>
  <div class="datasource-detail">
    <!-- 返回按钮 -->
    <div class="mb-4">
      <el-button @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>
    </div>

    <!-- 数据源标题 -->
    <div class="settings-header mb-6">
      <h3 class="text-xl font-semibold">{{ datasource?.ds_name || '加载中...' }}</h3>
      <p class="text-sm text-gray-500 mt-1">
        <el-tag :type="getTypeTagType(datasource?.ds_type)" size="small">
          {{ datasource?.ds_type }}
        </el-tag>
        <span class="ml-2">{{ datasource?.host }}:{{ datasource?.port }}/{{ datasource?.database }}</span>
      </p>
    </div>

    <!-- 页签 -->
    <el-tabs v-model="activeTab" class="detail-tabs">
      <!-- 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <el-card v-loading="loading">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="数据源名称">{{ datasource?.ds_name }}</el-descriptions-item>
            <el-descriptions-item label="数据库类型">{{ datasource?.ds_type }}</el-descriptions-item>
            <el-descriptions-item label="主机地址">{{ datasource?.host || '-' }}</el-descriptions-item>
            <el-descriptions-item label="端口">{{ datasource?.port || '-' }}</el-descriptions-item>
            <el-descriptions-item label="数据库名">{{ datasource?.database || '-' }}</el-descriptions-item>
            <el-descriptions-item label="用户名">{{ datasource?.username || '-' }}</el-descriptions-item>
            <el-descriptions-item label="是否问数目标">
              <el-tag :type="datasource?.is_query_target ? 'success' : 'info'" size="small">
                {{ datasource?.is_query_target ? '是' : '否' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div class="mt-4 flex gap-2">
            <el-button @click="handleTest">测试连接</el-button>
            <el-button v-if="!datasource?.is_query_target" type="primary" @click="handleSetActive">
              设为问数目标
            </el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 数据预览 -->
      <el-tab-pane label="数据预览" name="preview">
        <div class="preview-container flex gap-4">
          <!-- 表列表 -->
          <div class="table-list w-64 bg-white rounded-lg border">
            <div class="p-3 border-b font-medium">表列表 ({{ tables.length }})</div>
            <div class="overflow-auto max-h-96">
              <div
                v-for="table in tables"
                :key="table.table_name"
                class="table-item p-2 cursor-pointer hover:bg-gray-50"
                :class="{ active: selectedTable === table.table_name }"
                @click="handleSelectTable(table.table_name)"
              >
                <el-icon class="mr-2"><Grid /></el-icon>
                {{ table.table_name }}
              </div>
            </div>
          </div>

          <!-- 字段和数据预览 -->
          <div class="flex-1 flex flex-col gap-4">
            <!-- 字段信息 -->
            <el-card v-if="selectedTable">
              <template #header>
                <span>字段信息 - {{ selectedTable }}</span>
              </template>
              <el-table :data="columns" size="small" v-loading="columnsLoading">
                <el-table-column prop="column_name" label="字段名" />
                <el-table-column prop="data_type" label="类型" />
                <el-table-column prop="is_nullable" label="可空" width="80" />
              </el-table>
            </el-card>

            <!-- 数据预览 -->
            <el-card v-if="selectedTable">
              <template #header>
                <span>数据预览（前 100 行）</span>
              </template>
              <el-table :data="previewRows" size="small" v-loading="previewLoading" max-height="300">
                <el-table-column
                  v-for="col in previewColumns"
                  :key="col"
                  :prop="col"
                  :label="col"
                  min-width="120"
                />
              </el-table>
            </el-card>

            <el-empty v-if="!selectedTable" description="请选择一个表查看详情" />
          </div>
        </div>
      </el-tab-pane>

      <!-- Schema 学习 -->
      <el-tab-pane label="Schema 学习" name="schema">
        <SchemaPreview
          :datasource-id="datasourceId"
          @learning-started="handleLearningStarted"
        />
      </el-tab-pane>

      <!-- 知识管理 -->
      <el-tab-pane label="知识" name="knowledge">
        <KnowledgePanel :datasource-id="datasourceId" />
      </el-tab-pane>

      <!-- 对话 -->
      <el-tab-pane label="对话" name="chat">
        <DatasourceChat :datasource-id="datasourceId" />
      </el-tab-pane>
    </el-tabs>

    <!-- 学习进度弹窗 -->
    <LearningProgressDialog
      v-model:visible="showLearningDialog"
      :task-id="learningTaskId"
      :datasource-id="datasourceId"
      :datasource-name="datasource?.ds_name || ''"
      @completed="handleLearningCompleted"
      @view-schema="handleViewSchema"
      @retry="handleRetryLearning"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Grid } from '@element-plus/icons-vue'
import type { DataSourceConfig, TableInfo, ColumnInfo } from '@/types/settings'
import {
  getDatasource,
  testDatasource,
  setQueryDatasource,
  getDatasourceTables,
  getTableInfo,
  previewTable,
} from '@/api/settings'
import KnowledgePanel from './components/KnowledgePanel.vue'
import DatasourceChat from './components/DatasourceChat.vue'
import SchemaPreview from './components/SchemaPreview.vue'
import LearningProgressDialog from './components/LearningProgressDialog.vue'

const router = useRouter()
const route = useRoute()

const datasourceId = computed(() => Number(route.params.id))

const loading = ref(false)
const datasource = ref<DataSourceConfig | null>(null)
const activeTab = ref('info')

// 学习相关状态
const showLearningDialog = ref(false)
const learningTaskId = ref<number | null>(null)

// 数据预览
const tables = ref<TableInfo[]>([])
const selectedTable = ref('')
const columns = ref<ColumnInfo[]>([])
const columnsLoading = ref(false)
const previewLoading = ref(false)
const previewColumns = ref<string[]>([])
const previewRows = ref<unknown[][]>([])

function getTypeTagType(type?: string) {
  if (!type) return 'info'
  const types: Record<string, string> = {
    postgresql: 'primary',
    mysql: 'warning',
    sqlite: 'info',
  }
  return types[type] || 'info'
}

async function loadDatasource() {
  loading.value = true
  try {
    datasource.value = await getDatasource(datasourceId.value)
  } catch (e) {
    ElMessage.error('加载数据源失败')
  } finally {
    loading.value = false
  }
}

async function loadTables() {
  try {
    const res = await getDatasourceTables(datasourceId.value)
    tables.value = res.items
  } catch (e) {
    // Ignore
  }
}

async function handleSelectTable(tableName: string) {
  selectedTable.value = tableName
  columnsLoading.value = true
  previewLoading.value = true

  try {
    // 加载字段信息
    const info = await getTableInfo(datasourceId.value, tableName)
    columns.value = info.columns

    // 加载数据预览
    const preview = await previewTable(datasourceId.value, tableName, 100)
    previewColumns.value = preview.columns
    previewRows.value = preview.rows
  } catch (e) {
    ElMessage.error('加载表信息失败')
  } finally {
    columnsLoading.value = false
    previewLoading.value = false
  }
}

async function handleTest() {
  if (!datasource.value) return
  try {
    const result = await testDatasource(datasource.value.id)
    if (result.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(`连接失败：${result.message}`)
    }
  } catch (e) {
    ElMessage.error('测试失败')
  }
}

async function handleSetActive() {
  if (!datasource.value) return
  try {
    await setQueryDatasource(datasource.value.id)
    ElMessage.success('已设为问数目标')
    loadDatasource()
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

// ============ 学习相关方法 ============

function handleLearningStarted(taskId: number) {
  learningTaskId.value = taskId
  showLearningDialog.value = true
}

function handleLearningCompleted() {
  ElMessage.success('Schema 学习完成')
  // 刷新数据
  loadDatasource()
}

function handleViewSchema() {
  activeTab.value = 'schema'
}

async function handleRetryLearning() {
  // 重试学习 - 由 SchemaPreview 组件处理
}

onMounted(() => {
  loadDatasource()
  loadTables()
})
</script>

<style scoped>
.table-item {
  border-bottom: 1px solid #f0f0f0;
}

.table-item.active {
  background: #ecfdf5;
  color: #059669;
}
</style>