<template>
  <div class="ai-settings">
    <div class="settings-header mb-6">
      <h3 class="text-xl font-semibold">AI 模型配置</h3>
      <p class="text-sm text-gray-500 mt-1">配置大语言模型提供商和参数</p>
    </div>

    <!-- 当前激活配置 -->
    <el-card class="mb-4">
      <template #header>
        <div class="flex items-center justify-between">
          <span>当前激活配置</span>
          <el-button type="primary" size="small" @click="showAddDialog = true">
            新增配置
          </el-button>
        </div>
      </template>

      <div v-if="activeConfig" class="active-config">
        <div class="flex items-center gap-3">
          <el-tag :type="getProviderTagType(activeConfig.provider)">
            {{ activeConfig.provider }}
          </el-tag>
          <span class="font-medium">{{ activeConfig.config_name }}</span>
          <span class="text-gray-500">{{ activeConfig.model_name }}</span>
        </div>
      </div>
      <div v-else class="text-gray-400">
        未配置激活模型，使用环境变量默认值
      </div>
    </el-card>

    <!-- 配置列表 -->
    <el-card>
      <template #header>
        <span>所有配置</span>
      </template>

      <el-table :data="configs" v-loading="loading">
        <el-table-column prop="config_name" label="配置名称" />
        <el-table-column prop="provider" label="提供商">
          <template #default="{ row }">
            <el-tag :type="getProviderTagType(row.provider)" size="small">
              {{ row.provider }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型" />
        <el-table-column prop="base_url" label="API Base URL">
          <template #default="{ row }">
            <span class="text-xs text-gray-500">{{ row.base_url || '默认' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" type="success" size="small">激活</el-tag>
            <el-tag v-else type="info" size="small">未激活</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                v-if="!row.is_active"
                size="small"
                @click="handleActivate(row.id)"
              >
                激活
              </el-button>
              <el-button size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingConfig ? '编辑配置' : '新增配置'"
      width="500px"
    >
      <el-form :model="formData" label-width="120px">
        <el-form-item label="配置名称" required>
          <el-input v-model="formData.config_name" placeholder="如：生产环境-OpenAI" />
        </el-form-item>

        <el-form-item label="提供商" required>
          <el-select v-model="formData.provider" @change="onProviderChange">
            <el-option value="openai" label="OpenAI" />
            <el-option value="anthropic" label="Anthropic" />
            <el-option value="deepseek" label="DeepSeek (国内代理)" />
            <el-option value="custom" label="自定义提供商" />
          </el-select>
        </el-form-item>

        <el-form-item label="模型名称" required>
          <el-input v-model="formData.model_name" placeholder="如：gpt-4o-mini" />
          <div v-if="formData.provider === 'openai'" class="text-xs text-gray-500 mt-1">
            推荐：gpt-4o-mini, gpt-4o, gpt-3.5-turbo
          </div>
          <div v-if="formData.provider === 'anthropic'" class="text-xs text-gray-500 mt-1">
            推荐：claude-3-5-sonnet-20241022, claude-3-opus-20240229
          </div>
          <div v-if="formData.provider === 'deepseek'" class="text-xs text-gray-500 mt-1">
            推荐：deepseek-chat, deepseek-coder
          </div>
        </el-form-item>

        <el-form-item label="API Base URL">
          <el-input v-model="formData.base_url" placeholder="自定义 API 地址" />
          <div v-if="formData.provider === 'deepseek'" class="text-xs text-gray-500 mt-1">
            默认：https://api.deepseek.com/v1
          </div>
        </el-form-item>

        <el-form-item label="API Key" required>
          <el-input
            v-model="formData.api_key"
            type="password"
            show-password
            placeholder="输入 API Key"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { AIConfig } from '@/types/settings'
import { listAIConfigs, createAIConfig, updateAIConfig, deleteAIConfig, activateAIConfig } from '@/api/settings'

const loading = ref(false)
const configs = ref<AIConfig[]>([])
const activeConfig = ref<AIConfig | null>(null)
const showAddDialog = ref(false)
const editingConfig = ref<AIConfig | null>(null)

const formData = ref({
  config_name: '',
  provider: 'openai' as 'openai' | 'anthropic' | 'deepseek' | 'custom',
  model_name: '',
  base_url: '',
  api_key: '',
})

function getProviderTagType(provider: string) {
  const types: Record<string, string> = {
    openai: 'primary',
    anthropic: 'warning',
    deepseek: 'success',
    custom: 'info',
  }
  return types[provider] || 'info'
}

function onProviderChange(provider: string) {
  if (provider === 'deepseek' && !formData.value.base_url) {
    formData.value.base_url = 'https://api.deepseek.com/v1'
  }
}

async function loadConfigs() {
  loading.value = true
  try {
    const res = await listAIConfigs()
    configs.value = res.items
    activeConfig.value = res.active || null
  } catch (e) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleActivate(id: number) {
  try {
    await activateAIConfig(id)
    ElMessage.success('配置已激活')
    loadConfigs()
  } catch (e) {
    ElMessage.error('激活失败')
  }
}

async function handleSave() {
  if (!formData.value.config_name || !formData.value.model_name) {
    ElMessage.warning('请填写必填项')
    return
  }

  try {
    if (editingConfig.value) {
      await updateAIConfig(editingConfig.value.id, formData.value)
    } else {
      await createAIConfig(formData.value)
    }
    ElMessage.success('配置已保存')
    showAddDialog.value = false
    loadConfigs()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '保存失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此配置？', '确认', { type: 'warning' })
    await deleteAIConfig(id)
    ElMessage.success('配置已删除')
    loadConfigs()
  } catch {
    // Cancelled
  }
}

function handleEdit(config: AIConfig) {
  editingConfig.value = config
  formData.value = {
    config_name: config.config_name,
    provider: config.provider,
    model_name: config.model_name,
    base_url: config.base_url || '',
    api_key: '',
  }
  showAddDialog.value = true
}

onMounted(() => {
  loadConfigs()
})
</script>