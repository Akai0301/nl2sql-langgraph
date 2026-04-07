<template>
  <header class="top-bar">
    <!-- 左侧：Logo + 标题 -->
    <router-link to="/" class="top-bar-left">
      <div class="logo-container">
        <el-icon :size="24" class="text-blue-500"><DataAnalysis /></el-icon>
        <h1 class="app-title">NL2SQL 智能问数</h1>
      </div>
      <div class="app-subtitle">
        基于 LangGraph 的自然语言查询
      </div>
    </router-link>

    <!-- 右侧：操作区 -->
    <div class="top-bar-right">
      <!-- 系统设置入口 -->
      <router-link to="/settings" class="settings-btn" :class="{ active: isSettingsPage }">
        <el-icon :size="20"><Setting /></el-icon>
      </router-link>

      <!-- 分隔线 -->
      <div class="divider"></div>

      <!-- User Avatar Placeholder (SSO Ready) -->
      <el-tooltip content="企业级登录（即将推出）" placement="bottom">
        <div class="user-avatar-placeholder">
          <el-icon :size="18"><User /></el-icon>
        </div>
      </el-tooltip>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataAnalysis, Setting, User } from '@element-plus/icons-vue'

const route = useRoute()
const isSettingsPage = computed(() => route.path.startsWith('/settings'))
</script>

<style scoped>
.top-bar {
  height: 56px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
  cursor: pointer;
  transition: opacity 0.2s;
}

.top-bar-left:hover {
  opacity: 0.8;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.app-subtitle {
  font-size: 13px;
  color: #9ca3af;
  padding-left: 16px;
  border-left: 1px solid #e5e7eb;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settings-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: #6b7280;
  text-decoration: none;
  transition: all 0.2s;
}

.settings-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.settings-btn.active {
  background: #eff6ff;
  color: #3b82f6;
}

.divider {
  width: 1px;
  height: 24px;
  background: #e5e7eb;
}

.user-avatar-placeholder {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f3f4f6;
  border: 2px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s;
}

.user-avatar-placeholder:hover {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #3b82f6;
}
</style>