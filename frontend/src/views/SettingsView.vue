<template>
  <div class="settings-container h-full flex">
    <!-- 设置侧边栏 -->
    <div class="settings-sidebar bg-white border-r">
      <div class="p-4 border-b">
        <h2 class="text-lg font-semibold">系统设置</h2>
      </div>
      <nav class="p-3">
        <router-link
          to="/settings/ai"
          class="settings-nav-item"
          :class="{ active: $route.path === '/settings/ai' }"
        >
          <el-icon><Monitor /></el-icon>
          AI 模型配置
        </router-link>

        <router-link
          to="/settings/datasource"
          class="settings-nav-item"
          :class="{ active: $route.path.startsWith('/settings/datasource') }"
        >
          <el-icon><Coin /></el-icon>
          数据源管理
        </router-link>

        <router-link
          to="/settings/knowledge"
          class="settings-nav-item"
          :class="{ active: $route.path === '/settings/knowledge' }"
        >
          <el-icon><FolderOpened /></el-icon>
          知识库配置
        </router-link>
      </nav>
    </div>

    <!-- 设置内容区 -->
    <div class="settings-content flex-1 overflow-auto bg-gray-50 p-6">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Monitor, Coin, FolderOpened } from '@element-plus/icons-vue'
</script>

<style scoped>
.settings-sidebar {
  width: 200px;
  min-width: 200px;
}

.settings-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  color: #4b5563;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: 4px;
  text-decoration: none;
}

.settings-nav-item:hover {
  background: #e5e7eb;
}

.settings-nav-item.active {
  background: #dbeafe;
  color: #1d4ed8;
}
</style>