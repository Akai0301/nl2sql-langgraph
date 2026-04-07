<template>
  <div class="step-progress-bar">
    <!-- Compact step indicators -->
    <div class="steps-container">
      <template v-for="(step, index) in steps" :key="step.id">
        <div
          class="step-item"
          :class="getStepClass(step)"
          @click="toggleExpand(step.id)"
        >
          <div class="step-icon">
            <div v-if="step.status === 'completed'" class="step-completed-icon">
              <el-icon><Check /></el-icon>
            </div>
            <el-icon v-else-if="step.status === 'error'" class="text-red-500"><CircleCloseFilled /></el-icon>
            <el-icon v-else-if="step.status === 'running'" class="text-blue-500 is-loading"><Loading /></el-icon>
            <div v-else class="step-pending-dot"></div>
          </div>
          <div class="step-label">{{ step.label }}</div>
          <!-- Display duration for completed steps -->
          <div v-if="step.status === 'completed' && step.durationMs" class="step-duration">
            {{ formatDuration(step.durationMs) }}
          </div>
          <el-icon v-if="hasDetails(step)" class="expand-icon">
            <ArrowDown v-if="expandedSteps.has(step.id)" />
            <ArrowRight v-else />
          </el-icon>
        </div>
        <div v-if="index < steps.length - 1" class="step-connector" :class="{ active: step.status === 'completed' }"></div>
      </template>
    </div>

    <!-- Expanded details -->
    <transition name="slide">
      <div v-if="currentExpandedStep" class="step-details">
        <AnalysisStepDetail
          v-if="currentExpandedStep.id === 'analyze_question'"
          :output="currentExpandedStep.output"
        />
        <RetrievalStepDetail
          v-else-if="['knowledge_retrieval', 'metrics_retrieval', 'metadata_retrieval'].includes(currentExpandedStep.id)"
          :node-id="currentExpandedStep.id"
          :output="currentExpandedStep.output"
          :all-retrieval-outputs="allRetrievalOutputs"
        />
        <SQLStepDetail
          v-else-if="currentExpandedStep.id === 'sql_generation'"
          :output="currentExpandedStep.output"
          :sql="resultSql"
          @edit="$emit('editSql', $event)"
        />
        <ExecutionStepDetail
          v-else-if="currentExpandedStep.id === 'sql_execution'"
          :output="currentExpandedStep.output"
          :result="result"
        />
        <div v-else class="generic-detail">
          <pre>{{ JSON.stringify(currentExpandedStep.output, null, 2) }}</pre>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Check, CircleCloseFilled, Loading, ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import type { StepState, QueryResult } from '@/types'
import AnalysisStepDetail from './step-details/AnalysisStepDetail.vue'
import RetrievalStepDetail from './step-details/RetrievalStepDetail.vue'
import SQLStepDetail from './step-details/SQLStepDetail.vue'
import ExecutionStepDetail from './step-details/ExecutionStepDetail.vue'

const props = defineProps<{
  steps: StepState[]
  result?: QueryResult | null
}>()

defineEmits<{
  editSql: [sql: string]
}>()

const expandedSteps = ref<Set<string>>(new Set())

// Simplified steps for display (group parallel retrievals)
const steps = computed(() => {
  const result: StepState[] = []
  const retrievalSteps: StepState[] = []

  for (const step of props.steps) {
    if (['knowledge_retrieval', 'metrics_retrieval', 'metadata_retrieval'].includes(step.id)) {
      retrievalSteps.push(step)
    } else if (step.id === 'merge_context') {
      // Skip merge_context, it's internal
    } else if (step.id === 'metadata_analysis') {
      // Skip metadata_analysis, it's internal
    } else {
      result.push(step)
    }
  }

  // Add combined retrieval step
  if (retrievalSteps.length > 0) {
    const hasAnyRunning = retrievalSteps.some(s => s.status === 'running')
    const hasAnyError = retrievalSteps.some(s => s.status === 'error')
    const allCompleted = retrievalSteps.every(s => s.status === 'completed')

    // Calculate total duration for retrieval steps (use max since they run in parallel)
    const maxDuration = Math.max(...retrievalSteps.map(s => s.durationMs || 0))

    result.splice(1, 0, {
      id: 'retrieval',
      label: '智能检索',
      status: hasAnyError ? 'error' : hasAnyRunning ? 'running' : allCompleted ? 'completed' : 'pending',
      output: { retrievalSteps },
      durationMs: allCompleted && maxDuration > 0 ? maxDuration : undefined,
    })
  }

  return result
})

const currentExpandedStep = computed(() => {
  for (const stepId of expandedSteps.value) {
    const step = steps.value.find(s => s.id === stepId)
    if (step) return step
  }
  return null
})

const resultSql = computed(() => props.result?.sql || '')

const allRetrievalOutputs = computed(() => {
  const outputs: Record<string, unknown> = {}
  for (const step of props.steps) {
    if (['knowledge_retrieval', 'metrics_retrieval', 'metadata_retrieval'].includes(step.id)) {
      outputs[step.id] = step.output
    }
  }
  return outputs
})

function getStepClass(step: StepState): Record<string, boolean> {
  return {
    pending: step.status === 'pending',
    running: step.status === 'running',
    completed: step.status === 'completed',
    error: step.status === 'error',
    expandable: hasDetails(step),
  }
}

function hasDetails(step: StepState): boolean {
  if (step.status === 'pending') return false
  if (step.id === 'retrieval') return true
  return !!step.output && Object.keys(step.output).length > 0
}

function toggleExpand(stepId: string) {
  if (expandedSteps.value.has(stepId)) {
    expandedSteps.value.delete(stepId)
  } else {
    expandedSteps.value.clear()
    expandedSteps.value.add(stepId)
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  } else if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`
  } else {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.round((ms % 60000) / 1000)
    return `${minutes}m${seconds}s`
  }
}
</script>

<style scoped>
.step-progress-bar {
  margin-bottom: 16px;
}

.steps-container {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 12px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.step-item.expandable:hover {
  background: #e5e7eb;
}

.step-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.step-pending-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d1d5db;
}

.step-completed-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
}

.step-item.running .step-pending-dot {
  background: #3b82f6;
  animation: pulse 1.5s infinite;
}

.step-label {
  font-size: 12px;
  color: #1f2937;
  font-weight: 600;
  margin-top: 4px;
  white-space: nowrap;
}

.step-duration {
  font-size: 10px;
  color: #6b7280;
  margin-top: 2px;
}

.step-item.completed .step-label {
  color: #1f2937;
}

.step-item.running .step-label {
  color: #1f2937;
}

.step-item.error .step-label {
  color: #dc2626;
}

.expand-icon {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.step-connector {
  width: 40px;
  height: 2px;
  background: #3b82f6;
  margin: 0 -8px;
  margin-bottom: 24px;
}

.step-connector.active {
  background: #3b82f6;
}

.step-details {
  margin-top: 12px;
  padding: 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.generic-detail {
  font-size: 12px;
  color: #4b5563;
}

.generic-detail pre {
  margin: 0;
  white-space: pre-wrap;
}
</style>
