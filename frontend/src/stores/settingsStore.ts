import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DataSource } from '@/types'
import { getActiveDatasource, listDatasources, activateDatasource } from '@/api/query'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const activeDatasource = ref<DataSource | null>(null)
  const datasources = ref<DataSource[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const datasourceMessage = ref<string | null>(null)  // 提示信息（如未配置数据源时的提示）

  // Load active datasource
  async function loadActiveDatasource() {
    try {
      const response = await getActiveDatasource()
      activeDatasource.value = response.datasource
      datasourceMessage.value = response.message || null
    } catch (e) {
      console.error('Failed to load active datasource:', e)
      error.value = '加载数据源失败'
    }
  }

  // Load all datasources
  async function loadDatasources() {
    loading.value = true
    try {
      const response = await listDatasources()
      datasources.value = response.items
    } catch (e) {
      console.error('Failed to load datasources:', e)
      error.value = '加载数据源列表失败'
    } finally {
      loading.value = false
    }
  }

  // Switch datasource
  async function switchDatasource(dsId: number) {
    loading.value = true
    try {
      await activateDatasource(dsId)
      // Reload active datasource after switch
      await loadActiveDatasource()
    } catch (e) {
      console.error('Failed to switch datasource:', e)
      error.value = '切换数据源失败'
    } finally {
      loading.value = false
    }
  }

  // Initialize: load both active datasource and datasource list
  async function initialize() {
    await Promise.all([
      loadActiveDatasource(),
      loadDatasources(),
    ])
  }

  // Get display text for current datasource
  function getDatasourceDisplayText(): string {
    if (!activeDatasource.value) {
      return '未配置数据源'
    }

    const ds = activeDatasource.value
    const typeLabel = getTypeLabel(ds.ds_type)

    if (ds.is_from_env) {
      return `${ds.ds_name} (${typeLabel})`
    }

    return `${ds.ds_name} (${typeLabel}${ds.database ? ` - ${ds.database}` : ''})`
  }

  // Get type label
  function getTypeLabel(type: string): string {
    switch (type) {
      case 'postgresql': return 'PostgreSQL'
      case 'mysql': return 'MySQL'
      case 'sqlite': return 'SQLite'
      default: return type
    }
  }

  // Load on init
  initialize()

  return {
    // State
    activeDatasource,
    datasources,
    loading,
    error,
    datasourceMessage,
    // Actions
    loadActiveDatasource,
    loadDatasources,
    switchDatasource,
    initialize,
    // Helpers
    getDatasourceDisplayText,
    getTypeLabel,
  }
})