# 用户偏好记录

> **用途**：记录开发者的个人偏好和习惯，帮助 AI 更好地适配开发风格。
> **更新方式**：手动编辑，或通过 `/remember` 命令记录。

---

## 开发风格

### 代码风格
- 偏好简洁代码，避免过度工程
- 优先使用 async/await 而非回调
- 函数优先使用表达式（const fn = () => {}）

### 注释风格
- 不添加过多注释，代码应自解释
- 复杂逻辑才需要注释说明
- 使用中文注释

---

## 命名习惯

### 文件命名
- Python 文件使用下划线分隔：`node_functions.py`
- Vue 组件使用 PascalCase：`QueryInput.vue`
- TypeScript 文件使用 camelCase：`queryStore.ts`

### 变量命名
- 变量使用 camelCase
- 常量使用 UPPER_SNAKE_CASE
- 类名使用 PascalCase
- 私有变量使用下划线前缀

---

## 禁止事项

### 代码层面
- 不要使用过时的语法
- 不要添加未使用的导入
- 不要留下 console.log/print 调试语句

### 工程层面
- 不要过度抽象
- 不要过早优化
- 不要添加不必要的类型注解

---

## 偏好设置

### 响应风格
- 简洁明了，不要过多解释
- 直接给出解决方案
- 遇到问题主动提出

### 沟通方式
- 使用中文
- 技术术语保留英文
- 代码示例优先于文字描述

---

## 项目环境配置（🔴 必须遵守）

### 本地域名
- **后端地址**：http://nl2sql.local:8000（已在 hosts 文件配置 127.0.0.1 nl2sql.local）
- 所有 API 请求、测试、前端代理都应使用此域名

### Python 虚拟环境
- **虚拟环境路径**：`D:\01_AlCoding_Test\nl2sql-langgraph\venv`（项目根目录）
- **项目路径**：`D:\01_AlCoding_Test\nl2sql-langgraph`
- **启动后端命令**：
  ```bash
  cd d:/01_AlCoding_Test/nl2sql-langgraph && venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
  ```
- ⚠️ 必须从项目根目录启动，确保 `.env` 文件路径正确解析
- ⚠️ 不要直接调用 `uvicorn`，必须使用虚拟环境的 Python

### 启动服务检查清单
1. 后端启动前确认当前目录是 `d:/01_AlCoding_Test/nl2sql-langgraph`
2. 后端启动使用完整路径的虚拟环境 Python
3. 前端开发服务器端口：`3008`（vite.config.ts 已配置 strictPort: true）
4. 前端开发服务器代理目标应为 `http://nl2sql.local:8000`
5. 测试 API 时使用 `http://nl2sql.local:8000` 而非 `localhost:8000`