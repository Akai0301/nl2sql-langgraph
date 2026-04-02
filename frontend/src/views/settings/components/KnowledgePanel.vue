<template>
  <div class="knowledge-panel">
    <!-- 操作栏 -->
    <div class="mb-4 flex justify-between items-center">
      <div class="flex gap-2">
        <el-select v-model="filterType" placeholder="筛选类型" clearable size="small">
          <el-option value="term" label="业务术语" />
          <el-option value="qa" label="示例 Q&A" />
          <el-option value="metric" label="指标口径" />
          <el-option value="table_desc" label="表说明" />
        </el-select>
      </div>
      <el-button type="primary" size="small" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加知识
      </el-button>
    </div>

    <!-- 知识列表 -->
    <el-table :data="knowledgeList" v-loading="loading" size="small">
      <el-table-column prop="kb_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="getTypeTagType(row.kb_type)" size="small">
            {{ getTypeName(row.kb_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="kb_name" label="名称" />
      <el-table-column prop="kb_content" label="内容">
        <template #default="{ row }">
          <el-popover placement="left" :width="400" trigger="hover">
            <template #reference>
              <span class="text-gray-500 text-xs cursor-pointer hover:text-blue-500">
                {{ truncate(row.kb_content, 50) }}
              </span>
            </template>
            <pre class="text-xs whitespace-pre-wrap">{{ row.kb_content }}</pre>
          </el-popover>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="mt-4 flex justify-end">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="loadKnowledge"
      />
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingKnowledge ? '编辑知识' : '添加知识'"
      width="600px"
    >
      <el-form :model="formData" label-width="80px">
        <el-form-item label="类型" required>
          <el-select v-model="formData.kb_type" @change="onTypeChange">
            <el-option value="term" label="业务术语" />
            <el-option value="qa" label="示例 Q&A" />
            <el-option value="metric" label="指标口径" />
            <el-option value="table_desc" label="表说明" />
          </el-select>
        </el-form-item>

        <el-form-item label="名称" required>
          <el-input v-model="formData.kb_name" placeholder="知识项名称" />
        </el-form-item>

        <el-form-item label="内容">
          <el-input
            v-model="formData.kb_content"
            type="textarea"
            :rows="8"
            placeholder="JSON 格式的知识内容"
          />
          <div class="text-xs text-gray-500 mt-1">
            建议 JSON 格式，如：{{ getTypeTemplate(formData.kb_type) }}
          </div>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { KnowledgeConfig } from '@/types/settings'
import { listKnowledge, createKnowledge, updateKnowledge, deleteKnowledge } from '@/api/settings'

const props = defineProps<{
  datasourceId: number
}>()

const loading = ref(false)
const knowledgeList = ref<KnowledgeConfig[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const filterType = ref('')

const showAddDialog = ref(false)
const editingKnowledge = ref<KnowledgeConfig | null>(null)

const formData = ref({
  kb_type: 'term' as 'term' | 'qa' | 'metric' | 'table_desc',
  kb_name: '',
  kb_content: '',
  is_active: true,
})

const typeNames: Record<string, string> = {
  term: '业务术语',
  qa: '示例 Q&A',
  metric: '指标口径',
  table_desc: '表说明',
}

const typeTagTypes: Record<string, string> = {
  term: 'primary',
  qa: 'success',
  metric: 'warning',
  table_desc: 'info',
}

function getTypeName(type: string) {
  return typeNames[type] || type
}

function getTypeTagType(type: string) {
  return typeTagTypes[type] || 'info'
}

function truncate(str: string | null, len: number) {
  if (!str) return '-'
  return str.length > len ? str.slice(0, len) + '...' : str
}

function getTypeTemplate(type: string) {
  const templates: Record<string, string> = {
    term: '{"term": "销售额", "synonyms": ["销售金额", "营业额"], "meaning": "企业销售商品或服务所获得的收入"}',
    qa: '{"question": "查询销售额", "sql": "SELECT SUM(amount) FROM orders", "rationale": "按金额汇总"}',
    metric: '{"metric_name": "GMV", "definition": "商品交易总额", "aggregation": "SUM"}',
    table_desc: '{"table_name": "orders", "description": "订单表", "columns": [{"name": "id", "meaning": "订单ID"}]}',
  }
  return templates[type] || ''
}

function onTypeChange() {
  formData.value.kb_content = getTypeTemplate(formData.value.kb_type)
}

async function loadKnowledge() {
  loading.value = true
  try {
    const res = await listKnowledge(props.datasourceId, filterType.value || undefined, page.value, pageSize.value)
    knowledgeList.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载知识失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!formData.value.kb_name) {
    ElMessage.warning('请填写名称')
    return
  }

  try {
    if (editingKnowledge.value) {
      await updateKnowledge(props.datasourceId, editingKnowledge.value.id, formData.value)
    } else {
      await createKnowledge(props.datasourceId, formData.value)
    }
    ElMessage.success('保存成功')
    showAddDialog.value = false
    loadKnowledge()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

function handleEdit(row: KnowledgeConfig) {
  editingKnowledge.value = row
  formData.value = {
    kb_type: row.kb_type,
    kb_name: row.kb_name,
    kb_content: row.kb_content || '',
    is_active: row.is_active,
  }
  showAddDialog.value = true
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此知识项？', '确认', { type: 'warning' })
    await deleteKnowledge(props.datasourceId, id)
    ElMessage.success('删除成功')
    loadKnowledge()
  } catch {
    // Cancelled
  }
}

watch(() => props.datasourceId, () => {
  loadKnowledge()
})

watch(filterType, () => {
  page.value = 1
  loadKnowledge()
})

onMounted(() => {
  loadKnowledge()
})
</script>