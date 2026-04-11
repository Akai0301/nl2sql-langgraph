<template>
  <div class="flow-graph h-full w-full relative">
    <div ref="containerRef" class="h-full w-full">
      <VueFlow
        v-if="nodes.length > 0"
        :nodes="nodes"
        :edges="edges"
        :default-viewport="{ zoom: 0.8, x: 50, y: 20 }"
        :min-zoom="0.5"
        :max-zoom="1.5"
        fit-view-on-init
        :nodes-draggable="false"
        :nodes-connectable="false"
        :edges-updatable="false"
      >
        <Background pattern-color="#e5e7eb" :gap="20" />
        <Controls position="top-right" />
      </VueFlow>
    </div>

    <!-- Legend -->
    <div class="absolute bottom-4 left-4 bg-white rounded-lg shadow-sm p-3 text-xs">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 rounded-full bg-gray-300"></div>
          <span>待执行</span>
        </div>
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></div>
          <span>执行中</span>
        </div>
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 rounded-full bg-green-500"></div>
          <span>已完成</span>
        </div>
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 rounded-full bg-red-500"></div>
          <span>出错</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { VueFlow, Position } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import type { Node, Edge } from '@vue-flow/core'
import { useQueryStore } from '@/stores/queryStore'
import type { NodeStatus } from '@/types'

const store = useQueryStore()
const containerRef = ref<HTMLElement | null>(null)

// Node positions - arranged in shuttle pattern (embedding_generation hidden)
const nodePositions: Record<string, { x: number; y: number }> = {
  start: { x: 50, y: 100 },
  analyze_question: { x: 200, y: 100 },
  // embedding_generation: hidden from frontend display
  knowledge_retrieval: { x: 400, y: 30 },
  metrics_retrieval: { x: 400, y: 100 },
  metadata_retrieval: { x: 400, y: 170 },
  merge_context: { x: 600, y: 100 },
  metadata_analysis: { x: 750, y: 100 },
  sql_generation: { x: 900, y: 100 },
  sql_execution: { x: 1050, y: 100 },
  end: { x: 1200, y: 100 },
}

// Convert store state to VueFlow nodes
const nodes = computed<Node[]>(() => {
  if (!store.graphStructure) return []

  return store.graphStructure.nodes.map((node) => {
    const state = store.nodeStates.get(node.id)
    const status: NodeStatus = state?.status || 'pending'

    return {
      id: node.id,
      position: nodePositions[node.id] || { x: 0, y: 0 },
      type: 'default',
      data: { label: node.label },
      class: `node-${status}`,
      style: getNodeStyle(node.type, status),
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    }
  })
})

// Convert store edges to VueFlow edges
const edges = computed<Edge[]>(() => {
  if (!store.graphStructure) return []

  return store.graphStructure.edges.map((edge) => ({
    id: `e-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: false,
    style: getEdgeStyle(edge.source),
  }))
})

function getNodeStyle(nodeType: string, status: NodeStatus): Record<string, string> {
  const baseStyle: Record<string, string> = {
    padding: '8px 16px',
    'border-radius': '8px',
    'font-size': '12px',
    'font-weight': '500',
  }

  const statusStyles: Record<NodeStatus, Record<string, string>> = {
    pending: {
      background: '#fff',
      border: '2px solid #e5e7eb',
      color: '#9ca3af',
    },
    running: {
      background: '#eff6ff',
      border: '2px solid #3b82f6',
      color: '#1d4ed8',
    },
    completed: {
      background: '#ecfdf5',
      border: '2px solid #10b981',
      color: '#059669',
    },
    error: {
      background: '#fef2f2',
      border: '2px solid #ef4444',
      color: '#dc2626',
    },
  }

  const typeStyles: Record<string, Record<string, string>> = {
    start: { 'border-radius': '20px' },
    end: { 'border-radius': '20px' },
    parallel: { 'border-left': '4px solid #3b82f6' },
  }

  return {
    ...baseStyle,
    ...statusStyles[status],
    ...(typeStyles[nodeType] || {}),
  }
}

function getEdgeStyle(sourceId: string): Record<string, string> {
  const state = store.nodeStates.get(sourceId)
  if (state?.status === 'completed') {
    return { stroke: '#10b981', strokeWidth: '2' }
  }
  if (state?.status === 'running') {
    return { stroke: '#3b82f6', strokeWidth: '2' }
  }
  if (state?.status === 'error') {
    return { stroke: '#ef4444', strokeWidth: '2' }
  }
  return { stroke: '#e5e7eb', strokeWidth: '1' }
}
</script>

<style>
.flow-graph .vue-flow__node {
  transition: all 0.3s ease;
}

.flow-graph .vue-flow__edge-path {
  transition: stroke 0.3s ease, stroke-width 0.3s ease;
}
</style>
