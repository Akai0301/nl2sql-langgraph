#!/usr/bin/env node
/**
 * prepare-commit-msg.js
 * 由 git prepare-commit-msg hook 调用
 *
 * 功能：
 * 1. 定位当前开发者的 ai-sessions/{user}-ai-session-{host}.json
 * 2. 与暂存区文件取交集，用 git diff --cached --numstat 获取精确行数
 * 3. 向提交信息注入 AI 元数据 trailers
 * 4. 更新 session 累计统计，清除已提交的 pendingFiles
 * 5. 自动将更新后的 session 文件加入暂存区（随本次提交一起入库）
 *
 * 注入格式（Git Trailer 标准）：
 *   AI-Generated: true
 *   AI-Tool: claude-code
 *   AI-Model: claude-sonnet-4-6-cc
 *   AI-Lines: 150
 *   AI-Total-Lines: 200
 *   AI-Files: 3
 *   AI-File-List: service/user_service.py, controller/user_controller.py
 *   AI-Developer: zhangsan@DESKTOP-ABC
 *
 * 用法：node .claude/hooks/prepare-commit-msg.js <COMMIT_MSG_FILE> [source]
 */

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const { execSync } = require('child_process');

// ─── 工具函数（与 post-tool-use.js 保持一致）────────────────────────────────
const sanitize = s =>
  (s || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase().slice(0, 30);

function resolveSessionFile(projectRoot) {
  const username = sanitize(os.userInfo().username);
  const hostname = sanitize(os.hostname());
  const filename = `${username}-ai-session-${hostname}.json`;
  return {
    username,
    hostname,
    relPath: `ai-sessions/${filename}`,                          // 用于 git add
    file:    path.join(projectRoot, 'ai-sessions', filename),
  };
}

// ─── 参数处理 ─────────────────────────────────────────────────────────────────
const commitMsgFile = process.argv[2];
const commitSource  = process.argv[3] || '';

// 跳过合并、squash 等特殊提交
if (['merge', 'squash'].includes(commitSource) || !commitMsgFile) {
  process.exit(0);
}

// ─── 1. 获取项目根目录 ────────────────────────────────────────────────────────
const projectRoot = (() => {
  try {
    return execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
  } catch {
    return process.cwd();
  }
})();

// ─── 2. 读取 session 文件 ─────────────────────────────────────────────────────
const { username, hostname, relPath: sessionRelPath, file: sessionFile } =
  resolveSessionFile(projectRoot);

let session = null;
try {
  if (fs.existsSync(sessionFile)) {
    session = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
  }
} catch {
  process.exit(0);
}

// pendingFiles 兼容旧字段名 files；同时过滤超过 14 天的过期条目，防止废弃记录污染 Trailer
const STALE_TTL_MS = 14 * 24 * 60 * 60 * 1000;
const nowMs = Date.now();
const allPendingFiles = session?.pendingFiles || session?.files || [];
const pendingFiles = allPendingFiles.filter(f => {
  const ts = new Date(f.lastModified || f.timestamp || 0).getTime();
  // 无时间戳的旧格式条目保留（向后兼容），有时间戳的超期条目清除
  return !ts || (nowMs - ts) < STALE_TTL_MS;
});

if (!session || pendingFiles.length === 0) {
  // 无 pending 文件时也需要更新统计并 stage session
  stageSessionFileAndExit(sessionFile, sessionRelPath, projectRoot);
}

// ─── 3. 获取暂存区文件列表 ────────────────────────────────────────────────────
let stagedFiles = [];
try {
  const output = execSync('git diff --cached --name-only', { encoding: 'utf8' });
  stagedFiles = output.trim().split('\n').filter(Boolean).map(f => f.replace(/\\/g, '/'));
} catch {
  process.exit(0);
}

if (stagedFiles.length === 0) {
  process.exit(0);
}

// ─── 4. 匹配 AI 追踪文件 ──────────────────────────────────────────────────────
const matchFile = (sessionPath, stagedPath) => {
  const sp = sessionPath.replace(/\\/g, '/');
  const st = stagedPath.replace(/\\/g, '/');
  return sp === st || sp.endsWith('/' + st) || st.endsWith('/' + sp) || sp.endsWith(st);
};

const aiMatchedFiles = stagedFiles.filter(sf =>
  pendingFiles.some(f => matchFile(f.path, sf))
);

if (aiMatchedFiles.length === 0) {
  stageSessionFileAndExit(sessionFile, sessionRelPath, projectRoot);
}

// ─── 5. 精确统计行数（git diff --cached --numstat）────────────────────────────
let aiLinesAdded      = 0;
let aiLinesDeleted    = 0;
let totalLinesAdded   = 0;
let totalLinesDeleted = 0;

try {
  const numstatOutput = execSync('git diff --cached --numstat', { encoding: 'utf8' });
  for (const line of numstatOutput.trim().split('\n').filter(Boolean)) {
    const parts   = line.split('\t');
    const added   = parseInt(parts[0], 10);
    const deleted = parseInt(parts[1], 10);
    const fPath   = (parts[2] || '').replace(/\\/g, '/');
    if (!isNaN(added)) {
      totalLinesAdded += added;
      if (aiMatchedFiles.some(sf => sf === fPath || fPath.endsWith(sf) || sf.endsWith(fPath))) {
        aiLinesAdded += added;
      }
    }
    if (!isNaN(deleted)) {
      totalLinesDeleted += deleted;
      if (aiMatchedFiles.some(sf => sf === fPath || fPath.endsWith(sf) || sf.endsWith(fPath))) {
        aiLinesDeleted += deleted;
      }
    }
  }
} catch {
  aiLinesAdded = aiLinesDeleted = totalLinesAdded = totalLinesDeleted = -1;
}

// ─── 6. 读取并校验原始提交信息 ────────────────────────────────────────────────
let commitMsg = '';
try {
  commitMsg = fs.readFileSync(commitMsgFile, 'utf8');
} catch {
  process.exit(0);
}

if (commitMsg.includes('AI-Generated:')) {
  process.exit(0);  // 避免 amend 时重复注入
}

// ─── 7. 构建 AI 元数据 trailers ───────────────────────────────────────────────
const model = (session.model || process.env.ANTHROPIC_DEFAULT_SONNET_MODEL || 'claude-code')
  .replace(/-cc$/, '');  // 去掉内部后缀，对外更简洁

const shortList = aiMatchedFiles
  .slice(0, 5)
  .map(f => { const p = f.split('/'); return p.length > 2 ? p.slice(-2).join('/') : f; })
  .join(', ');
const extra = aiMatchedFiles.length > 5 ? ` (+${aiMatchedFiles.length - 5} more)` : '';

const trailers = [
  `AI-Generated: true`,
  `AI-Tool: claude-code`,
  `AI-Model: ${model}`,
  ...(aiLinesAdded >= 0 ? [
    `AI-Lines: ${aiLinesAdded}`,
    `AI-Lines-Deleted: ${aiLinesDeleted}`,
    `AI-Total-Lines: ${totalLinesAdded}`,
    `AI-Total-Lines-Deleted: ${totalLinesDeleted}`,
  ] : []),
  `AI-Files: ${aiMatchedFiles.length}`,
  `AI-File-List: ${shortList}${extra}`,
  `AI-Developer: ${username}@${hostname}`,
].join('\n');

// 必须用 \n\n 与 subject 分隔，确保 trailers 进入 git body 而非 subject 段落
try {
  fs.writeFileSync(commitMsgFile, commitMsg.trimEnd() + '\n\n' + trailers + '\n', 'utf8');
} catch {
  // 写入失败静默忽略
}

// ─── 8. 更新 session：移除已提交的 pendingFiles（含过期条目），累加统计 ─────────
try {
  // 从 allPendingFiles 中同时过滤：已提交的文件 + TTL 过期条目
  session.pendingFiles = allPendingFiles
    .filter(f => {
      const ts = new Date(f.lastModified || f.timestamp || 0).getTime();
      return !ts || (nowMs - ts) < STALE_TTL_MS;
    })
    .filter(f => !aiMatchedFiles.some(sf => matchFile(f.path, sf)));
  // 删除旧字段名（如果存在）
  delete session.files;

  session.stats = session.stats || { totalOperations: 0, totalFilesEdited: 0, totalAiLines: 0, totalAiLinesDeleted: 0, totalCommits: 0 };
  session.stats.totalCommits        += 1;
  session.stats.totalAiLines        += Math.max(0, aiLinesAdded);
  session.stats.totalAiLinesDeleted  = (session.stats.totalAiLinesDeleted || 0) + Math.max(0, aiLinesDeleted);
  session.lastUpdated                = new Date().toISOString();

  fs.writeFileSync(sessionFile, JSON.stringify(session, null, 2), 'utf8');
} catch {
  // 更新失败静默忽略
}

// ─── 9. 自动将 session 文件加入暂存区 ─────────────────────────────────────────
stageSessionFileAndExit(sessionFile, sessionRelPath, projectRoot);

// ─── 工具函数 ─────────────────────────────────────────────────────────────────
function stageSessionFileAndExit(file, relPath, root) {
  try {
    if (fs.existsSync(file)) {
      execSync(`git add "${relPath}"`, { cwd: root, stdio: 'pipe' });
    }
  } catch {
    // stage 失败不影响主流程
  }
  process.exit(0);
}
