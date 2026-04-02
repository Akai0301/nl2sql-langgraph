<template>
  <div class="app-container h-screen flex">
    <!-- 左侧主导航（紧凑图标模式） -->
    <SidebarNav v-if="!isQueryPage" />

    <!-- 路由视图 -->
    <div class="main-content flex-1 flex flex-col overflow-hidden">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SidebarNav from '@/views/components/SidebarNav.vue'

const route = useRoute()
const isQueryPage = computed(() => route.path === '/')
</script>

<style>
/* Global styles */
* {
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}

.app-container {
  background: #f5f7fa;
}
</style>