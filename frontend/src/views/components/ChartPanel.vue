<template>
  <div class="chart-panel bg-white rounded-lg shadow-sm p-4">
    <!-- Chart Type Selector -->
    <div class="flex items-center gap-4 mb-4">
      <span class="text-sm text-gray-600">图表类型：</span>
      <el-radio-group v-model="chartType" size="small">
        <el-radio-button value="bar">柱状图</el-radio-button>
        <el-radio-button value="line">折线图</el-radio-button>
        <el-radio-button value="pie">饼图</el-radio-button>
      </el-radio-group>

      <div class="flex-1"></div>

      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-600">X轴：</span>
        <el-select v-model="xAxis" size="small" placeholder="选择维度" style="width: 120px">
          <el-option
            v-for="col in categoryColumns"
            :key="col"
            :label="col"
            :value="col"
          />
        </el-select>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-600">Y轴：</span>
        <el-select v-model="yAxis" size="small" placeholder="选择指标" style="width: 120px">
          <el-option
            v-for="col in numericColumns"
            :key="col"
            :label="col"
            :value="col"
          />
        </el-select>
      </div>
    </div>

    <!-- Chart -->
    <div v-if="canRenderChart" class="h-80">
      <v-chart :option="chartOption" autoresize />
    </div>

    <div v-else class="h-80 flex items-center justify-center text-gray-400">
      <div class="text-center">
        <el-icon :size="48"><PieChart /></el-icon>
        <p class="mt-2">请选择至少一个数值列作为Y轴</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { PieChart } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart as EchartsPie } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useQueryStore } from '@/stores/queryStore'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  EchartsPie,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

const props = defineProps<{
  columns?: string[]
  rows?: unknown[][]
}>()

const store = useQueryStore()

const chartType = ref<'bar' | 'line' | 'pie'>('bar')
const xAxis = ref('')
const yAxis = ref('')

// Get column types
const columns = computed(() => props.columns || store.result?.columns || [])
const rows = computed(() => props.rows || store.result?.rows || [])

const categoryColumns = computed(() => columns.value)
const numericColumns = computed(() => {
  if (rows.value.length === 0) return []

  return columns.value.filter((_col, index) => {
    // Check if the column contains numeric values
    const sampleValue = rows.value[0]?.[index]
    return typeof sampleValue === 'number'
  })
})

// Auto-select columns
watch([numericColumns, categoryColumns], ([nums, cats]) => {
  if (!yAxis.value && nums.length > 0) {
    yAxis.value = nums[0]
  }
  if (!xAxis.value && cats.length > 0) {
    // Prefer non-numeric columns for X axis
    const nonNumeric = cats.filter(c => !nums.includes(c))
    xAxis.value = nonNumeric.length > 0 ? nonNumeric[0] : cats[0]
  }
}, { immediate: true })

const canRenderChart = computed(() => {
  return yAxis.value && rows.value.length > 0
})

// Prepare chart data
const chartData = computed(() => {
  if (!xAxis.value || !yAxis.value) return { labels: [], values: [] }

  const xIndex = columns.value.indexOf(xAxis.value)
  const yIndex = columns.value.indexOf(yAxis.value)

  if (xIndex === -1 || yIndex === -1) return { labels: [], values: [] }

  const labels: string[] = []
  const values: number[] = []

  rows.value.forEach(row => {
    labels.push(String(row[xIndex] ?? ''))
    values.push(Number(row[yIndex]) || 0)
  })

  return { labels, values }
})

// Chart option
const chartOption = computed(() => {
  const { labels, values } = chartData.value

  if (chartType.value === 'pie') {
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
      },
      series: [
        {
          type: 'pie',
          radius: '60%',
          data: labels.map((label, index) => ({
            name: label,
            value: values[index],
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    }
  }

  return {
    tooltip: {
      trigger: 'axis',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        rotate: labels.length > 5 ? 45 : 0,
      },
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: yAxis.value,
        type: chartType.value,
        data: values,
        smooth: chartType.value === 'line',
        areaStyle: chartType.value === 'line' ? {} : undefined,
      },
    ],
  }
})
</script>
