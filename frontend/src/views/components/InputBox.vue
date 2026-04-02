<template>
  <div class="input-box">
    <div class="input-container">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="1"
        :autosize="{ minRows: 1, maxRows: 4 }"
        placeholder="输入您的问题，例如：查询过去30天各地区的订单金额"
        :disabled="isExecuting"
        @keydown.enter.exact.prevent="handleSubmit"
      />
      <el-button
        v-if="!isExecuting"
        type="primary"
        :disabled="!inputText.trim()"
        @click="handleSubmit"
      >
        <el-icon><Position /></el-icon>
        发送
      </el-button>
      <el-button
        v-else
        type="danger"
        @click="handleStop"
      >
        <el-icon><VideoPause /></el-icon>
        停止
      </el-button>
    </div>
    <div class="input-hints">
      <span class="hint">按 Enter 发送</span>
      <span class="hint">|</span>
      <span class="hint">支持自然语言查询</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Position, VideoPause } from '@element-plus/icons-vue'

const props = defineProps<{
  isExecuting?: boolean
}>()

const emit = defineEmits<{
  submit: [question: string]
  stop: []
}>()

const inputText = ref('')

function handleSubmit() {
  const text = inputText.value.trim()
  if (text && !props.isExecuting) {
    emit('submit', text)
    inputText.value = ''
  }
}

function handleStop() {
  emit('stop')
}
</script>

<style scoped>
.input-box {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.input-container {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  max-width: 900px;
  margin: 0 auto;
}

.input-container .el-textarea {
  flex: 1;
}

.input-container .el-button {
  height: 40px;
  padding: 0 24px;
}

.input-hints {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

.hint {
  font-size: 12px;
  color: #9ca3af;
}
</style>
