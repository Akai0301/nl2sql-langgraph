<template>
  <div class="knowledge-settings">
    <div class="settings-header mb-6">
      <h3 class="text-xl font-semibold">知识库配置</h3>
      <p class="text-sm text-gray-500 mt-1">管理各数据源的业务知识，包括术语、示例 Q&A、指标口径、表说明</p>
    </div>

    <!-- 知识类型说明 -->
    <el-card class="mb-6">
      <template #header>
        <span>知识类型说明</span>
      </template>
      <div class="grid grid-cols-2 gap-4">
        <div class="type-card">
          <el-tag type="primary">业务术语</el-tag>
          <p class="text-sm text-gray-500 mt-2">业务术语解释、同义词映射。帮助 AI 理解业务黑话。</p>
        </div>
        <div class="type-card">
          <el-tag type="success">示例 Q&A</el-tag>
          <p class="text-sm text-gray-500 mt-2">常见问题的 SQL 示例。AI 会参考示例生成更准确的 SQL。</p>
        </div>
        <div class="type-card">
          <el-tag type="warning">指标口径</el-tag>
          <p class="text-sm text-gray-500 mt-2">指标口径定义、计算规则。确保指标计算的一致性。</p>
        </div>
        <div class="type-card">
          <el-tag type="info">表说明</el-tag>
          <p class="text-sm text-gray-500 mt-2">表/字段的业务含义说明。帮助 AI 理解数据结构。</p>
        </div>
      </div>
    </el-card>

    <!-- 数据源知识统计 -->
    <el-card>
      <template #header>
        <span>各数据源知识统计</span>
      </template>

      <el-table :data="datasourceStats" v-loading="loading">
        <el-table-column prop="ds_name" label="数据源" />
        <el-table-column prop="ds_type" label="类型">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.ds_type)" size="small">
              {{ row.ds_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="术语" width="80">
          <template #default="{ row }">
            {{ row.term_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="Q&A" width="80">
          <template #default="{ row }">
            {{ row.qa_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="指标" width="80">
          <template #default="{ row }">
            {{ row.metric_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="表说明" width="80">
          <template #default="{ row }">
            {{ row.table_desc_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="goToDetail(row.id)">
              管理
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { DataSourceConfig } from '@/types/settings'
import { listDatasources, listKnowledge } from '@/api/settings'

interface DatasourceStat extends DataSourceConfig {
  term_count: number
  qa_count: number
  metric_count: number
  table_desc_count: number
}

const router = useRouter()
const loading = ref(false)
const datasourceStats = ref<DatasourceStat[]>([])

function getTypeTagType(type: string) {
  const types: Record<string, string> = {
    postgresql: 'primary',
    mysql: 'warning',
    sqlite: 'info',
  }
  return types[type] || 'info'
}

async function loadStats() {
  loading.value = true
  try {
    const res = await listDatasources()

    const stats: DatasourceStat[] = []

    for (const ds of res.items) {
      // 加载各类型知识数量
      const [term, qa, metric, tableDesc] = await Promise.all([
        listKnowledge(ds.id, 'term', 1, 1),
        listKnowledge(ds.id, 'qa', 1, 1),
        listKnowledge(ds.id, 'metric', 1, 1),
        listKnowledge(ds.id, 'table_desc', 1, 1),
      ])

      stats.push({
        ...ds,
        term_count: term.total || 0,
        qa_count: qa.total || 0,
        metric_count: metric.total || 0,
        table_desc_count: tableDesc.total || 0,
      })
    }

    datasourceStats.value = stats
  } catch (e) {
    // Ignore
  } finally {
    loading.value = false
  }
}

function goToDetail(id: number) {
  router.push(`/settings/datasource/${id}`)
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.type-card {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
</style>