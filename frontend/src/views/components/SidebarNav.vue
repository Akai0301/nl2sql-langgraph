<template>
  <div class="sidebar-nav h-full flex flex-col bg-gray-900 text-white">
    <!-- Logo -->
    <div class="p-4 border-b border-gray-700">
      <div class="flex items-center justify-center">
        <el-icon :size="24" class="text-blue-400"><DataAnalysis /></el-icon>
      </div>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 p-3">
      <router-link
        to="/"
        class="nav-item"
        :class="{ active: $route.path === '/' }"
      >
        <el-icon><ChatLineRound /></el-icon>
        <span>智能问数</span>
      </router-link>

      <router-link
        to="/settings"
        class="nav-item"
        :class="{ active: $route.path.startsWith('/settings') }"
      >
        <el-icon><Setting /></el-icon>
        <span>系统设置</span>
      </router-link>
    </nav>

    <!-- 底部信息 -->
    <div class="p-3 text-center text-xs text-gray-500">
      v0.2.0
    </div>
  </div>
</template>

<script setup lang="ts">
import { DataAnalysis, ChatLineRound, Setting } from '@element-plus/icons-vue'
</script>

<style scoped>
.sidebar-nav {
  width: 60px;
  min-width: 60px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 8px;
  text-decoration: none;
}

.nav-item:hover {
  background: #374151;
  color: white;
}

.nav-item.active {
  background: #3b82f6;
  color: white;
}

.nav-item .el-icon {
  font-size: 20px;
  margin-bottom: 4px;
}
</style>