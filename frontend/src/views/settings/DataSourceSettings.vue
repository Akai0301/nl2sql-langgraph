<template>
  <div class="datasource-settings">
    <div class="settings-header mb-6">
      <h3 class="text-xl font-semibold">数据源管理</h3>
      <p class="text-sm text-gray-500 mt-1">管理多个数据库连接，支持 PostgreSQL、MySQL、SQLite</p>
    </div>

    <!-- 操作栏 -->
    <div class="mb-4 flex justify-between items-center">
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        新增数据源
      </el-button>
    </div>

    <!-- 数据源列表 -->
    <el-card>
      <el-table :data="datasources" v-loading="loading">
        <el-table-column prop="ds_name" label="名称" />
        <el-table-column prop="ds_type" label="类型">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.ds_type)" size="small">
              {{ row.ds_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="连接信息">
          <template #default="{ row }">
            <span class="text-xs text-gray-500">
              {{ row.host }}:{{ row.port || defaultPort(row.ds_type) }}/{{ row.database }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="is_query_target" label="问数目标" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_query_target" type="success" size="small">是</el-tag>
            <el-tag v-else type="info" size="small">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="340">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="handleDetail(row)">详情</el-button>
              <el-button size="small" @click="handleTest(row.id)">测试</el-button>
              <el-button
                size="small"
                type="primary"
                :loading="learningTaskId !== null && learningDatasourceId === row.id"
                @click="handleLearn(row)"
              >
                学习
              </el-button>
              <el-button
                v-if="!row.is_query_target"
                size="small"
                @click="handleSetActive(row.id)"
              >
                设为目标
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="新增数据源"
      width="500px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="数据源名称" required>
          <el-input v-model="formData.ds_name" placeholder="如：生产数据库" />
        </el-form-item>

        <el-form-item label="数据库类型" required>
          <el-select v-model="formData.ds_type" @change="onTypeChange">
            <el-option value="postgresql" label="PostgreSQL" />
            <el-option value="mysql" label="MySQL" />
            <el-option value="sqlite" label="SQLite" />
          </el-select>
        </el-form-item>

        <template v-if="formData.ds_type !== 'sqlite'">
          <el-form-item label="主机地址">
            <el-input v-model="formData.host" placeholder="localhost" />
          </el-form-item>

          <el-form-item label="端口">
            <el-input-number v-model="formData.port" :min="1" :max="65535" />
          </el-form-item>

          <el-form-item label="数据库名">
            <el-input v-model="formData.database" placeholder="数据库名称" />
          </el-form-item>

          <el-form-item label="用户名">
            <el-input v-model="formData.username" placeholder="用户名" />
          </el-form-item>

          <el-form-item label="密码">
            <el-input v-model="formData.password" type="password" show-password placeholder="密码" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="数据库文件">
            <el-input v-model="formData.database" placeholder="数据库文件路径（如：/path/to/db.sqlite）" />
          </el-form-item>
        </template>

        <el-form-item label="DSN（可选）">
          <el-input
            v-model="formData.dsn_override"
            type="textarea"
            :rows="2"
            placeholder="完整连接串，优先使用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 学习进度弹窗 -->
    <LearningProgressDialog
      v-model:visible="showLearningDialog"
      :task-id="learningTaskId"
      :datasource-id="learningDatasourceId"
      :datasource-name="learningDatasourceName"
      @completed="handleLearningCompleted"
      @view-schema="handleViewSchema"
      @retry="handleRetryLearning"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { DataSourceConfig } from '@/types/settings'
import {
  listDatasources,
  createDatasource,
  deleteDatasource,
  testDatasource,
  setQueryDatasource,
  triggerSchemaLearning,
} from '@/api/settings'
import LearningProgressDialog from './components/LearningProgressDialog.vue'

const router = useRouter()
const loading = ref(false)
const datasources = ref<DataSourceConfig[]>([])
const showAddDialog = ref(false)

// 学习相关状态
const showLearningDialog = ref(false)
const learningTaskId = ref<number | null>(null)
const learningDatasourceId = ref(0)
const learningDatasourceName = ref('')

const formData = ref({
  ds_name: '',
  ds_type: 'postgresql' as 'postgresql' | 'mysql' | 'sqlite',
  host: 'localhost',
  port: 5432,
  database: '',
  username: '',
  password: '',
  dsn_override: '',
})

function getTypeTagType(type: string) {
  const types: Record<string, string> = {
    postgresql: 'primary',
    mysql: 'warning',
    sqlite: 'info',
  }
  return types[type] || 'info'
}

function defaultPort(type: string) {
  const ports: Record<string, number> = {
    postgresql: 5432,
    mysql: 3306,
    sqlite: 0,
  }
  return ports[type] || 0
}

function onTypeChange(type: string) {
  formData.value.port = defaultPort(type)
}

async function loadDatasources() {
  loading.value = true
  try {
    const res = await listDatasources()
    datasources.value = res.items
  } catch (e) {
    ElMessage.error('加载数据源失败')
  } finally {
    loading.value = false
  }
}

async function handleTest(id: number) {
  try {
    const result = await testDatasource(id)
    if (result.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(`连接失败：${result.message}`)
    }
  } catch (e) {
    ElMessage.error('测试失败')
  }
}

async function handleSetActive(id: number) {
  try {
    await setQueryDatasource(id)
    ElMessage.success('已设为问数目标')
    loadDatasources()
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

function handleDetail(row: DataSourceConfig) {
  router.push(`/settings/datasource/${row.id}`)
}

async function handleSave() {
  if (!formData.value.ds_name) {
    ElMessage.warning('请填写数据源名称')
    return
  }

  try {
    await createDatasource(formData.value)
    ElMessage.success('数据源已创建')
    showAddDialog.value = false
    loadDatasources()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '创建失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此数据源？', '确认', { type: 'warning' })
    await deleteDatasource(id)
    ElMessage.success('数据源已删除')
    loadDatasources()
  } catch {
    // Cancelled
  }
}

// ============ 学习相关方法 ============

async function handleLearn(row: DataSourceConfig) {
  try {
    const result = await triggerSchemaLearning(row.id)
    if (result.success) {
      learningTaskId.value = result.task_id
      learningDatasourceId.value = row.id
      learningDatasourceName.value = row.ds_name
      showLearningDialog.value = true
    } else {
      ElMessage.error(result.message || '启动学习失败')
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '启动学习失败')
  }
}

function handleLearningCompleted() {
  ElMessage.success('Schema 学习完成')
  loadDatasources()
}

function handleViewSchema() {
  // 跳转到数据源详情页查看 Schema
  router.push(`/settings/datasource/${learningDatasourceId.value}`)
}

async function handleRetryLearning() {
  // 重新触发学习
  if (learningDatasourceId.value) {
    try {
      const result = await triggerSchemaLearning(learningDatasourceId.value)
      if (result.success) {
        learningTaskId.value = result.task_id
      }
    } catch (e: unknown) {
      ElMessage.error((e as Error).message || '重试失败')
    }
  }
}

onMounted(() => {
  loadDatasources()
})
</script>