#!/usr/bin/env node
/**
 * UserPromptSubmit Hook - 强制技能评估 (跨平台版本)
 * 功能: 开发场景下，将 Skills 激活率从约 25% 提升到 90% 以上
 *
 * 适配项目: nl2sql-langgraph (智能问数项目)
 * 架构: LangGraph StateGraph (梭子形多 Agent 流水线)
 * 技术栈: FastAPI + Python + psycopg + LangGraph + Vue 3
 */

const fs = require('fs');
const path = require('path');

/**
 * 查找项目根目录（包含 .claude 目录的目录）
 * 支持从任意子目录运行时正确定位
 */
function findProjectRoot(startDir) {
  let dir = startDir;
  while (dir !== path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, '.claude'))) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  // 如果找不到，返回当前目录
  return startDir;
}

const projectRoot = findProjectRoot(process.cwd());

// 从 stdin 读取用户输入
let inputData = '';
try {
  inputData = fs.readFileSync(0, 'utf8');
} catch {
  process.exit(0);
}

let input;
try {
  input = JSON.parse(inputData);
} catch {
  process.exit(0);
}

const prompt = (input.prompt || '').trim();

// 检测是否是恢复会话（防止上下文溢出死循环）
const skipPatterns = [
  'continued from a previous conversation',
  'ran out of context',
  'No code restore',
  'Conversation compacted',
  'commands restored',
  'context window',
  'session is being continued'
];

const isRecoverySession = skipPatterns.some(pattern =>
  prompt.toLowerCase().includes(pattern.toLowerCase())
);

if (isRecoverySession) {
  // 恢复会话，跳过技能评估以防止死循环
  process.exit(0);
}

// 检测是否是斜杠命令
// 规则：以 / 开头，且后面不包含第二个 /（排除 /iot/device 这样的路径）
const isSlashCommand = /^\/[^\/\s]+$/.test(prompt.split(/\s/)[0]);

if (isSlashCommand) {
  // 斜杠命令，跳过技能评估（但 /remember 命令需要激活 lesson-learned）
  const isRememberCommand = prompt.trim().startsWith('/remember');
  if (!isRememberCommand) {
    process.exit(0);
  }
}

// ─── 纠正检测 ────────────────────────────────────────────────────────────────
// 检测用户消息是否包含纠正/反馈关键词，自动触发 lesson-learned skill
const correctionKeywords = [
  '不对', '错了', '不是这样', '应该是', '应该用', '应该这样',
  '你搞错了', '你弄错了', '你写错了', '你理解错了',
  '记住', '记下来', '下次', '以后', '别再',
  '纠正', '更正', '修正', '这不对', '不应该',
  '怎么又', '还是这样', '一直这样', '已经说过',
];
const hasCorrection = correctionKeywords.some(kw => prompt.includes(kw));

// ─── 经验库注入 ──────────────────────────────────────────────────────────────
// 读取项目经验库的规则速查表，注入到每次会话作为背景知识
let lessonsInjection = '';
try {
  const lessonsPath = path.join(projectRoot, '.claude', 'memory', 'lessons.md');
  if (fs.existsSync(lessonsPath)) {
    const lessonsContent = fs.readFileSync(lessonsPath, 'utf8');
    // 提取 RULES_START 和 RULES_END 之间的内容（规则速查表）
    const rulesMatch = lessonsContent.match(/<!-- RULES_START -->([\s\S]*?)<!-- RULES_END -->/);
    if (rulesMatch && rulesMatch[1].trim() && !rulesMatch[1].trim().startsWith('<!--')) {
      lessonsInjection = `\n\n---\n\n## 📚 项目经验库（本项目历史纠正沉淀的规则）\n\n> ⚠️ 以下规则来自真实纠正记录，实现任务时必须遵守：\n\n${rulesMatch[1].trim()}\n\n---`;
    }
  }
} catch {
  // 读取失败静默忽略
}

// 检测是否存在前端目录（frontend/）
const hasFrontend = fs.existsSync(path.join(projectRoot, 'frontend'));

// 联动触发规则（根据项目类型动态生成）
const cascadeRulesSection = hasFrontend ? `**联动触发规则（自动追加，不需要用户明确说"接口文档"或"前台同步"）**：

| 如果匹配到 | 必须同时追加 | 原因 |
|-----------|------------|------|
| \`api-development\` | \`api-doc-sync\` | 接口层变更必须同步文档 |
| \`api-development\` | \`http-client\` | 接口变更需同步前台 API 调用层 |
| \`database-ops\` | \`db-meta-query\` | 数据库操作可能需要查询元数据 |
| \`performance-doctor\` | \`database-ops\` | SQL 性能优化涉及数据库操作 |

示例：用户说"优化慢查询"
- 步骤1评估：匹配 \`performance-doctor\`（性能优化）
- 联动追加：自动追加 \`database-ops\`（数据库操作）
- 步骤2激活：先 Skill(performance-doctor)，再 Skill(database-ops)` : `**联动触发规则（自动追加，不需要用户明确说"接口文档"）**：

| 如果匹配到 | 必须同时追加 | 原因 |
|-----------|------------|------|
| \`api-development\` | \`api-doc-sync\` | 接口层变更必须同步文档 |
| \`database-ops\` | \`db-meta-query\` | 数据库操作可能需要查询元数据 |
| \`performance-doctor\` | \`database-ops\` | SQL 性能优化涉及数据库操作 |

示例：用户说"优化慢查询"
- 步骤1评估：匹配 \`performance-doctor\`（性能优化）
- 联动追加：自动追加 \`database-ops\`（数据库操作）
- 步骤2激活：先 Skill(performance-doctor)，再 Skill(database-ops)`;

