---
name: ui-enhancement
description: |
  前端（frontend）现代化 UI 提升指南。基于 Vue 3 + TailwindCSS + Element Plus + ECharts + Vue Flow，
  涵盖设计系统扩展、流畅动效、响应式布局、字体排版、组件美化，打造区别于同质化后台的现代风格界面。

  触发场景：
  - 要求界面更现代化、美观、有设计感
  - 需要给页面添加动效、过渡动画、微交互
  - 要求自适应布局、响应式设计
  - 字体排版优化、字号层次、行距
  - 卡片美化、表格优化、按钮视觉升级
  - 整体风格升级（渐变、阴影、圆角系统）
  - 暗色模式适配增强

  触发词：现代化、美观、动效、动画、微交互、自适应、响应式、字体、排版、渐变、阴影、圆角、卡片美化、视觉升级、UI优化、界面优化、风格优化、玻璃拟态、glassmorphism、设计系统、design token

  注意：Element Plus 基础组件用法 → 使用 ui-pc；路由跳转动效 → 使用 router-pc；状态管理 → 使用 store-pc。

  适用目录：frontend/**
---

# 前端现代化 UI 提升指南（ui-enhancement）

> **适用范围**: `frontend/` 目录下所有页面与组件
> **技术边界**: Vue 3 + TailwindCSS + Element Plus + ECharts + Vue Flow（**项目无 animate.css / gsap**，请使用原生 CSS transition 和 Vue Transition API）

---

## 一、核心设计理念

### 1.1 反同质化原则

大多数后台系统都是"蓝色+白色+方形表格"的同质化风格。以下是差异化方向：

| 维度 | 同质化做法 | 现代化做法 |
|------|----------|----------|
| 间距 | 硬编码 `padding: 20px` | TailwindCSS spacing scale（4px 基准网格） |
| 颜色 | 单一 Element Plus 蓝 | 自定义主题色 + 渐变层 + 语义化颜色 |
| 圆角 | 0 或 4px | 层级圆角系统（小4px / 中8px / 大12px / 超大16px+） |
| 阴影 | 无阴影或 box-shadow 一刀切 | 3层海拔系统（flat / raised / floating） |
| 字体 | 系统默认14px | 中文优化字体栈 + 层次化字号系统 |
| 动效 | 无或生硬 | 物理感弹簧曲线 + 分层时序 |
| 表格 | 默认斑马纹 | 悬浮高亮 + 行内操作显现 |

### 1.2 技术约束（必须遵守）

```
✅ 可用：CSS transition、CSS animation（@keyframes）、Vue <Transition>、@vueuse/core
✅ 可用：TailwindCSS 类名、自定义 CSS 变量
✅ 可用：Element Plus CSS 变量覆盖（--el-xxx）
✅ 可用：backdrop-filter（现代浏览器支持良好）
❌ 不可用：animate.css（项目未安装）
❌ 不可用：gsap（项目未安装）
❌ 不可用：framer-motion（React 库）
```

---

## 二、TailwindCSS 设计系统

### 2.1 扩展 TailwindCSS 配置

**文件路径**: `frontend/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // 间距系统（基于 4px 网格）
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      // 圆角系统
      borderRadius: {
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        '2xl': '24px',
      },
      // 阴影系统
      boxShadow: {
        'sm': '0 1px 4px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
        'md': '0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
        'lg': '0 8px 24px rgba(0, 0, 0, 0.10), 0 4px 8px rgba(0, 0, 0, 0.06)',
        'xl': '0 16px 40px rgba(0, 0, 0, 0.12), 0 8px 16px rgba(0, 0, 0, 0.08)',
        'colored': '0 8px 24px rgba(64, 158, 255, 0.20)',
      },
      // 动效时序
      transitionDuration: {
        'fast': '100ms',
        'normal': '200ms',
        'slow': '350ms',
      },
      // 缓动曲线
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      // 字号系统
      fontSize: {
        'xs': ['11px', { lineHeight: '1.3' }],
        'sm': ['12px', { lineHeight: '1.4' }],
        'base': ['13px', { lineHeight: '1.5' }],
        'md': ['14px', { lineHeight: '1.5' }],
        'lg': ['16px', { lineHeight: '1.5' }],
        'xl': ['18px', { lineHeight: '1.4' }],
        '2xl': ['22px', { lineHeight: '1.3' }],
        '3xl': ['28px', { lineHeight: '1.2' }],
      },
    },
  },
  plugins: [],
}
```

### 2.2 CSS 自定义属性

**文件路径**: `frontend/src/assets/main.css`

```css
:root {
  /* 圆角系统 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* 阴影系统 */
  --shadow-sm: 0 1px 4px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
  --shadow-lg: 0 8px 24px rgba(0,0,0,.10), 0 4px 8px rgba(0,0,0,.06);
  --shadow-colored: 0 8px 24px rgba(64, 158, 255, 0.20);

  /* 背景层次 */
  --content-bg: #f5f7fa;
  --card-bg: #ffffff;
  --divider: #f0f2f5;

  /* 语义化颜色 */
  --color-success-bg: rgba(103, 194, 58, 0.08);
  --color-warning-bg: rgba(230, 162, 60, 0.08);
  --color-danger-bg: rgba(245, 108, 108, 0.08);
  --color-primary-bg: rgba(59, 125, 232, 0.08);
}

