<template>
  <div class="example-questions p-6">
    <h2 class="text-lg font-medium text-gray-700 mb-4">
      <el-icon class="mr-2 align-middle"><Opportunity /></el-icon>
      试试这些问题
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="example in examples"
        :key="example.id"
        class="example-card"
        @click="$emit('select', example.question)"
      >
        <div class="example-icon">
          <el-icon :size="24"><component :is="example.icon" /></el-icon>
        </div>
        <div class="example-content">
          <div class="example-category">{{ example.category }}</div>
          <div class="example-question">{{ example.question }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Opportunity,
  TrendCharts,
  PieChart,
  Location,
  Calendar,
  User,
  DataAnalysis,
  ShoppingCart,
  Goods,
  Money,
} from '@element-plus/icons-vue'

defineEmits<{
  select: [question: string]
}>()

const examples = [
  // 基础销售分析
  {
    id: '1',
    question: '查询过去30天各地区的订单金额',
    category: '销售分析',
    icon: TrendCharts,
  },
  {
    id: '2',
    question: '按月份统计最近半年的销售趋势',
    category: '趋势分析',
    icon: PieChart,
  },
  {
    id: '3',
    question: '查询各区域的订单数量分布',
    category: '区域分析',
    icon: Location,
  },
  // 同比分析（新增 2024 数据支持）
  {
    id: '4',
    question: '2025年12月销售额同比增长率',
    category: '同比分析',
    icon: Calendar,
  },
  {
    id: '5',
    question: '2024年第四季度各品类销售额',
    category: '同比分析',
    icon: DataAnalysis,
  },
  {
    id: '6',
    question: '各月份环比增长率',
    category: '环比分析',
    icon: TrendCharts,
  },
  // 客户行为分析（RFM）
  {
    id: '7',
    question: '各会员等级的消费金额分布',
    category: '客户分析',
    icon: User,
  },
  {
    id: '8',
    question: '客户复购率统计',
    category: '客户分析',
    icon: User,
  },
  {
    id: '9',
    question: '消费金额超过5万的客户有哪些',
    category: '客户分析',
    icon: Money,
  },
  // 分布分析
  {
    id: '10',
    question: '订单金额区间分布',
    category: '分布分析',
    icon: ShoppingCart,
  },
  {
    id: '11',
    question: '各价格区间产品的销售占比',
    category: '分布分析',
    icon: Goods,
  },
  {
    id: '12',
    question: '各品类销售额占比',
    category: '占比分析',
    icon: PieChart,
  },
]
</script>

<style scoped>
.example-questions {
  max-width: 1200px;
  margin: 0 auto;
}

.example-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.example-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

.example-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 12px;
  color: white;
}

.example-category {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.example-question {
  font-size: 14px;
  color: #1f2937;
  font-weight: 500;
}
</style>