// 纠正提示（仅在检测到纠正关键词时追加）
const correctionAlert = hasCorrection
  ? `\n\n> 🔔 **纠正检测**：检测到用户消息包含纠正/反馈关键词。\n> 在技能评估步骤中，**必须额外追加 \`lesson-learned\`** 技能，用于将此纠正结构化记录到项目经验库。`
  : '';

const instructions = `## 强制技能激活流程（必须执行）${correctionAlert}${lessonsInjection}

### 步骤 1 - 评估（必须在响应中明确展示）

针对用户问题，列出匹配的技能：\`技能名: 理由\`，无匹配则写"无匹配技能"

可用技能（nl2sql-langgraph 项目）：
- api-development: API设计/RESTful/接口规范/FastAPI路由/SSE流式接口
- api-doc-sync: 接口文档/API文档/生成文档/同步文档/前端对接/接口说明/接口规格/文档更新/接口变更/对接文档/接口清单
- database-ops: 数据库/SQL/建表/PostgreSQL/MySQL/双数据库/表设计/字段设计
- db-meta-query: 数据库表/表结构/DDL/表字段/列信息/索引/元数据/information_schema
- usql-client: usql/usql连接/usql查询/usql执行/数据库命令行/SQL命令行/usql工具/usql客户端
- utils-toolkit: 工具类/常用工具函数/字符串处理/时间格式化
- bug-detective: Bug/报错/异常/不工作/调试/问题排查/LangGraph调试
- error-handler: 异常处理/全局异常/参数校验/日志/错误码/try-except
- performance-doctor: 性能/慢查询/SQL优化/缓存/N+1问题/索引优化/响应慢
- architecture-design: 架构/模块划分/LangGraph/流程设计/节点设计/技术栈
- code-patterns: 规范/代码风格/命名规范/Git提交规范/代码审查
- project-navigator: 项目结构/文件定位/模块查找/代码导航/app目录/frontend目录
- git-workflow: Git/提交/commit/分支/合并/代码管理
- task-tracker: 任务跟踪/记录进度/继续任务/开发计划
- tech-decision: 技术选型/方案对比/架构决策
- brainstorm: 头脑风暴/创意/方案设计/需求分析
- test-development: 测试/单元测试/pytest/异步测试/接口测试/LangGraph节点测试
- json-serialization: JSON/序列化/反序列化/Pydantic模型/日期格式/类型转换
- websocket-sse: WebSocket/SSE/实时推送/消息通知/流式输出/Server-Sent Events
- openai-interaction: OpenAI/GPT/ChatCompletion/流式输出/streaming/多模态/function calling/tool use/AI对话/模型交互/LLM调用
- dev-docs: 研发文档/交付文档/需求文档/需求分析/架构文档/设计手册/详细设计/测试报告/文档生成
- add-skill: 添加技能/创建技能/新技能/技能开发/写技能
- ui-enhancement: 现代化/美观/动效/动画/微交互/自适应/响应式/UI优化/界面优化/风格优化
- simplify: 代码简化/重构优化/代码质量/代码复用/效率优化/消除冗余/精简代码
- lesson-learned: 纠正/错误记录/记住/经验沉淀/用户反馈/学习记录（检测到纠正关键词时必须追加）
- knowledge-sync: 同步配置/更新文档/记录经验/知识反馈/配置同步（开发完成后同步更新配置）
- ui-pc: UI组件/前端界面/Vue组件/Element Plus/页面布局/前端开发 (frontend/)
- router-pc: 路由/Vue Router/导航守卫/动态路由/路由配置/路由拦截 (frontend/)
- store-pc: 状态管理/Pinia/Vuex/前端存储/本地存储/queryStore (frontend/)
- http-client: Axios/request/axios/请求拦截/响应拦截/API调用/接口调用/前端调接口 (frontend/)

### 步骤 2 - 激活（逐个调用，等待每个完成）

⚠️ **必须逐个调用 Skill() 工具，每次调用后等待返回再调用下一个**
- 有 N 个匹配技能 → 逐个发起 N 次 Skill() 调用（不要并行！）
- 无匹配技能 → 写"无匹配技能"

**调用顺序**：按列出顺序，先调用第一个，等返回后再调用第二个...

### 步骤 3 - 实现

只有在步骤 2 的所有 Skill() 调用完成后，才能开始实现。

---

${cascadeRulesSection}

---

**关键规则（违反将导致任务失败）**：
1. ⛔ 禁止：评估后跳过 Skill() 直接实现
2. ⛔ 禁止：只调用部分技能（必须全部调用）
3. ⛔ 禁止：并行调用多个 Skill()（必须串行，一个一个来）
4. ✅ 正确：评估 → 逐个调用 Skill() → 全部完成后实现

**正确示例**：
用户问："帮我添加一个新的 LangGraph 节点"

匹配技能：
- architecture-design: 涉及 LangGraph 流程设计
- database-ops: 可能需要查询数据库元数据

激活技能：
> Skill(architecture-design)
> Skill(database-ops)

[所有技能激活完成后开始实现...]

**错误示例（禁止）**：
❌ 只调用部分技能
❌ 列出技能但不调用 Skill()
❌ 并行调用（会导致只有一个生效）`;

console.log(instructions);
process.exit(0);
