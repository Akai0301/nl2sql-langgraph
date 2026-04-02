#!/usr/bin/env node
/**
 * PostToolUse Hook - Claude Code 写入/编辑文件后触发
 * 功能: 记录 AI 操作到 ai-sessions/{用户名}-ai-session-{主机名}.json
 *       并检测配置同步需求
 *
 * 文件命名：{sanitized_username}-ai-session-{sanitized_hostname}.json
 * 存储位置：{项目根目录}/ai-sessions/（提交到 git，多人可见）
 *
 * 适配项目: nl2sql-langgraph (LangGraph 梭子形流水线)
 */

const fs   = require('fs');
const path = require('path');
const os   = require('os');

// ─── 工具函数 ─────────────────────────────────────────────────────────────────
/** 清理字符串：只保留字母数字、下划线、连字符，小写，最长 30 字符 */
const sanitize = s =>
  (s || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase().slice(0, 30);

/** 计算当前开发者的 session 文件路径 */
function resolveSessionFile(projectRoot) {
  const username = sanitize(os.userInfo().username);
  const hostname = sanitize(os.hostname());
  const filename = `${username}-ai-session-${hostname}.json`;
  return {
    username,
    hostname,
    filename,
    dir:  path.join(projectRoot, 'ai-sessions'),
    file: path.join(projectRoot, 'ai-sessions', filename),
  };
}

// ─── 配置同步检测规则 ─────────────────────────────────────────────────────────
/**
 * 检测文件变更是否需要同步配置
 * 返回: { needsSync: boolean, syncTargets: string[], message: string }
 */
function checkConfigSync(normalizedFilePath) {
  const syncRules = [
    // LangGraph 核心文件
    {
      pattern: /^app\/state\.py$/,
      targets: ['CLAUDE.md (状态定义)', 'langgraph-flow/SKILL.md'],
      message: 'State 定义变更，需同步更新状态文档'
    },
    {
      pattern: /^app\/nodes\.py$/,
      targets: ['CLAUDE.md (节点列表)', 'langgraph-flow/SKILL.md'],
      message: '节点函数变更，需同步更新节点文档'
    },
    {
      pattern: /^app\/graph_builder\.py$/,
      targets: ['CLAUDE.md (流程图)', 'langgraph-flow/SKILL.md'],
      message: '图构建变更，需同步更新流程文档'
    },
    {
      pattern: /^app\/tools\.py$/,
      targets: ['CLAUDE.md (工具函数)', 'project-navigator/SKILL.md'],
      message: '工具函数变更，需同步更新工具列表'
    },
    {
      pattern: /^app\/streaming\.py$/,
      targets: ['CLAUDE.md (SSE 接口)', 'websocket-sse/SKILL.md'],
      message: '流式接口变更，需同步更新 SSE 文档'
    },
    // 数据库相关
    {
      pattern: /^db\/.*\.sql$/,
      targets: ['CLAUDE.md (数据库表)', 'database-ops/SKILL.md'],
      message: '数据库脚本变更，需同步更新表结构文档'
    },
    {
      pattern: /^app\/mysql_tools\.py$/,
      targets: ['CLAUDE.md (MySQL 工具)', 'database-ops/SKILL.md'],
      message: 'MySQL 工具变更，需同步更新数据库文档'
    },
    // 前端相关
    {
      pattern: /^frontend\/src\/stores\/.*\.ts$/,
      targets: ['CLAUDE.md (状态管理)', 'store-pc/SKILL.md'],
      message: 'Pinia Store 变更，需同步更新状态管理文档'
    },
    {
      pattern: /^frontend\/src\/api\/.*\.ts$/,
      targets: ['CLAUDE.md (API 调用)', 'http-client/SKILL.md'],
      message: 'API 调用层变更，需同步更新 HTTP 客户端文档'
    },
    {
      pattern: /^frontend\/src\/views\/.*\.vue$/,
      targets: ['CLAUDE.md (前端组件)', 'ui-pc/SKILL.md'],
      message: '前端组件变更，需同步更新组件文档'
    },
    // 后端 API
    {
      pattern: /^app\/.*_routes\.py$/,
      targets: ['api-doc-sync/references/', 'CLAUDE.md (API 列表)'],
      message: 'API 路由变更，需同步生成接口文档'
    },
    {
      pattern: /^app\/main\.py$/,
      targets: ['CLAUDE.md (应用入口)', 'api-doc-sync/references/'],
      message: '应用入口变更，需检查路由配置'
    }
  ];

  for (const rule of syncRules) {
    if (rule.pattern.test(normalizedFilePath)) {
      return {
        needsSync: true,
        syncTargets: rule.targets,
        message: rule.message
      };
    }
  }

  return { needsSync: false, syncTargets: [], message: '' };
}

// ─── API 变更检测（接口文档同步提醒）─────────────────────────────────────
/**
 * 检测是否修改了后端 API 文件（app/*.py）
 * 若是，通过 systemMessage 提醒同步接口文档
 */
function checkApiChange(normalizedFilePath) {
  // 检测 app 目录下的 Python 文件（后端 API 相关）
  return /^app\/.*\.py$/.test(normalizedFilePath);
}

// ─── 读取 stdin ───────────────────────────────────────────────────────────────
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

const toolName  = input.tool_name;
const toolInput = input.tool_input || {};

// 追踪 Write、Edit 和 NotebookEdit 工具
if (!['Write', 'Edit', 'NotebookEdit'].includes(toolName)) {
  process.exit(0);
}

// NotebookEdit 使用 notebook_path，Write/Edit 使用 file_path
const filePath = toolInput.file_path || toolInput.notebook_path || '';
if (!filePath) {
  process.exit(0);
}

// 标准化路径（正斜杠）
const normalizedPath = filePath.replace(/\\/g, '/');

// 排除不需要追踪的路径
const excludePatterns = [
  /\/\.claude\//,
  /\/\.git\//,
  /\/ai-sessions\/[^/]+-ai-session-[^/]+\.json$/,  // 只排除 session JSON 文件自身
  /\/node_modules\//,
  /\/venv\//,
  /\/\.venv\//,
  /\/env\//,
  /\/ENV\//,
  /\/dist\//,
  /\/build\//,
  /\/__pycache__\//,
  /\.py[cod]$/,
  /\.log$/,
  /\.db$/,
  /\.sqlite3?$/,
  /\.env(\.|$)/,
];

if (excludePatterns.some(p => p.test(normalizedPath))) {
  process.exit(0);
}

// ─── 定位 session 文件 ───────────────────────────────────────────────────────
const projectRoot = process.cwd();
const { username, hostname, dir, file: sessionFile } = resolveSessionFile(projectRoot);

// 确保 ai-sessions/ 目录存在
try {
  fs.mkdirSync(dir, { recursive: true });
} catch {
  // 目录已存在，忽略
}

// ─── 读取或初始化 session ────────────────────────────────────────────────────
let session = {
  developer:   username,
  hostname:    hostname,
  model:       process.env.ANTHROPIC_DEFAULT_SONNET_MODEL || 'claude-code',
  firstSeen:   new Date().toISOString(),
  lastUpdated: new Date().toISOString(),
  stats: {
    totalOperations:   0,
    totalFilesEdited:  0,
    totalAiLines:      0,
    totalCommits:      0,
  },
  pendingFiles: [],  // 已被 Claude 修改但尚未提交的文件
};

try {
  if (fs.existsSync(sessionFile)) {
    const existing = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
    if (existing && existing.developer) {
      session = existing;
      // 确保新字段存在（兼容旧版本）
      session.stats        = session.stats        || { totalOperations: 0, totalFilesEdited: 0, totalAiLines: 0, totalAiLinesDeleted: 0, totalCommits: 0 };
      session.stats.totalAiLinesDeleted = session.stats.totalAiLinesDeleted || 0;
      session.pendingFiles = session.pendingFiles  || session.files || [];
    }
  }
} catch {
  // 读取失败使用默认值
}

// 每次操作时同步最新模型信息（防止切换模型后 session 中的 model 字段过期）
const currentModel = process.env.ANTHROPIC_DEFAULT_SONNET_MODEL;
if (currentModel) {
  session.model = currentModel;
}

// ─── 更新 pendingFiles ───────────────────────────────────────────────────────
const existingIndex = session.pendingFiles.findIndex(f => f.path === normalizedPath);
if (existingIndex >= 0) {
  session.pendingFiles[existingIndex].operations += 1;
  session.pendingFiles[existingIndex].lastTool    = toolName;
  session.pendingFiles[existingIndex].lastModified = new Date().toISOString();
} else {
  session.pendingFiles.push({
    path:         normalizedPath,
    tool:         toolName,
    operations:   1,
    timestamp:    new Date().toISOString(),
    lastModified: new Date().toISOString(),
  });
  session.stats.totalFilesEdited += 1;
}

// 更新累计统计
session.stats.totalOperations += 1;
session.lastUpdated = new Date().toISOString();

// ─── 写入 session 文件 ───────────────────────────────────────────────────────
try {
  fs.writeFileSync(sessionFile, JSON.stringify(session, null, 2), 'utf8');
} catch {
  // 写入失败，静默忽略（不影响主流程）
}

// ─── 配置同步检测 ─────────────────────────────────────────────────────────────
const syncCheck = checkConfigSync(normalizedPath);
const apiChange = checkApiChange(normalizedPath);

// 构建系统消息
const systemMessages = [];

if (syncCheck.needsSync) {
  systemMessages.push(
    `📐 **配置同步提醒**：\`${normalizedPath}\``,
    ``,
    `${syncCheck.message}`,
    ``,
    `需同步的配置：`,
    ...syncCheck.syncTargets.map(t => `  - ${t}`),
    ``,
    `激活方式：告诉我"同步配置" 或 激活 \`knowledge-sync\` Skill`
  );
}

if (apiChange && !syncCheck.needsSync) {
  systemMessages.push(
    `⚡ **后端文件已修改**：\`${normalizedPath}\``,
    ``,
    `API 层发生变更，请同步更新接口文档：`,
    `📄 \`.claude/skills/api-doc-sync/references/\` 下对应的文档文件`,
    ``,
    `激活方式：告诉我"同步接口文档" 或 激活 \`api-doc-sync\` Skill`
  );
}

if (systemMessages.length > 0) {
  const docHint = {
    systemMessage: systemMessages.join('\n')
  };
  console.log(JSON.stringify(docHint));
}

process.exit(0);