#!/usr/bin/env node
/**
 * reset-session.js - 重置当前开发者的 AI session 追踪记录
 *
 * 只清除 pendingFiles（待提交缓冲），保留累计统计数据（stats）。
 * 适用场景：手动开始新一轮工作追踪，或 pendingFiles 数据混乱时。
 *
 * 用法：node scripts/ai-tracker/reset-session.js [--full]
 *   --full  完全重置，包括统计数据（慎用）
 */

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const { execSync } = require('child_process');

const sanitize = s =>
  (s || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase().slice(0, 30);

const fullReset = process.argv.includes('--full');

let projectRoot;
try {
  projectRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
} catch {
  projectRoot = process.cwd();
}

const username    = sanitize(os.userInfo().username);
const hostname    = sanitize(os.hostname());
const filename    = `${username}-ai-session-${hostname}.json`;
const sessionFile = path.join(projectRoot, 'ai-sessions', filename);

if (!fs.existsSync(sessionFile)) {
  console.log(`⚠ Session 文件不存在：ai-sessions/${filename}`);
  console.log('  请先运行：node scripts/ai-tracker/install.js');
  process.exit(1);
}

try {
  const current = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));

  if (fullReset) {
    // 完全重置
    const freshData = {
      developer:   username,
      hostname:    hostname,
      model:       current.model || 'claude-code',
      firstSeen:   new Date().toISOString(),
      lastUpdated: new Date().toISOString(),
      stats: { totalOperations: 0, totalFilesEdited: 0, totalAiLines: 0, totalAiLinesDeleted: 0, totalCommits: 0 },
      pendingFiles: [],
    };
    fs.writeFileSync(sessionFile, JSON.stringify(freshData, null, 2));
    console.log(`✓ Session 已完全重置（含统计数据）：ai-sessions/${filename}`);
  } else {
    // 只清除 pendingFiles，保留统计
    const pendingCount = (current.pendingFiles || current.files || []).length;
    current.pendingFiles = [];
    delete current.files;
    current.lastUpdated = new Date().toISOString();
    fs.writeFileSync(sessionFile, JSON.stringify(current, null, 2));
    console.log(`✓ pendingFiles 已清除（共 ${pendingCount} 条），统计数据已保留`);
    console.log(`  文件：ai-sessions/${filename}`);
    console.log(`  累计统计：${JSON.stringify(current.stats)}`);
  }
} catch (err) {
  console.error(`✗ 重置失败：${err.message}`);
  process.exit(1);
}
