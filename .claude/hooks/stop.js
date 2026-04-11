#!/usr/bin/env node
/**
 * Stop Hook - Claude 回话结束时触发
 * 功能: nul 文件清理 + 完成音效
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

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

// 清理可能误创建的 nul 文件（Windows 下 > nul 可能创建该文件）
// nul 文件由 Bash `> nul` 命令产生，通常只在浅层目录，深度限制为 2
const SKIP_DIRS = new Set(['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.mypy_cache', '.pytest_cache']);
const findAndDeleteNul = (dir, depth = 0) => {
  if (depth > 2) return;
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isFile() && entry.name === 'nul') {
        fs.unlinkSync(fullPath);
        console.error(`已清理: ${fullPath}`);
      } else if (entry.isDirectory() && !entry.name.startsWith('.') && !SKIP_DIRS.has(entry.name)) {
        findAndDeleteNul(fullPath, depth + 1);
      }
    }
  } catch {
    // 访问失败时静默忽略
  }
};
findAndDeleteNul(projectRoot);

// 播放完成音效（可选）- 使用项目根目录
const audioFile = path.join(projectRoot, '.claude', 'audio', 'completed.wav');
try {
  if (fs.existsSync(audioFile)) {
    const platform = process.platform;
    if (platform === 'darwin') {
      execSync(`afplay "${audioFile}"`, { stdio: ['pipe', 'pipe', 'pipe'] });
    } else if (platform === 'win32') {
      execSync(`powershell -c "(New-Object Media.SoundPlayer '${audioFile.replace(/'/g, "''")}').PlaySync()"`, {
        stdio: ['pipe', 'pipe', 'pipe']
      });
    } else if (platform === 'linux') {
      try {
        execSync(`aplay "${audioFile}"`, { stdio: ['pipe', 'pipe', 'pipe'] });
      } catch {
        try {
          execSync(`paplay "${audioFile}"`, { stdio: ['pipe', 'pipe', 'pipe'] });
        } catch {
          // 播放失败，静默忽略
        }
      }
    }
  }
} catch {
  // 播放失败时静默忽略
}

process.exit(0);
