#!/usr/bin/env node
/**
 * install.js - AI 代码追踪系统安装脚本
 *
 * 功能：
 * 1. 创建 ai-sessions/ 目录（提交到仓库，按开发者存储 session 文件）
 * 2. 安装 prepare-commit-msg Git Hook（注入 AI 元数据 + 自动 stage session 文件）
 * 3. 安装 pre-commit Git Hook（自动 stage 当前用户的 session 文件）
 * 4. 初始化当前用户的 session 文件
 * 5. 清理旧版本遗留的 .gitignore 排除项
 *
 * 多人团队：每位开发者克隆后各自运行一次，session 文件按 用户名-主机名 唯一命名
 *
 * 用法：node scripts/ai-tracker/install.js
 */

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const { execSync, spawnSync } = require('child_process');

// ─── 工具函数 ─────────────────────────────────────────────────────────────────
const green  = s => `\x1b[32m${s}\x1b[0m`;
const yellow = s => `\x1b[33m${s}\x1b[0m`;
const red    = s => `\x1b[31m${s}\x1b[0m`;
const bold   = s => `\x1b[1m${s}\x1b[0m`;
const dim    = s => `\x1b[2m${s}\x1b[0m`;

const log = {
  ok:   msg => console.log(`  ${green('✓')} ${msg}`),
  warn: msg => console.log(`  ${yellow('⚠')} ${msg}`),
  err:  msg => console.log(`  ${red('✗')} ${msg}`),
  info: msg => console.log(`  → ${msg}`),
  skip: msg => console.log(`  ${dim('○')} ${msg} (已存在，跳过)`),
};

