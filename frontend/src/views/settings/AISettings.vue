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
        <el-table-column prop="has_api_key" label="API Key" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.has_api_key" type="success" size="small">已配置</el-tag>
            <el-tag v-else type="danger" size="small">未配置</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" type="success" size="small">激活</el-tag>
            <el-tag v-else type="info" size="small">未激活</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                v-if="!row.is_active"
                size="small"
                @click="handleActivate(row.id)"
              >
                激活
              </el-button>
              <el-button size="small" @click="handleTest(row)">
                测试
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

        <el-form-item label="API Key" :required="!editingConfig">
          <el-input
            v-model="formData.api_key"
            :type="showApiKey ? 'text' : 'password'"
            :placeholder="editingConfig ? '输入新密钥覆盖原值，留空保留原值' : '输入 API Key'"
            class="flex-1"
          >
            <template #suffix>
              <el-icon class="cursor-pointer text-gray-600 hover:text-gray-800" @click="toggleApiKeyVisibility">
                <View v-if="!showApiKey" />
                <Hide v-else />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button
          type="info"
          @click="handleTestInDialog"
          :loading="testing"
          :disabled="!formData.model_name"
        >
          测试连接
        </el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { View, Hide } from '@element-plus/icons-vue'
import type { AIConfig } from '@/types/settings'
import {
  listAIConfigs,
  createAIConfig,
  updateAIConfig,
  deleteAIConfig,
  activateAIConfig,
  testAIConfig,
  getAIConfigApiKey,
  type AITestResult,
} from '@/api/settings'

const loading = ref(false)
const testing = ref(false)
const configs = ref<AIConfig[]>([])
const activeConfig = ref<AIConfig | null>(null)
const showAddDialog = ref(false)
const editingConfig = ref<AIConfig | null>(null)
const testResult = ref<AITestResult | null>(null)

// API Key 可见性切换
const showApiKey = ref(false)

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
    console.error('加载配置失败:', e)
    ElMessage.error(`加载配置失败: ${(e as Error).message || '未知错误'}`)
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

  // 构建请求数据，如果 API Key 为空则不传（保留原值）
  const saveData: Record<string, unknown> = {
    config_name: formData.value.config_name,
    model_name: formData.value.model_name,
    base_url: formData.value.base_url || null,
  }

  // 只有输入了 API Key 才传递
  if (formData.value.api_key) {
    saveData.api_key = formData.value.api_key
  }

  try {
    if (editingConfig.value) {
      await updateAIConfig(editingConfig.value.id, saveData)
    } else {
      // 新建时必须填写 API Key
      if (!formData.value.api_key) {
        ElMessage.warning('请填写 API Key')
        return
      }
      await createAIConfig({
        ...saveData,
        provider: formData.value.provider,
        api_key: formData.value.api_key,
      })
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

async function handleEdit(config: AIConfig) {
  editingConfig.value = config
  formData.value = {
    config_name: config.config_name,
    provider: config.provider,
    model_name: config.model_name,
    base_url: config.base_url || '',
    api_key: '',
  }
  showApiKey.value = false
  showAddDialog.value = true

  // 如果已配置 API Key，自动加载显示
  if (config.has_api_key) {
    try {
      const result = await getAIConfigApiKey(config.id)
      formData.value.api_key = result.api_key
      showApiKey.value = false  // 默认隐藏，用户可切换
    } catch (e) {
      // 加载失败不影响编辑，用户可手动输入
      console.error('加载 API Key 失败:', e)
    }
  }
}

/**
 * 切换 API Key 可见性
 */
function toggleApiKeyVisibility() {
  showApiKey.value = !showApiKey.value
}

/**
 * 测试已保存的配置
 */
async function handleTest(config: AIConfig) {
  testing.value = true
  try {
    const result = await testAIConfig(config.id)
    if (result.success) {
      ElMessage.success(`连接成功 (${result.latency_ms}ms)`)
    } else {
      ElMessage.error(result.message || '连接失败')
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '测试失败')
  } finally {
    testing.value = false
  }
}

/**
 * 在对话框中测试配置（使用当前表单数据）
 */
async function handleTestInDialog() {
  if (!formData.value.model_name) {
    ElMessage.warning('请填写模型名称')
    return
  }

  // 如果是编辑模式且有 ID，可以测试
  if (editingConfig.value) {
    testing.value = true
    try {
      // 使用表单数据覆盖数据库配置进行测试
      const result = await testAIConfig(editingConfig.value.id, {
        base_url: formData.value.base_url || undefined,
        api_key: formData.value.api_key || undefined,
        model_name: formData.value.model_name,
      })
      testResult.value = result
      if (result.success) {
        ElMessage.success(`连接成功 (${result.latency_ms}ms)`)
      } else {
        ElMessage.error(result.message || '连接失败')
      }
    } catch (e: unknown) {
      ElMessage.error((e as Error).message || '测试失败')
    } finally {
      testing.value = false
    }
  } else {
    // 新建模式：需要先保存才能测试
    ElMessage.info('请先保存配置后再测试')
  }
}

onMounted(() => {
  loadConfigs()
})
</script>