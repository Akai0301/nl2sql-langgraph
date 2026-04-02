<template>
  <div class="analysis-detail">
    <div class="detail-header">
      <el-icon class="mr-2"><Search /></el-icon>
      <span>问题分析结果</span>
    </div>

    <div class="detail-content">
      <!-- Keywords -->
      <div v-if="keywords.length > 0" class="keywords-section">
        <div class="section-label">提取的关键词</div>
        <div class="keywords-list">
          <el-tag
            v-for="keyword in keywords"
            :key="keyword"
            size="small"
            type="info"
            class="keyword-tag"
          >
            {{ keyword }}
          </el-tag>
        </div>
      </div>

      <!-- Intent (if available) -->
      <div v-if="intent" class="intent-section">
        <div class="section-label">识别意图</div>
        <div class="intent-text">{{ intent }}</div>
      </div>

      <!-- No data -->
      <div v-if="keywords.length === 0 && !intent" class="no-data">
        暂无分析数据
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps<{
  output?: Record<string, unknown>
}>()

const keywords = computed(() => {
  if (!props.output?.keywords) return []
  const kw = props.output.keywords
  return Array.isArray(kw) ? kw : []
})

const intent = computed(() => {
  return props.output?.intent as string | undefined
})
</script>

<style scoped>
.analysis-detail {
  min-width: 200px;
}

.detail-header {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #374151;
  margin-bottom: 12px;
}

.detail-content {
  font-size: 14px;
}

.section-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}

.keywords-section {
  margin-bottom: 16px;
}

.keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-tag {
  font-size: 13px;
}

.intent-section {
  margin-bottom: 8px;
}

.intent-text {
  color: #1f2937;
  background: #f3f4f6;
  padding: 8px 12px;
  border-radius: 6px;
}

.no-data {
  color: #9ca3af;
  text-align: center;
  padding: 16px;
}
</style>