const sanitize = s =>
  (s || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase().slice(0, 30);

// ─── 环境信息 ─────────────────────────────────────────────────────────────────
let projectRoot;
try {
  projectRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
} catch {
  console.error(red('错误：必须在 git 仓库中运行此脚本'));
  process.exit(1);
}

const username     = sanitize(os.userInfo().username);
const hostname     = sanitize(os.hostname());
const sessionFile  = `${username}-ai-session-${hostname}.json`;
const sessionDir   = path.join(projectRoot, 'ai-sessions');
const sessionPath  = path.join(sessionDir, sessionFile);
const gitHooksDir  = path.join(projectRoot, '.git', 'hooks');
const claudeHooks  = path.join(projectRoot, '.claude', 'hooks');
const relPrepare   = path.relative(projectRoot, path.join(claudeHooks, 'prepare-commit-msg.js'))
                      .replace(/\\/g, '/');

console.log('');
console.log(bold('═══════════════════════════════════════════════'));
console.log(bold('   AI 代码追踪系统 - 安装向导'));
console.log(bold('═══════════════════════════════════════════════'));
console.log(`  开发者：${bold(username)}  主机：${bold(hostname)}`);
console.log(`  Session 文件：${bold('ai-sessions/' + sessionFile)}`);
console.log('');

// ─── Step 1: 验证依赖 Hook 文件 ──────────────────────────────────────────────
console.log(bold('Step 1: 验证 .claude/hooks/ 文件'));

for (const f of ['post-tool-use.js', 'prepare-commit-msg.js']) {
  const p = path.join(claudeHooks, f);
  if (fs.existsSync(p)) {
    log.ok(f);
  } else {
    log.err(`${f} 不存在（${p}）`);
    process.exit(1);
  }
}

// ─── Step 2: 创建 ai-sessions/ 目录 ──────────────────────────────────────────
console.log('');
console.log(bold('Step 2: 创建 ai-sessions/ 目录'));

try {
  fs.mkdirSync(sessionDir, { recursive: true });
  log.ok('ai-sessions/ 目录已就绪');
} catch (err) {
  log.err(`创建目录失败: ${err.message}`);
  process.exit(1);
}

// 添加 .gitkeep 确保空目录也能提交
const gitkeep = path.join(sessionDir, '.gitkeep');
if (!fs.existsSync(gitkeep)) {
  fs.writeFileSync(gitkeep, '');
  log.ok('ai-sessions/.gitkeep 已创建');
}

// ─── Step 3: 初始化当前用户 Session 文件 ─────────────────────────────────────
console.log('');
console.log(bold(`Step 3: 初始化 Session 文件 (${sessionFile})`));

if (fs.existsSync(sessionPath)) {
  log.skip(sessionFile);
} else {
  // 尝试迁移旧版 .claude/ai-session.json
  let migratedStats = null;
  const oldFile = path.join(projectRoot, '.claude', 'ai-session.json');
  if (fs.existsSync(oldFile)) {
    try {
      const old = JSON.parse(fs.readFileSync(oldFile, 'utf8'));
      migratedStats = old.stats || null;
      log.info('检测到旧版 .claude/ai-session.json，已迁移统计数据');
    } catch {
      // 迁移失败不影响继续
    }
  }

  const initData = {
    developer:   username,
    hostname:    hostname,
    model:       process.env.ANTHROPIC_DEFAULT_SONNET_MODEL || 'claude-code',
    firstSeen:   new Date().toISOString(),
    lastUpdated: new Date().toISOString(),
    stats: migratedStats || {
      totalOperations:  0,
      totalFilesEdited: 0,
      totalAiLines:     0,
      totalCommits:     0,
    },
    pendingFiles: [],
  };

  try {
    fs.writeFileSync(sessionPath, JSON.stringify(initData, null, 2));
    log.ok(`${sessionFile} 已创建`);
  } catch (err) {
    log.warn(`创建 session 文件失败: ${err.message}`);
  }
}

// ─── Step 4: 安装 prepare-commit-msg Git Hook ────────────────────────────────
console.log('');
console.log(bold('Step 4: 安装 Git Hook — prepare-commit-msg'));

const prepareContent = `#!/bin/sh
# prepare-commit-msg — AI 代码追踪系统 (自动生成，勿手动修改)
# 安装时间: ${new Date().toISOString()}
COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SCRIPT="$PROJECT_ROOT/${relPrepare}"
if [ -f "$HOOK_SCRIPT" ]; then
  node "$HOOK_SCRIPT" "$COMMIT_MSG_FILE" "$COMMIT_SOURCE"
fi
exit 0
`;
installHook(path.join(gitHooksDir, 'prepare-commit-msg'), prepareContent, 'prepare-commit-msg');

// ─── Step 5: 安装 pre-commit Git Hook（自动 stage session 文件）────────────
console.log('');
console.log(bold('Step 5: 安装 Git Hook — pre-commit (自动 stage session 文件)'));

// 用 Node 内联脚本动态计算 session 文件名，避免硬编码
const preCommitContent = `#!/bin/sh
# pre-commit — AI 代码追踪系统 (自动生成，勿手动修改)
# 安装时间: ${new Date().toISOString()}
# 功能：将当前开发者的 AI session 文件自动加入暂存区

SESSION_FILE=$(node -e "
const os=require('os');
const s=x=>(x||'unknown').replace(/[^a-zA-Z0-9_-]/g,'_').toLowerCase().slice(0,30);
console.log('ai-sessions/'+s(os.userInfo().username)+'-ai-session-'+s(os.hostname())+'.json');
" 2>/dev/null)

if [ -n "$SESSION_FILE" ] && [ -f "$SESSION_FILE" ]; then
  git add "$SESSION_FILE" 2>/dev/null || true
fi

exit 0
`;
installHook(path.join(gitHooksDir, 'pre-commit'), preCommitContent, 'pre-commit');

// ─── Step 6: 清理旧版 .gitignore 排除项 ──────────────────────────────────────
console.log('');
console.log(bold('Step 6: 清理旧版配置'));

const gitignorePath = path.join(projectRoot, '.gitignore');
try {
  if (fs.existsSync(gitignorePath)) {
    let content = fs.readFileSync(gitignorePath, 'utf8');
    const OLD_PATTERN = '.claude/ai-session.json';
    if (content.includes(OLD_PATTERN)) {
      // 移除旧条目（含前后注释行）
      content = content
        .split('\n')
        .filter(line => !line.includes(OLD_PATTERN) && !line.includes('AI 代码追踪系统 - 会话文件'))
        .join('\n');
      fs.writeFileSync(gitignorePath, content);
      log.ok('.gitignore 旧条目已清理');
    } else {
      log.skip('.gitignore 无需清理');
    }
  }
} catch (err) {
  log.warn(`清理 .gitignore 失败: ${err.message}`);
}

// 清理旧版 .git/info/exclude
const excludePath = path.join(projectRoot, '.git', 'info', 'exclude');
try {
  if (fs.existsSync(excludePath)) {
    let content = fs.readFileSync(excludePath, 'utf8');
    if (content.includes('.claude/ai-session.json')) {
      content = content
        .split('\n')
        .filter(l => !l.includes('.claude/ai-session.json') && !l.includes('AI 代码追踪系统 - 本地会话'))
        .join('\n');
      fs.writeFileSync(excludePath, content);
      log.ok('.git/info/exclude 旧条目已清理');
    } else {
      log.skip('.git/info/exclude 无需清理');
    }
  }
} catch {
  // 非致命
}

// ─── Step 7: 将 ai-sessions/ 加入 git 追踪 ───────────────────────────────────
console.log('');
console.log(bold('Step 7: 将 ai-sessions/ 加入 git 追踪'));

try {
  execSync(`git add ai-sessions/`, { cwd: projectRoot, stdio: 'pipe' });
  log.ok('ai-sessions/ 已加入 git 暂存区');
} catch (err) {
  log.warn(`git add ai-sessions/ 失败: ${err.message}`);
}

// ─── 完成 ─────────────────────────────────────────────────────────────────────
console.log('');
console.log(bold('═══════════════════════════════════════════════'));
console.log(green(bold('  ✓ 安装完成！')));
console.log(bold('═══════════════════════════════════════════════'));
console.log('');
console.log(bold('Session 文件路径：'));
console.log(`  ${green('ai-sessions/' + sessionFile)}`);
console.log(`  命名规则：{用户名}-ai-session-{主机名}.json`);
console.log(`  存储策略：提交到仓库，多人各自一份，无冲突`);
console.log('');
console.log(bold('工作流程：'));
console.log('  1. Claude Code 写/改文件 → PostToolUse Hook 记录到 session 文件');
console.log('  2. git commit → pre-commit 自动 stage session 文件');
console.log('                → prepare-commit-msg 注入 AI 元数据 trailers');
console.log('  3. session 文件随代码一起提交，团队可见');
console.log('');
console.log(bold('常用命令：'));
console.log('  查看报告    python scripts/ai-tracker/report.py');
console.log('  按月统计    python scripts/ai-tracker/report.py --since 2026-01-01');
console.log('  查看单人    python scripts/ai-tracker/report.py --developer zhangsan');
console.log('  查看单人    python scripts/ai-tracker/report.py --author zhangsan  # --author 是别名');
console.log('  JSON 输出   python scripts/ai-tracker/report.py --format json');
console.log('  重置记录    node scripts/ai-tracker/reset-session.js');
console.log('');
console.log(bold('多人团队：'));
console.log('  每位成员克隆后执行：node scripts/ai-tracker/install.js');
console.log('  各自的 session 文件名唯一，不会产生冲突。');
console.log('');

// ─── 辅助函数 ─────────────────────────────────────────────────────────────────
function installHook(hookPath, content, name) {
  try {
    if (fs.existsSync(hookPath)) {
      const existing = fs.readFileSync(hookPath, 'utf8');
      if (existing.includes('AI 代码追踪系统')) {
        log.skip(`${name} git hook`);
        return;
      }
      fs.writeFileSync(hookPath + '.backup', existing);
      log.warn(`已备份原有 ${name} hook → ${hookPath}.backup`);
    }
    fs.writeFileSync(hookPath, content, { mode: 0o755 });
    log.ok(`${name} git hook 已安装`);
  } catch (err) {
    log.err(`安装 ${name} hook 失败: ${err.message}`);
    process.exit(1);
  }
}
