<template>
  <div class="query-input">
    <el-form @submit.prevent="handleSubmit">
      <div class="flex gap-3">
        <el-input
          v-model="question"
          placeholder="输入您的问题，例如：查询过去30天按地区的订单金额"
          size="large"
          :disabled="store.isExecuting"
          clearable
          @keyup.enter="handleSubmit"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          size="large"
          :loading="store.isExecuting"
          @click="handleSubmit"
        >
          {{ store.isExecuting ? '查询中' : '查询' }}
        </el-button>
        <el-button
          v-if="store.isExecuting"
          size="large"
          @click="store.cancelQuery"
        >
          取消
        </el-button>
      </div>
    </el-form>

    <!-- Quick Examples -->
    <div class="mt-3 flex gap-2 flex-wrap">
      <span class="text-xs text-gray-400 mr-2">示例问题：</span>
      <el-tag
        v-for="example in examples"
        :key="example"
        size="small"
        class="cursor-pointer hover:bg-blue-50"
        @click="question = example"
      >
        {{ example }}
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useQueryStore } from '@/stores/queryStore'

const store = useQueryStore()
const question = ref('')

const examples = [
  '查询最近30天的订单金额',
  '按月统计销售额',
  '查询各地区的订单数量',
  '过去7天按地区的GMV',
]

async function handleSubmit() {
  const q = question.value.trim()
  if (!q) return

  try {
    await store.executeQuery(q)
  } catch (e) {
    console.error('Query failed:', e)
  }
}
</script>

<style scoped>
.query-input {
  width: 100%;
}
</style>
