<template>
  <div class="app-container h-screen flex flex-col">
    <!-- 顶部栏 -->
    <TopBar />

    <!-- 主内容区 -->
    <div class="main-content flex-1 flex overflow-hidden">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import TopBar from '@/views/components/TopBar.vue'
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

.main-content {
  background: #f5f7fa;
}
</style>