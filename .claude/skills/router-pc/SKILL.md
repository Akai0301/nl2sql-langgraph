---
name: router-pc
description: |
  前端（frontend）路由管理指南。本项目为单页应用，路由配置简单。

  触发场景：
  - 理解前端路由结构
  - 添加新页面路由

  触发词：路由、Vue Router、router

  适用目录：frontend/**
---

# 前端路由管理指南

> **适用于**: `frontend/` 目录下的智能问数前端
> **技术栈**: Vue 3.5 + Vue Router 4

---

## 项目路由结构

本项目为单页应用（SPA），路由配置简单：

```typescript
// main.ts
import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import QueryView from './views/QueryView.vue'

const routes = [
  {
    path: '/',
    name: 'Query',
    component: QueryView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.mount('#app')
```

---

## 添加新页面

### 步骤 1：创建页面组件

```vue
<!-- src/views/NewPage.vue -->
<template>
  <div class="new-page">
    <h1>新页面</h1>
  </div>
</template>

<script setup lang="ts">
// 页面逻辑
</script>
```

### 步骤 2：添加路由配置

```typescript
const routes = [
  {
    path: '/',
    name: 'Query',
    component: QueryView
  },
  {
    path: '/new-page',
    name: 'NewPage',
    component: () => import('./views/NewPage.vue')  // 懒加载
  }
]
```

---

## 路由导航

```vue
<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <button @click="navigateTo('/new-page')">跳转</button>
</template>
```

---

## 参考文件

| 用途 | 路径 |
|------|------|
| 入口文件 | `frontend/src/main.ts` |
| 主页面 | `frontend/src/views/QueryView.vue` |