html.dark {
  --content-bg: #0f0f0f;
  --card-bg: #1d1e1f;
  --divider: #303030;
  --shadow-sm: 0 1px 4px rgba(0,0,0,.20);
  --shadow-md: 0 4px 12px rgba(0,0,0,.30);
  --shadow-lg: 0 8px 24px rgba(0,0,0,.40);
}
```

---

## 三、字体排版系统

### 3.1 中文优化字体栈

```css
/* frontend/src/assets/main.css */
body {
  font-family:
    "PingFang SC",         /* macOS / iOS 苹方 */
    "Noto Sans SC",        /* Google 思源黑体 */
    "Microsoft YaHei UI",  /* Win10+ 微软雅黑 UI */
    "Microsoft YaHei",     /* Win 7 */
    "Helvetica Neue",
    Arial,
    sans-serif;
  font-size: 13px;
  line-height: 1.5;
  letter-spacing: 0.01em;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

### 3.2 标题层次规范

```vue
<template>
  <!-- 页面主标题 -->
  <h1 class="text-xl font-semibold text-gray-900">查询结果</h1>

  <!-- 区块标题 -->
  <h2 class="text-md font-semibold text-gray-900">历史记录</h2>

  <!-- 辅助说明文字 -->
  <p class="text-sm text-gray-500">输入自然语言问题开始查询</p>

  <!-- 数字突出（统计卡片） -->
  <span class="text-3xl font-bold tabular-nums">12,580</span>
</template>
```

---

## 四、动效体系

### 4.1 Vue Transition 组件增强

```vue
<script setup>
import { ref } from 'vue'

const visible = ref(true)
</script>

<template>
  <!-- 滑动上浮动效 -->
  <Transition name="slide-up">
    <div v-if="visible" class="card">内容</div>
  </Transition>

  <!-- 弹性缩放动效 -->
  <Transition name="scale-spring">
    <div v-if="visible" class="modal">弹窗</div>
  </Transition>
</template>

<style scoped>
/* 滑动上浮 */
.slide-up-enter-active {
  transition: transform 350ms cubic-bezier(0, 0, 0.2, 1),
              opacity 250ms cubic-bezier(0, 0, 0.2, 1);
}
.slide-up-leave-active {
  transition: transform 200ms cubic-bezier(0.4, 0, 1, 1),
              opacity 150ms cubic-bezier(0.4, 0, 1, 1);
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* 弹性缩放 */
.scale-spring-enter-active {
  transition: transform 350ms cubic-bezier(0.34, 1.56, 0.64, 1),
              opacity 200ms ease;
}
.scale-spring-leave-active {
  transition: transform 180ms cubic-bezier(0.4, 0, 1, 1),
              opacity 150ms ease;
}
.scale-spring-enter-from {
  opacity: 0;
  transform: scale(0.92);
}
.scale-spring-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
```

### 4.2 列表交错动效

```vue
<template>
  <TransitionGroup name="slide-up" tag="div" class="grid gap-4">
    <div
      v-for="(item, index) in items"
      :key="item.id"
      :style="{ transitionDelay: `${index * 40}ms` }"
      class="card"
    >
      {{ item.name }}
    </div>
  </TransitionGroup>
</template>
```

### 4.3 @vueuse/core 动效 Hooks

```vue
<script setup>
import { useTransition, TransitionPresets } from '@vueuse/core'
import { ref, onMounted } from 'vue'

// 数字滚动动效
const rawValue = ref(0)
const displayValue = useTransition(rawValue, {
  duration: 800,
  transition: TransitionPresets.easeOutCubic,
})

onMounted(() => {
  rawValue.value = 12580
})
</script>

<template>
  <div class="text-3xl font-bold">{{ Math.round(displayValue) }}</div>
</template>
```

### 4.4 CSS 微交互规范

```vue
<template>
  <!-- 按钮微交互 -->
  <button class="btn-interactive">
    提交查询
  </button>

  <!-- 卡片悬浮效果 -->
  <div class="card-hover">
    统计卡片
  </div>
</template>

<style scoped>
.btn-interactive {
  transition: transform 150ms cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 200ms ease;
}

.btn-interactive:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.25);
}

.btn-interactive:active {
  transform: translateY(0) scale(0.97);
}

.card-hover {
  transition: box-shadow 250ms ease, transform 250ms ease;
}

.card-hover:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
</style>
```

---

## 五、卡片与容器样式

### 5.1 现代卡片系统

```vue
<template>
  <!-- 基础卡片 -->
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
    <div class="flex items-center justify-between mb-4 pb-4 border-b border-gray-100">
      <h3 class="text-md font-semibold">卡片标题</h3>
      <span class="text-sm text-gray-500">更多</span>
    </div>
    <div class="content">
      卡片内容
    </div>
  </div>

  <!-- 悬浮卡片 -->
  <div class="card-hover bg-white rounded-xl shadow-sm p-6 cursor-pointer">
    统计卡片
  </div>

  <!-- 渐变背景卡片 -->
  <div class="rounded-xl p-6 text-white bg-gradient-to-br from-blue-500 to-blue-400">
    <div class="text-3xl font-bold">12,580</div>
    <div class="text-sm opacity-80">总查询数</div>
  </div>
</template>
```

### 5.2 玻璃拟态（适用于浮层）

```vue
<template>
  <div class="glass-panel p-4 rounded-xl">
    浮层内容
  </div>
</template>

<style scoped>
.glass-panel {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(16px) saturate(1.5);
  -webkit-backdrop-filter: blur(16px) saturate(1.5);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}

html.dark .glass-panel {
  background: rgba(20, 20, 20, 0.75);
  border-color: rgba(255, 255, 255, 0.08);
}
</style>
```

---

## 六、表格视觉升级

### 6.1 现代表格样式

```vue
<template>
  <el-table
    :data="tableData"
    class="modern-table"
    :header-cell-style="{ background: 'var(--content-bg)', fontWeight: 600 }"
  >
    <el-table-column prop="name" label="名称" />
    <el-table-column prop="status" label="状态" />
    <el-table-column label="操作" width="150">
      <template #default="scope">
        <div class="row-actions opacity-0 group-hover:opacity-100 transition-opacity">
          <el-button link type="primary">编辑</el-button>
          <el-button link type="danger">删除</el-button>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<style>
.modern-table {
  --el-table-border-color: var(--divider);
  --el-table-row-hover-bg-color: rgba(64, 158, 255, 0.04);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.modern-table th.el-table__cell {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: var(--el-text-color-secondary);
}

.modern-table tr:hover .row-actions {
  opacity: 1;
}
</style>
```

---

## 七、响应式布局规范

### 7.1 流体间距

```vue
<template>
  <!-- 使用 TailwindCSS 响应式类 -->
  <div class="p-4 md:p-6 lg:p-8">
    内容区
  </div>
</template>
```

### 7.2 CSS Grid 卡片网格

```vue
<template>
  <!-- 响应式统计卡片区 -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div v-for="stat in stats" :key="stat.key" class="card-hover bg-white rounded-xl p-6">
      ...
    </div>
  </div>
</template>
```

---

## 八、ECharts 图表美化

### 8.1 图表主题配置

```typescript
// frontend/src/views/components/ChartPanel.vue
const chartOption = {
  // 使用项目配色
  color: ['#3b7de8', '#30b08f', '#f59e0b', '#f59e0b'],

  // 圆角柱状图
  series: [{
    type: 'bar',
    barMaxWidth: 40,
    itemStyle: {
      borderRadius: [4, 4, 0, 0]
    }
  }],

  // 优雅的网格
  grid: {
    top: 40,
    right: 20,
    bottom: 40,
    left: 60,
    containLabel: true
  },

  // 简洁的坐标轴
  xAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#909399' }
  },
  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#f0f2f5' } },
    axisLabel: { color: '#909399' }
  }
}
```

---

## 九、Vue Flow 流程图美化

### 9.1 节点样式

```typescript
// frontend/src/views/components/FlowGraph.vue
const nodeStyles = {
  // 默认节点
  default: {
    background: '#fff',
    border: '1px solid #e4e7ed',
    borderRadius: '8px',
    padding: '12px 20px',
    fontSize: '13px',
  },

  // 运行中节点
  running: {
    background: '#ecf5ff',
    border: '1px solid #3b7de8',
    boxShadow: '0 4px 12px rgba(64, 158, 255, 0.2)',
  },

  // 完成节点
  completed: {
    background: '#f0f9eb',
    border: '1px solid #67c23a',
  },

  // 错误节点
  error: {
    background: '#fef0f0',
    border: '1px solid #f56c6c',
  }
}
```

---

## 十、常见反模式（避免）

| ❌ 反模式 | ✅ 正确做法 |
|---------|---------|
| `transition: all 0.3s` | 指定具体属性：`transition: transform 200ms ease, opacity 150ms ease` |
| `animation-duration: 1s`（太慢） | 遵循时序系统：快=100ms、常规=200ms、慢=350ms |
| 所有卡片 `border-radius: 4px` | 使用圆角层级系统（sm/md/lg/xl） |
| `color: #666` 硬编码 | 使用 `text-gray-500` 或 `var(--el-text-color-secondary)` |
| 颜色不支持暗黑模式 | 所有颜色使用 CSS 变量或 TailwindCSS 类 |
| `padding: 20px` 到处一样 | 内容区使用响应式类 `p-4 md:p-6` |
| 弹窗无出现动效 | 配合 `<Transition name="scale-spring">` |
| 数字直接赋值没有过渡 | 使用 `useTransition` 数字滚动 |

---

## 十一、文件修改速查

| 需求 | 修改文件 |
|------|---------|
| 添加设计令牌变量 | `frontend/tailwind.config.js` |
| 添加 CSS 变量 | `frontend/src/assets/main.css` |
| 覆盖 Element Plus 样式 | 组件内 `<style>` 使用 `:deep()` |
| 业务组件独立样式 | 组件内 `<style scoped>` |