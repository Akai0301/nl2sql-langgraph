<template>
  <div class="sql-detail">
    <div class="detail-header">
      <el-icon class="mr-2"><Document /></el-icon>
      <span>生成的 SQL</span>
      <div class="header-actions">
        <el-button text size="small" @click="copySql">
          <el-icon class="mr-1"><CopyDocument /></el-icon>
          复制
        </el-button>
        <el-button text size="small" @click="toggleEdit">
          <el-icon class="mr-1"><Edit /></el-icon>
          {{ isEditing ? '取消' : '编辑' }}
        </el-button>
      </div>
    </div>

    <div class="sql-content">
      <div v-if="!isEditing" class="sql-display">
        <pre><code>{{ displaySql }}</code></pre>
      </div>
      <div v-else class="sql-edit">
        <el-input
          v-model="editedSql"
          type="textarea"
          :rows="8"
          placeholder="编辑 SQL..."
        />
        <div class="edit-actions">
          <el-button size="small" @click="cancelEdit">取消</el-button>
          <el-button type="primary" size="small" @click="applyEdit">
            应用并重新执行
          </el-button>
        </div>
      </div>
    </div>

    <!-- Rationale -->
    <div v-if="rationale" class="rationale-section">
      <div class="section-label">生成说明</div>
      <div class="rationale-text">{{ rationale }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Document, CopyDocument, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  output?: Record<string, unknown>
  sql?: string
}>()

const emit = defineEmits<{
  edit: [sql: string]
}>()

const isEditing = ref(false)
const editedSql = ref('')

const displaySql = computed(() => {
  if (props.sql) return props.sql
  if (props.output?.generated_sql) return props.output.generated_sql as string
  return '-- SQL 将在此显示'
})

const rationale = computed(() => {
  return props.output?.rationale as string | undefined
})

function copySql() {
  navigator.clipboard.writeText(displaySql.value)
  ElMessage.success('SQL 已复制到剪贴板')
}

function toggleEdit() {
  if (isEditing.value) {
    cancelEdit()
  } else {
    editedSql.value = displaySql.value
    isEditing.value = true
  }
}

function cancelEdit() {
  isEditing.value = false
  editedSql.value = ''
}

function applyEdit() {
  if (editedSql.value.trim()) {
    emit('edit', editedSql.value)
    isEditing.value = false
  }
}
</script>

<style scoped>
.sql-detail {
  min-width: 400px;
}

.detail-header {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #374151;
  margin-bottom: 12px;
}

.header-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.sql-content {
  margin-bottom: 12px;
}

.sql-display {
  background: #1e293b;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.sql-display pre {
  margin: 0;
}

.sql-display code {
  color: #e2e8f0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.sql-edit {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.rationale-section {
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.section-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}

.rationale-text {
  font-size: 13px;
  color: #4b5563;
  background: #f3f4f6;
  padding: 8px 12px;
  border-radius: 6px;
}
</style>
