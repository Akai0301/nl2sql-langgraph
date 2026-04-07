<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="learning-progress">
      <!-- 状态图标 -->
      <div class="status-icon mb-4 text-center">
        <el-icon v-if="status === 'running'" class="is-loading" :size="48" color="#409EFF">
          <Loading />
        </el-icon>
        <el-icon v-else-if="status === 'completed'" :size="48" color="#67C23A">
          <CircleCheck />
        </el-icon>
        <el-icon v-else-if="status === 'failed'" :size="48" color="#F56C6C">
          <CircleClose />
        </el-icon>
        <el-icon v-else :size="48" color="#909399">
          <Clock />
        </el-icon>
      </div>

      <!-- 进度条 -->
      <el-progress
        :percentage="progress"
        :status="progressStatus"
        :stroke-width="20"
        class="mb-4"
      />

      <!-- 当前步骤 -->
      <div class="current-step mb-2">
        <span class="text-gray-500">当前步骤：</span>
        <span class="font-medium">{{ currentStep || '准备中...' }}</span>
      </div>

      <!-- 提示信息 -->
      <div class="message text-sm text-gray-500 mb-4">
        {{ message }}
      </div>

      <!-- 错误信息 -->
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        :closable="false"
        class="mb-4"
      />

      <!-- 完成统计 -->
      <div v-if="status === 'completed'" class="stats bg-gray-50 p-3 rounded">
        <div class="flex justify-between text-sm">
          <span>表数量：</span>
          <span class="font-medium">{{ tableCount }} 张</span>
        </div>
        <div class="flex justify-between text-sm">
          <span>字段数量：</span>
          <span class="font-medium">{{ fieldCount }} 个</span>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button v-if="status === 'running'" @click="handleCancel">取消</el-button>
      <el-button v-if="status === 'completed'" type="primary" @click="handleViewSchema">查看 Schema</el-button>
      <el-button v-if="status === 'failed'" type="primary" @click="handleRetry">重试</el-button>
      <el-button v-if="status !== 'running'" @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { Loading, CircleCheck, CircleClose, Clock } from '@element-plus/icons-vue'
import type { LearningStatus } from '@/types/settings'
import { getLearningProgress } from '@/api/settings'

const props = defineProps<{
  visible: boolean
  taskId: number | null
  datasourceId: number
  datasourceName: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'completed'): void
  (e: 'view-schema'): void
  (e: 'retry'): void
}>()

const status = ref<LearningStatus>('pending')
const progress = ref(0)
const currentStep = ref('')
const message = ref('')
const error = ref<string | null>(null)
const tableCount = ref(0)
const fieldCount = ref(0)

let pollTimer: ReturnType<typeof setInterval> | null = null

const title = computed(() => {
  const names: Record<LearningStatus, string> = {
    pending: '准备学习',
    running: '正在学习',
    completed: '学习完成',
    failed: '学习失败',
  }
  return `${names[status.value]} - ${props.datasourceName}`
})

const progressStatus = computed(() => {
  if (status.value === 'completed') return 'success'
  if (status.value === 'failed') return 'exception'
  return undefined
})

async function pollProgress() {
  if (!props.taskId) return

  try {
    const data = await getLearningProgress(props.taskId)
    status.value = data.status
    progress.value = data.progress
    currentStep.value = data.current_step
    message.value = data.message
    error.value = data.error

    if (data.status === 'completed') {
      // 获取统计信息
      tableCount.value = 0 // 需要从 schema_cache 获取
      fieldCount.value = 0
      stopPolling()
      emit('completed')
    } else if (data.status === 'failed') {
      stopPolling()
    }
  } catch (e) {
    console.error('Failed to poll progress:', e)
  }
}

function startPolling() {
  stopPolling()
  pollProgress() // 立即执行一次
  pollTimer = setInterval(pollProgress, 2000) // 每 2 秒轮询
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function handleCancel() {
  stopPolling()
  emit('update:visible', false)
}

function handleClose() {
  emit('update:visible', false)
}

function handleViewSchema() {
  emit('view-schema')
  emit('update:visible', false)
}

function handleRetry() {
  emit('retry')
}

// 监听 visible 和 taskId 变化
watch(
  () => [props.visible, props.taskId],
  ([visible, taskId]) => {
    if (visible && taskId) {
      // 重置状态
      status.value = 'pending'
      progress.value = 0
      currentStep.value = ''
      message.value = ''
      error.value = null
      startPolling()
    } else {
      stopPolling()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.learning-progress {
  text-align: center;
}

.status-icon {
  display: flex;
  justify-content: center;
  align-items: center;
}

.current-step {
  text-align: left;
}

.message {
  text-align: left;
}

.stats {
  text-align: left;
}
</style>