<template>
  <div class="retrieval-list">
    <div v-if="items.length === 0" class="empty-text">
      {{ emptyText }}
    </div>
    <div v-else class="items-container">
      <div
        v-for="(item, index) in items"
        :key="index"
        class="retrieval-item"
      >
        <div
          v-for="field in fields"
          :key="field.key"
          class="item-field"
        >
          <span class="field-label">{{ field.label }}:</span>
          <span class="field-value">{{ getItemValue(item, field.key) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  items: Record<string, unknown>[]
  fields: { key: string; label: string }[]
  emptyText: string
}>()

function getItemValue(item: Record<string, unknown>, key: string): string {
  const value = item[key]
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.retrieval-list {
  max-height: 300px;
  overflow-y: auto;
}

.empty-text {
  color: #9ca3af;
  text-align: center;
  padding: 24px;
  font-size: 14px;
}

.items-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.retrieval-item {
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 13px;
}

.item-field {
  margin-bottom: 4px;
}

.item-field:last-child {
  margin-bottom: 0;
}

.field-label {
  color: #6b7280;
  margin-right: 4px;
}

.field-value {
  color: #1f2937;
}
</style>
