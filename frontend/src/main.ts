import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

import App from './App.vue'
import './assets/main.css'

// 路由配置
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'query',
      component: () => import('./views/QueryView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('./views/SettingsView.vue'),
      children: [
        {
          path: '',
          redirect: '/settings/ai',
        },
        {
          path: 'ai',
          name: 'settings-ai',
          component: () => import('./views/settings/AISettings.vue'),
        },
        {
          path: 'datasource',
          name: 'settings-datasource',
          component: () => import('./views/settings/DataSourceSettings.vue'),
        },
        {
          path: 'datasource/:id',
          name: 'datasource-detail',
          component: () => import('./views/settings/DataSourceDetail.vue'),
        },
        {
          path: 'knowledge',
          name: 'settings-knowledge',
          component: () => import('./views/settings/KnowledgeSettings.vue'),
        },
      ],
    },
  ],
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')