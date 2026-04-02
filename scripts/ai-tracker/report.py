#!/usr/bin/env python3
"""
AI 代码占比分析报告生成器
==========================
结合 git log AI 元数据 trailers 和 ai-sessions/*.json 文件，
统计项目整体及各开发者的 AI 代码生成占比。

用法：
    python scripts/ai-tracker/report.py                     # 全量分析
    python scripts/ai-tracker/report.py --since 2026-01-01  # 指定起始日期
    python scripts/ai-tracker/report.py --developer zhangsan # 按开发者过滤
    python scripts/ai-tracker/report.py --format json        # JSON 输出
    python scripts/ai-tracker/report.py --top 10             # 最近 N 条 AI 提交
    python scripts/ai-tracker/report.py --sessions-only      # 只看 session 文件统计

Commit Trailer 格式（由 prepare-commit-msg.js 自动注入）：
    AI-Generated: true
    AI-Tool: claude-code
    AI-Model: claude-sonnet-4-6-cc
    AI-Lines: 150
    AI-Total-Lines: 200
    AI-Files: 3
    AI-File-List: service/user_service.py, controller/user_controller.py
    AI-Developer: zhangsan@DESKTOP-ABC
"""

import subprocess
import sys
import json
import argparse
import io
import glob
import os
import re
import urllib.request
from datetime import datetime
from collections import defaultdict
from typing import Optional


# ─── Chart.js 离线兜底 ────────────────────────────────────────────────────────
_CHARTJS_CACHE_PATH = os.path.join(os.path.dirname(__file__), '_chartjs_cache.js')

# CDN 备选列表（按可用性排序）
_CHARTJS_CDNS = [
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
    'https://unpkg.com/chart.js@4.4.0/dist/chart.umd.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
]

# 极简 Chart.js 兼容层（纯 Canvas 实现，CDN 完全不可用时使用）
_CHARTJS_FALLBACK = r"""
/* ── Chart.js 离线简易替代（纯 Canvas，支持 bar / line / doughnut） ── */
(function(global){
'use strict';
const COLORS=['#3b7de8','#10b981','#f59e0b','#8b5cf6','#ef4444','#06b6d4','#ec4899','#84cc16'];
function px(v){return Math.round(v);}
function clr(i){return COLORS[i%COLORS.length];}
function drawRoundRect(ctx,x,y,w,h,r){
  ctx.beginPath();
  ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);ctx.arcTo(x+w,y,x+w,y+r,r);
  ctx.lineTo(x+w,y+h-r);ctx.arcTo(x+w,y+h,x+w-r,y+h,r);
  ctx.lineTo(x+r,y+h);ctx.arcTo(x,y+h,x,y+h-r,r);
  ctx.lineTo(x,y+r);ctx.arcTo(x,y,x+r,y,r);
  ctx.closePath();
}
class Chart{
  constructor(canvas,cfg){
    this.canvas=canvas;this.cfg=cfg;
    this.type=cfg.type||(cfg.data&&cfg.data.datasets&&cfg.data.datasets[0]&&cfg.data.datasets[0].type)||'bar';
    requestAnimationFrame(()=>this.draw());
  }
  draw(){
    const canvas=this.canvas,cfg=this.cfg;
    const dpr=window.devicePixelRatio||1;
    const W=canvas.offsetWidth||canvas.width||300;
    const H=canvas.offsetHeight||canvas.height||200;
    canvas.width=W*dpr;canvas.height=H*dpr;
    canvas.style.width=W+'px';canvas.style.height=H+'px';
    const ctx=canvas.getContext('2d');
    ctx.scale(dpr,dpr);
    ctx.clearRect(0,0,W,H);
    if(this.type==='doughnut'){this._drawDoughnut(ctx,W,H,cfg);}
    else{this._drawBar(ctx,W,H,cfg);}
  }
  _drawBar(ctx,W,H,cfg){
    const PAD={t:16,r:16,b:56,l:48};
    const datasets=cfg.data.datasets||[];
    const labels=cfg.data.labels||[];
    const isH=(cfg.options&&cfg.options.indexAxis)==='y';
    const allVals=datasets.flatMap(d=>d.data||[]);
    const maxV=Math.max(...allVals,1);
    const cW=W-PAD.l-PAD.r,cH=H-PAD.t-PAD.b;
    /* grid */
    ctx.strokeStyle='#f1f5f9';ctx.lineWidth=1;
    const TICKS=4;
    for(let i=0;i<=TICKS;i++){
      const v=isH?PAD.t+cH/TICKS*i:PAD.t+cH/TICKS*(TICKS-i);
      ctx.beginPath();ctx.moveTo(PAD.l,v);ctx.lineTo(PAD.l+cW,v);ctx.stroke();
    }
    /* axes */
    ctx.strokeStyle='#cbd5e1';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(PAD.l,PAD.t);ctx.lineTo(PAD.l,PAD.t+cH);ctx.lineTo(PAD.l+cW,PAD.t+cH);ctx.stroke();
    /* tick labels */
    ctx.fillStyle='#64748b';ctx.font='11px sans-serif';ctx.textAlign='right';
    for(let i=0;i<=TICKS;i++){
      const val=Math.round(maxV/TICKS*(TICKS-i));
      const y=PAD.t+cH/TICKS*i;
      ctx.fillText(val>=1000?(val/1000).toFixed(1)+'k':val,PAD.l-4,y+4);
    }
    /* bars */
    const n=labels.length;const grpW=cW/Math.max(n,1);
    const dsCount=datasets.length;
    datasets.forEach((ds,di)=>{
      ctx.fillStyle=ds.backgroundColor||(Array.isArray(ds.backgroundColor)?ds.backgroundColor[di]:clr(di))||clr(di);
      (ds.data||[]).forEach((v,i)=>{
        const bW=Math.max(2,(grpW*0.7)/dsCount);
        const bH=Math.max(0,(v/maxV)*cH);
        const x=PAD.l+i*grpW+(grpW-bW*dsCount)/2+di*bW;
        const y=PAD.t+cH-bH;
        drawRoundRect(ctx,x,y,bW,bH,3);
        const c=typeof ds.backgroundColor==='string'?ds.backgroundColor:clr(di);
        ctx.fillStyle=c;ctx.fill();
      });
    });
    /* x labels */
    ctx.fillStyle='#64748b';ctx.font='11px sans-serif';ctx.textAlign='center';
    labels.forEach((l,i)=>{
      ctx.fillText(String(l).substring(0,8),PAD.l+i*grpW+grpW/2,PAD.t+cH+16);
    });
    /* legend */
    if(datasets.length>1){
      let lx=PAD.l;
      datasets.forEach((ds,di)=>{
        const c=typeof ds.backgroundColor==='string'?ds.backgroundColor:clr(di);
        ctx.fillStyle=c;ctx.fillRect(lx,H-14,10,10);
        ctx.fillStyle='#64748b';ctx.textAlign='left';
        ctx.fillText(ds.label||'',lx+13,H-5);
        lx+=ctx.measureText(ds.label||'').width+28;
      });
    }
  }
  _drawDoughnut(ctx,W,H,cfg){
    const PAD=40,cx=W/2,cy=(H-40)/2+PAD/2;
    const r=Math.min(W,H-40)/2-PAD;
    const inner=r*0.62;
    const data=cfg.data.datasets[0].data||[];
    const labels=cfg.data.labels||[];
    const total=data.reduce((a,b)=>a+b,0)||1;
    let angle=-Math.PI/2;
    data.forEach((v,i)=>{
      const sweep=v/total*Math.PI*2;
      ctx.beginPath();ctx.moveTo(cx,cy);
      ctx.arc(cx,cy,r,angle,angle+sweep);
      ctx.closePath();
      ctx.fillStyle=COLORS[i%COLORS.length];ctx.fill();
      angle+=sweep;
    });
    /* hole */
    ctx.beginPath();ctx.arc(cx,cy,inner,0,Math.PI*2);
    ctx.fillStyle='#fff';ctx.fill();
    /* center text */
    ctx.fillStyle='#1e293b';ctx.font='bold 14px sans-serif';ctx.textAlign='center';
    ctx.fillText(total.toLocaleString(),cx,cy+5);
    /* legend */
    const lStartY=cy+r+16;
    let lx=8;
    labels.forEach((l,i)=>{
      ctx.fillStyle=COLORS[i%COLORS.length];ctx.fillRect(lx,lStartY,10,10);
      ctx.fillStyle='#64748b';ctx.font='11px sans-serif';ctx.textAlign='left';
      const txt=String(l).substring(0,12);
      ctx.fillText(txt,lx+13,lStartY+9);
      lx+=ctx.measureText(txt).width+28;
      if(lx>W-60){lx=8;}
    });
  }
}
Chart.defaults={font:{family:'sans-serif',size:12},color:'#64748b'};
global.Chart=Chart;
})(window);
"""


def _get_chartjs_inline() -> str:
    """获取 Chart.js 内容：本地缓存 → 多 CDN 下载 → 内置极简兜底"""
    # 1. 本地缓存命中
    if os.path.exists(_CHARTJS_CACHE_PATH):
        try:
            with open(_CHARTJS_CACHE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            if len(content) > 10000:  # 简单验证非空
                return content
        except Exception:
            pass

    # 2. 依次尝试多个 CDN
    for url in _CHARTJS_CDNS:
        try:
            req = urllib.request.urlopen(url, timeout=6)
            js = req.read().decode('utf-8')
            if len(js) > 10000:
                # 写入本地缓存
                try:
                    with open(_CHARTJS_CACHE_PATH, 'w', encoding='utf-8') as f:
                        f.write(js)
                except Exception:
                    pass
                print(f'[chart.js] 已从 {url} 下载并缓存到本地', file=sys.stderr)
                return js
        except Exception:
            continue

    # 3. 网络完全不可用，使用内置极简兜底
    print('[chart.js] 网络不可用，已切换为离线简易图表模式', file=sys.stderr)
    return _CHARTJS_FALLBACK

# Windows 编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ─── ANSI 颜色 ────────────────────────────────────────────────────────────────
def colored(text: str, code: str) -> str:
    try:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass
    return f"\033[{code}m{text}\033[0m"

G    = lambda s: colored(s, "32")
Y    = lambda s: colored(s, "33")
B    = lambda s: colored(s, "34")
C    = lambda s: colored(s, "36")
R    = lambda s: colored(s, "31")
BOLD = lambda s: colored(s, "1")
DIM  = lambda s: colored(s, "2")


# ─── 工具函数 ─────────────────────────────────────────────────────────────────
def ratio_bar(ai: int, total: int, width: int = 28) -> str:
    if total <= 0:
        return "-" * width
    filled = int(ai / total * width)
    return G("#" * filled) + ("-" * (width - filled))


def fmt_ratio(ai: int, total: int) -> str:
    if total <= 0:
        return "N/A"
    r = ai / total * 100
    return (G if r >= 70 else Y if r >= 40 else lambda s: s)(f"{r:.1f}%")


def get_project_root() -> str:
    try:
        return subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, encoding='utf-8'
        ).stdout.strip()
    except Exception:
        return os.getcwd()


# ─── Session 文件解析 ─────────────────────────────────────────────────────────
def load_session_files(project_root: str) -> list[dict]:
    """读取 ai-sessions/ 目录下所有开发者的 session 文件"""
    sessions_dir = os.path.join(project_root, 'ai-sessions')
    if not os.path.isdir(sessions_dir):
        return []

    sessions = []
    pattern = os.path.join(sessions_dir, '*-ai-session-*.json')
    for fpath in glob.glob(pattern):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['_file'] = os.path.basename(fpath)
            # 兼容旧字段 files → pendingFiles
            if 'files' in data and 'pendingFiles' not in data:
                data['pendingFiles'] = data.pop('files')
            sessions.append(data)
        except Exception:
            pass
    return sessions


# ─── Git Log 解析 ──────────────────────────────────────────────────────────────
def get_git_log(since: Optional[str] = None, developer: Optional[str] = None) -> str:
    cmd = [
        'git', 'log',
        '--format=COMMIT_START%nhash:%H%nshort:%h%ndate:%ai%nauthor:%an%nsubject:%s%nBODY_START%n%b%nCOMMIT_END',
    ]
    if since:
        cmd.extend(['--after', since])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return result.stdout
    except FileNotFoundError:
        print(R("错误：未找到 git 命令"))
        sys.exit(1)


def get_total_lines(since: Optional[str] = None) -> int:
    cmd = ['git', 'log', '--numstat', '--format=']
    if since:
        cmd.extend(['--after', since])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        total = 0
        for line in result.stdout.splitlines():
            parts = line.strip().split('\t')
            if len(parts) >= 2 and parts[0].isdigit():
                total += int(parts[0])
        return total
    except Exception:
        return 0


def _parse_trailers_from_subject(subject: str, c: dict) -> None:
    """从 subject 行提取 AI trailers（兼容旧版 prepare-commit-msg 格式）。

    旧版 bug：prepare-commit-msg.js 写入 trailers 前只有一个 \\n，
    导致 trailers 进入 subject 段落而非 body，git %b 为空。
    新版已修复，此函数处理历史遗留提交。
    """
    import re
    # 匹配 " AI-Xxx: " 形式的 key 边界
    pattern = re.compile(r'\s+(AI-[\w-]+):\s+')
    matches = list(pattern.finditer(subject))
    if not matches:
        return
    for i, m in enumerate(matches):
        key = m.group(1)
        value_start = m.end()
        value_end   = matches[i + 1].start() if i + 1 < len(matches) else len(subject)
        value = subject[value_start:value_end].strip()
        if   key == 'AI-Generated':  c['ai_generated'] = value.lower() in ('true', '1', 'yes')
        elif key == 'AI-Tool':       c['ai_tool']       = value
        elif key == 'AI-Model':      c['ai_model']      = value
        elif key == 'AI-Developer':  c['ai_developer']  = value
        elif key == 'AI-File-List':  c['ai_file_list']  = value
        elif key == 'AI-Lines':
            try: c['ai_lines'] = int(value)
            except: pass
        elif key == 'AI-Total-Lines':
            try: c['ai_total_lines'] = int(value)
            except: pass
        elif key == 'AI-Files':
            try: c['ai_files'] = int(value)
            except: pass


def parse_commits(raw_log: str) -> list[dict]:
    commits = []
    for raw in raw_log.split('COMMIT_START\n'):
        raw = raw.strip()
        if not raw or 'hash:' not in raw:
            continue

        c = {
            'hash': '', 'short': '', 'date': '', 'author': '', 'subject': '',
            'ai_generated': False, 'ai_tool': '', 'ai_model': '',
            'ai_lines': 0, 'ai_lines_deleted': 0,
            'ai_total_lines': 0, 'ai_total_lines_deleted': 0,
            'ai_files': 0, 'ai_file_list': '', 'ai_developer': '',
        }

        body_lines, in_body = [], False
        for line in raw.splitlines():
            if line == 'BODY_START':   in_body = True;  continue
            if line == 'COMMIT_END':   in_body = False; continue
            if in_body:
                body_lines.append(line)
                continue
            if line.startswith('hash:'):    c['hash']    = line[5:].strip()
            elif line.startswith('short:'): c['short']   = line[6:].strip()
            elif line.startswith('date:'):  c['date']    = line[5:].strip()
            elif line.startswith('author:'): c['author'] = line[7:].strip()
            elif line.startswith('subject:'): c['subject'] = line[8:].strip()

        for line in body_lines:
            line = line.strip()
            if line.startswith('AI-Generated:'):
                c['ai_generated'] = line.split(':', 1)[1].strip().lower() in ('true', '1', 'yes')
            elif line.startswith('AI-Tool:'):       c['ai_tool']       = line.split(':', 1)[1].strip()
            elif line.startswith('AI-Model:'):      c['ai_model']      = line.split(':', 1)[1].strip()
            elif line.startswith('AI-Developer:'):  c['ai_developer']  = line.split(':', 1)[1].strip()
            elif line.startswith('AI-Lines:'):
                try: c['ai_lines'] = int(line.split(':', 1)[1].strip())
                except: pass
            elif line.startswith('AI-Lines-Deleted:'):
                try: c['ai_lines_deleted'] = int(line.split(':', 1)[1].strip())
                except: pass
            elif line.startswith('AI-Total-Lines:'):
                try: c['ai_total_lines'] = int(line.split(':', 1)[1].strip())
                except: pass
            elif line.startswith('AI-Total-Lines-Deleted:'):
                try: c['ai_total_lines_deleted'] = int(line.split(':', 1)[1].strip())
                except: pass
            elif line.startswith('AI-Files:'):
                try: c['ai_files'] = int(line.split(':', 1)[1].strip())
                except: pass
            elif line.startswith('AI-File-List:'): c['ai_file_list'] = line.split(':', 1)[1].strip()

        # 兼容旧版格式：trailers 嵌入 subject 行（旧版 prepare-commit-msg.js 的 bug）
        if not c['ai_generated'] and 'AI-Generated:' in c.get('subject', ''):
            _parse_trailers_from_subject(c['subject'], c)

        if c['hash']:
            commits.append(c)
    return commits


# ─── 控制台报告 ────────────────────────────────────────────────────────────────
def print_report(commits: list[dict], total_lines: int, sessions: list[dict],
                 since: Optional[str], developer: Optional[str], top_n: int):
    W = 62

    # 按开发者过滤（基于 AI-Developer trailer）
    if developer:
        commits = [c for c in commits if developer.lower() in c.get('ai_developer', '').lower()
                   or developer.lower() in c.get('author', '').lower()]

    ai_commits     = [c for c in commits if c['ai_generated']]
    total_ai_lines         = sum(c['ai_lines'] for c in ai_commits)
    total_ai_lines_deleted = sum(c['ai_lines_deleted'] for c in ai_commits)
    ai_net_lines           = total_ai_lines - total_ai_lines_deleted

    # ── 头部 ──────────────────────────────────────────────────────────────────
    print(f"\n{BOLD('=' * W)}")
    print(BOLD("   AI 代码占比分析报告"))
    print(BOLD(f"   生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    if since:     print(BOLD(f"   分析范围: {since} 至今"))
    if developer: print(BOLD(f"   开发者: {developer}"))
    print(BOLD('=' * W))

    # ── 总体概览 ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD('[ 总体概览 ]')}")
    total = len(commits)
    ai_c  = len(ai_commits)
    print(f"  总提交数       {BOLD(str(total))} 个")
    if total > 0:
        print(f"  AI 辅助提交    {BOLD(str(ai_c))} 个  ({fmt_ratio(ai_c, total)})")
        print(f"  人工提交       {total - ai_c} 个")
    print()
    print(f"\n{BOLD('[ 代码行数 ]')}")
    print(f"  总新增行数     {BOLD(str(total_lines))} 行")
    print(f"  AI 生成行数    {BOLD(str(total_ai_lines))} 行")
    if total_ai_lines_deleted > 0:
        print(f"  AI 删除行数    {BOLD(str(total_ai_lines_deleted))} 行")
        print(f"  AI 净增行数    {BOLD(str(ai_net_lines))} 行  {DIM('(生成 - 删除)')}")
    if total_lines > 0:
        print(f"  AI 代码占比    {fmt_ratio(total_ai_lines, total_lines)}  {DIM('(按生成行计)')}")
        print(f"  可视化         [{ratio_bar(total_ai_lines, total_lines)}]")

    # ── 效率指标 ──────────────────────────────────────────────────────────────
    if ai_commits:
        avg_ai_lines = total_ai_lines / len(ai_commits)
        commit_ratios = [
            c['ai_lines'] / c['ai_total_lines'] * 100
            for c in ai_commits if c['ai_total_lines'] > 0
        ]
        avg_commit_ratio = sum(commit_ratios) / len(commit_ratios) if commit_ratios else 0
        max_c    = max(ai_commits, key=lambda c: c['ai_lines'])
        max_hint = f"({max_c['short']} · {max_c['date'][:10]})"
        print(f"\n{BOLD('[ 效率指标 ]')}")
        print(f"  AI 提交均值    {avg_ai_lines:.0f} 行/次  {DIM('(每次 AI 提交平均生成行数)')}")
        print(f"  单次占比均值   {avg_commit_ratio:.1f}%  {DIM('(每次提交中 AI 行的平均占比)')}")
        print(f"  最大单次提交   {max_c['ai_lines']} 行  {DIM(max_hint)}")

    # ── Session 文件统计（各开发者） ──────────────────────────────────────────
    if sessions:
        print(f"\n{BOLD('[ 开发者 AI 使用统计 (来自 session 文件) ]')}")
        print(f"  {'开发者':<20} {'主机':<20} {'累计操作':>8} {'生成行':>8} {'删除行':>8} {'净增行':>8} {'提交数':>6}  待提交")
        print(f"  {'-'*20} {'-'*20} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6}  {'-'*8}")
        for s in sorted(sessions, key=lambda x: -(x.get('stats', {}).get('totalAiLines', 0))):
            dev       = s.get('developer', '?')
            host      = s.get('hostname', '?')
            stats     = s.get('stats', {})
            ops       = stats.get('totalOperations', 0)
            lines     = stats.get('totalAiLines', 0)
            deleted   = stats.get('totalAiLinesDeleted', 0)
            net       = lines - deleted
            commits_n = stats.get('totalCommits', 0)
            pending   = len(s.get('pendingFiles', []))
            pending_s = f"{Y(str(pending) + ' 个')}" if pending > 0 else DIM('0 个')
            print(f"  {C(dev):<28} {host:<20} {ops:>8} {lines:>8} {deleted:>8} {net:>8} {commits_n:>6}  {pending_s}")

    # ── 开发者贡献分解（来自 git trailers）────────────────────────────────────
    if ai_commits:
        dev_git_stats: dict[str, dict] = defaultdict(lambda: {'commits': 0, 'ai_lines': 0, 'ai_deleted': 0})
        for c in ai_commits:
            dev_key = (c['ai_developer'] or c['author'] or 'unknown').split('@')[0]
            dev_git_stats[dev_key]['commits']    += 1
            dev_git_stats[dev_key]['ai_lines']   += c['ai_lines']
            dev_git_stats[dev_key]['ai_deleted'] += c['ai_lines_deleted']

        if len(dev_git_stats) > 1:
            print(f"\n{BOLD('[ 开发者贡献分解 (来自 git trailers) ]')}")
            print(f"  {'开发者':<20} {'AI提交':>7} {'生成行':>8} {'删除行':>8} {'净增行':>8}")
            print(f"  {'-'*20} {'-'*7} {'-'*8} {'-'*8} {'-'*8}")
            for dev_key, ds in sorted(dev_git_stats.items(), key=lambda x: -x[1]['ai_lines']):
                net = ds['ai_lines'] - ds['ai_deleted']
                print(f"  {C(dev_key):<28} {ds['commits']:>7} {ds['ai_lines']:>8} {ds['ai_deleted']:>8} {net:>8}")

    # ── 模型分布 ──────────────────────────────────────────────────────────────
    if ai_commits:
        model_stats: dict[str, dict] = defaultdict(lambda: {'commits': 0, 'lines': 0})
        for c in ai_commits:
            model_stats[c['ai_model'] or 'unknown']['commits'] += 1
            model_stats[c['ai_model'] or 'unknown']['lines']   += c['ai_lines']

        print(f"\n{BOLD('[ AI 模型分布 ]')}")
        for model, st in sorted(model_stats.items(), key=lambda x: -x[1]['lines']):
            short = model.replace('claude-', '').replace('-cc', '')
            print(f"  {C(short):<32} {st['commits']:>4} 次提交  {st['lines']:>6} 行")

    # ── 月度趋势 ──────────────────────────────────────────────────────────────
    monthly: dict[str, dict] = defaultdict(lambda: {'total': 0, 'ai': 0, 'ai_lines': 0})
    for c in commits:
        m = c['date'][:7] if c['date'] else 'unknown'
        monthly[m]['total'] += 1
        if c['ai_generated']:
            monthly[m]['ai']      += 1
            monthly[m]['ai_lines'] += c['ai_lines']

    if len(monthly) > 1:
        print(f"\n{BOLD('[ 月度趋势 ]')}")
        print(f"  {'月份':<10} {'总提交':>7} {'AI提交':>7} {'AI占比':>9} {'AI行数':>9}")
        print(f"  {'-'*10} {'-'*7} {'-'*7} {'-'*9} {'-'*9}")
        for m in sorted(monthly.keys(), reverse=True)[:12]:
            s = monthly[m]
            print(f"  {m:<10} {s['total']:>7} {s['ai']:>7} {fmt_ratio(s['ai'], s['total']):>17} {s['ai_lines']:>9}")

    # ── 提交规模分布 ──────────────────────────────────────────────────────────
    if ai_commits:
        size_bands = [
            ('微小  <20行',     0,    20),
            ('小型  20-100行',  20,   100),
            ('中型  100-300行', 100,  300),
            ('大型  300-1k行',  300,  1000),
            ('超大  1k+行',     1000, 10**9),
        ]
        band_counts = {label: 0 for label, _, _ in size_bands}
        for c in ai_commits:
            for label, lo, hi in size_bands:
                if lo <= c['ai_lines'] < hi:
                    band_counts[label] += 1
                    break
        print(f"\n{BOLD('[ 提交规模分布 ]')}")
        total_sized = len(ai_commits)
        for label, count in band_counts.items():
            if count > 0:
                bar_len = int(count / total_sized * 24)
                bar = G('#' * bar_len) + DIM('·' * (24 - bar_len))
                print(f"  {label:<16} {count:>4} 次  [{bar}]  {fmt_ratio(count, total_sized)}")

    # ── 周度趋势（近 8 周）────────────────────────────────────────────────────
    weekly: dict[str, dict] = defaultdict(lambda: {'total': 0, 'ai': 0, 'ai_lines': 0})
    for c in commits:
        if c['date']:
            try:
                dt  = datetime.fromisoformat(c['date'][:19])
                iso = dt.isocalendar()
                week_key = f"{iso[0]}-W{iso[1]:02d}"
                weekly[week_key]['total'] += 1
                if c['ai_generated']:
                    weekly[week_key]['ai']       += 1
                    weekly[week_key]['ai_lines'] += c['ai_lines']
            except Exception:
                pass

    recent_weeks = sorted(weekly.keys(), reverse=True)[:8]
    if len(recent_weeks) > 1:
        print(f"\n{BOLD('[ 周度趋势 (近 8 周) ]')}")
        print(f"  {'周次':<12} {'总提交':>7} {'AI提交':>7} {'AI占比':>9} {'AI行数':>9}")
        print(f"  {'-'*12} {'-'*7} {'-'*7} {'-'*9} {'-'*9}")
        for w in recent_weeks:
            wk = weekly[w]
            print(f"  {w:<12} {wk['total']:>7} {wk['ai']:>7} {fmt_ratio(wk['ai'], wk['total']):>17} {wk['ai_lines']:>9}")

    # ── 文件类型分布 ──────────────────────────────────────────────────────────
    if ai_commits:
        ext_counter: dict[str, int] = defaultdict(int)
        for c in ai_commits:
            raw = re.sub(r'\s*\(\+\d+ more\)', '', c['ai_file_list'])
            for f in raw.split(','):
                f = f.strip()
                if '.' in f:
                    ext = f.rsplit('.', 1)[-1].lower()
                    if 1 <= len(ext) <= 6 and ext.isalnum():
                        ext_counter[ext] += 1
        if ext_counter:
            top_exts   = sorted(ext_counter.items(), key=lambda x: -x[1])[:10]
            total_ext  = sum(ext_counter.values())
            max_cnt    = top_exts[0][1]
            print(f"\n{BOLD('[ 文件类型分布 (Top 10) ]')}")
            for ext, cnt in top_exts:
                bar_len = int(cnt / max_cnt * 22)
                bar = G('#' * bar_len) + DIM('·' * (22 - bar_len))
                print(f"  .{ext:<8} {cnt:>4} 次  [{bar}]  {fmt_ratio(cnt, total_ext)}")

    # ── 最近 AI 提交明细 ──────────────────────────────────────────────────────
    if ai_commits:
        n = min(top_n, len(ai_commits))
        print(f"\n{BOLD(f'[ 最近 {n} 条 AI 提交 ]')}")
        print(f"  {'提交':<8} {'日期':<12} {'开发者':<16} {'AI/总行数':>13} {'占比':>8}  主题")
        print(f"  {'-'*8} {'-'*12} {'-'*16} {'-'*13} {'-'*8}  {'-'*20}")
        for c in ai_commits[:n]:
            date_s   = c['date'][:10] if c['date'] else '?'
            dev_s    = (c['ai_developer'] or c['author'] or '?').split('@')[0][:14]
            lines_s  = f"{c['ai_lines']}/{c.get('ai_total_lines', '?')}"
            ratio_s  = fmt_ratio(c['ai_lines'], c.get('ai_total_lines', 0)) if c.get('ai_total_lines') else 'N/A'
            subj     = c['subject'][:38] + ('...' if len(c['subject']) > 38 else '')
            model_s  = (c['ai_model'] or '').replace('claude-', '').replace('-cc', '')[:12]
            print(f"  {C(c['short']):<8} {date_s:<12} {dev_s:<16} {lines_s:>13} {ratio_s:>16}  {subj}")
            if model_s:
                print(f"  {'':8} {'':12} {'':16} {'':13} {'':8}  {B(f'[{model_s}]')}")

    print()
    print(BOLD("=" * W))
    print()


def print_json_report(commits: list[dict], total_lines: int, sessions: list[dict]):
    ai_commits             = [c for c in commits if c['ai_generated']]
    total_ai_lines         = sum(c['ai_lines'] for c in ai_commits)
    total_ai_lines_deleted = sum(c['ai_lines_deleted'] for c in ai_commits)

    # 效率指标
    avg_ai_lines = total_ai_lines / len(ai_commits) if ai_commits else 0
    commit_ratios = [c['ai_lines'] / c['ai_total_lines'] * 100 for c in ai_commits if c['ai_total_lines'] > 0]
    avg_commit_ratio = sum(commit_ratios) / len(commit_ratios) if commit_ratios else 0

    # 提交规模分布
    size_bands = [('<20', 0, 20), ('20-100', 20, 100), ('100-300', 100, 300), ('300-1k', 300, 1000), ('1k+', 1000, 10**9)]
    commit_size_dist = {}
    for label, lo, hi in size_bands:
        commit_size_dist[label] = sum(1 for c in ai_commits if lo <= c['ai_lines'] < hi)

    # 周度趋势（近 8 周）
    weekly_map: dict[str, dict] = defaultdict(lambda: {'total': 0, 'ai': 0, 'ai_lines': 0})
    for c in commits:
        if c['date']:
            try:
                dt = datetime.fromisoformat(c['date'][:19])
                iso = dt.isocalendar()
                wk = f"{iso[0]}-W{iso[1]:02d}"
                weekly_map[wk]['total'] += 1
                if c['ai_generated']:
                    weekly_map[wk]['ai']       += 1
                    weekly_map[wk]['ai_lines'] += c['ai_lines']
            except Exception:
                pass
    weekly_trends = [
        {'week': w, **weekly_map[w]}
        for w in sorted(weekly_map.keys(), reverse=True)[:8]
    ]

    # 文件类型分布
    ext_counter: dict[str, int] = defaultdict(int)
    for c in ai_commits:
        raw = re.sub(r'\s*\(\+\d+ more\)', '', c['ai_file_list'])
        for f in raw.split(','):
            f = f.strip()
            if '.' in f:
                ext = f.rsplit('.', 1)[-1].lower()
                if 1 <= len(ext) <= 6 and ext.isalnum():
                    ext_counter[ext] += 1
    file_type_dist = [{'ext': k, 'count': v} for k, v in sorted(ext_counter.items(), key=lambda x: -x[1])[:10]]

    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_commits':           len(commits),
            'ai_commits':              len(ai_commits),
            'ai_commit_ratio':         round(len(ai_commits) / len(commits) * 100, 2) if commits else 0,
            'total_lines_added':       total_lines,
            'ai_lines_added':          total_ai_lines,
            'ai_lines_deleted':        total_ai_lines_deleted,
            'ai_net_lines':            total_ai_lines - total_ai_lines_deleted,
            'ai_lines_ratio':          round(total_ai_lines / total_lines * 100, 2) if total_lines > 0 else 0,
        },
        'efficiency': {
            'avg_ai_lines_per_commit': round(avg_ai_lines, 1),
            'avg_ai_ratio_per_commit': round(avg_commit_ratio, 1),
        },
        'commit_size_distribution':    commit_size_dist,
        'weekly_trends':               weekly_trends,
        'file_type_distribution':      file_type_dist,
        'developers': [
            {
                'developer':          s.get('developer'),
                'hostname':           s.get('hostname'),
                'model':              s.get('model'),
                'stats':              s.get('stats', {}),
                'pending_files':      len(s.get('pendingFiles', [])),
                'last_updated':       s.get('lastUpdated'),
            }
            for s in sessions
        ],
        'ai_commits': [
            {
                'hash': c['hash'], 'short': c['short'], 'date': c['date'],
                'author': c['author'], 'subject': c['subject'],
                'ai_developer': c['ai_developer'], 'ai_model': c['ai_model'],
                'ai_lines': c['ai_lines'], 'ai_lines_deleted': c['ai_lines_deleted'],
                'ai_net_lines': c['ai_lines'] - c['ai_lines_deleted'],
                'ai_total_lines': c['ai_total_lines'],
                'ai_files': c['ai_files'], 'ai_file_list': c['ai_file_list'],
            }
            for c in ai_commits
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


# ─── HTML 报告生成器 ───────────────────────────────────────────────────────────
def build_html_report(commits: list[dict], total_lines: int, sessions: list[dict],
                      since: Optional[str] = None, developer: Optional[str] = None) -> str:
    """生成自包含的现代化 HTML 报告（白色主题，支持搜索/导出）"""
    if developer:
        commits = [c for c in commits if
                   developer.lower() in c.get('ai_developer', '').lower() or
                   developer.lower() in c.get('author', '').lower()]

    ai_commits             = [c for c in commits if c['ai_generated']]
    total_ai_lines         = sum(c['ai_lines'] for c in ai_commits)
    total_ai_lines_deleted = sum(c['ai_lines_deleted'] for c in ai_commits)
    ai_net_lines           = total_ai_lines - total_ai_lines_deleted
    ai_commit_pct          = round(len(ai_commits) / len(commits) * 100, 1) if commits else 0
    ai_lines_pct           = round(total_ai_lines / total_lines * 100, 1) if total_lines > 0 else 0

    avg_ai_lines    = round(total_ai_lines / len(ai_commits), 1) if ai_commits else 0
    commit_ratios   = [c['ai_lines'] / c['ai_total_lines'] * 100 for c in ai_commits if c['ai_total_lines'] > 0]
    avg_ratio       = round(sum(commit_ratios) / len(commit_ratios), 1) if commit_ratios else 0

    # 月度数据
    monthly: dict = defaultdict(lambda: {'total': 0, 'ai': 0, 'ai_lines': 0})
    for c in commits:
        m = c['date'][:7] if c['date'] else 'unknown'
        monthly[m]['total'] += 1
        if c['ai_generated']:
            monthly[m]['ai'] += 1
            monthly[m]['ai_lines'] += c['ai_lines']
    m_labels   = sorted(monthly.keys())[-12:]
    m_ai_lines = [monthly[m]['ai_lines'] for m in m_labels]
    m_total    = [monthly[m]['total']    for m in m_labels]
    m_ai       = [monthly[m]['ai']       for m in m_labels]

    # 模型分布
    model_map: dict = defaultdict(lambda: {'commits': 0, 'lines': 0})
    for c in ai_commits:
        key = (c['ai_model'] or 'unknown').replace('claude-', '').replace('-cc', '')
        model_map[key]['commits'] += 1
        model_map[key]['lines']   += c['ai_lines']
    models_sorted = sorted(model_map.items(), key=lambda x: -x[1]['lines'])

    # 文件类型
    ext_map: dict = defaultdict(int)
    for c in ai_commits:
        raw = re.sub(r'\s*\(\+\d+ more\)', '', c['ai_file_list'])
        for f in raw.split(','):
            f = f.strip()
            if '.' in f:
                ext = f.rsplit('.', 1)[-1].lower()
                if 1 <= len(ext) <= 6 and ext.isalnum():
                    ext_map[ext] += 1
    top_exts = sorted(ext_map.items(), key=lambda x: -x[1])[:10]

    # 提交规模
    size_bands = [('<20', 0, 20), ('20-100', 20, 100), ('100-300', 100, 300),
                  ('300-1k', 300, 1000), ('1k+', 1000, 10**9)]
    band_counts = {l: sum(1 for c in ai_commits if lo <= c['ai_lines'] < hi)
                   for l, lo, hi in size_bands}

    # 开发者（git trailers）
    dev_map: dict = defaultdict(lambda: {'commits': 0, 'ai_lines': 0, 'ai_deleted': 0})
    for c in ai_commits:
        dk = (c['ai_developer'] or c['author'] or 'unknown').split('@')[0]
        dev_map[dk]['commits']    += 1
        dev_map[dk]['ai_lines']   += c['ai_lines']
        dev_map[dk]['ai_deleted'] += c['ai_lines_deleted']

    # 提交记录（供前端 Table 使用）
    commits_json = json.dumps([{
        'hash':      c['short'],
        'date':      c['date'][:10] if c['date'] else '',
        'author':    (c['ai_developer'] or c['author'] or '?').split('@')[0],
        'subject':   c['subject'],
        'model':     (c['ai_model'] or '').replace('claude-', '').replace('-cc', ''),
        'ai_lines':  c['ai_lines'],
        'deleted':   c['ai_lines_deleted'],
        'net':       c['ai_lines'] - c['ai_lines_deleted'],
        'total':     c['ai_total_lines'],
        'files':     c['ai_files'],
        'file_list': c['ai_file_list'],
    } for c in ai_commits], ensure_ascii=False)

    chart_data = json.dumps({
        'monthly':    {'labels': m_labels, 'ai_lines': m_ai_lines, 'ai': m_ai, 'total': m_total},
        'models':     {'labels': [k for k, _ in models_sorted],
                       'lines':  [v['lines'] for _, v in models_sorted]},
        'file_types': {'labels': [f'.{k}' for k, _ in top_exts],
                       'counts': [v for _, v in top_exts]},
        'size_bands': {'labels': list(band_counts.keys()),
                       'counts': list(band_counts.values())},
    }, ensure_ascii=False)

    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    range_text   = f"分析范围：{since} 至今" if since else "全量分析"
    dev_text     = f" · 开发者：{developer}" if developer else ""

    # ── 开发者行 HTML ───────────────────────────────────────────────────────────
    dev_rows_html = ''
    for dk, ds in sorted(dev_map.items(), key=lambda x: -x[1]['ai_lines']):
        net = ds['ai_lines'] - ds['ai_deleted']
        dev_rows_html += (
            f'<tr><td>{dk}</td><td>{ds["commits"]}</td>'
            f'<td>{ds["ai_lines"]:,}</td><td>{ds["ai_deleted"]:,}</td>'
            f'<td><strong>{net:,}</strong></td></tr>'
        )

    # ── Session 行 HTML ─────────────────────────────────────────────────────────
    session_rows_html = ''
    for s in sorted(sessions, key=lambda x: -(x.get('stats', {}).get('totalAiLines', 0))):
        st      = s.get('stats', {})
        pending = len(s.get('pendingFiles', []))
        net_s   = st.get('totalAiLines', 0) - st.get('totalAiLinesDeleted', 0)
        badge   = f'<span class="badge badge-warn">{pending} 待提交</span>' if pending else '<span class="badge badge-ok">干净</span>'
        session_rows_html += (
            f'<tr><td>{s.get("developer","?")}</td><td>{s.get("hostname","?")}</td>'
            f'<td>{s.get("model","?")}</td>'
            f'<td>{st.get("totalOperations",0):,}</td>'
            f'<td>{st.get("totalAiLines",0):,}</td>'
            f'<td>{st.get("totalAiLinesDeleted",0):,}</td>'
            f'<td><strong>{net_s:,}</strong></td>'
            f'<td>{st.get("totalCommits",0)}</td>'
            f'<td>{badge}</td></tr>'
        )

    # ── CSS（plain string，无 f-string 转义问题） ──────────────────────────────
    CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"PingFang SC","Microsoft YaHei UI","Microsoft YaHei","Helvetica Neue",Arial,sans-serif;
     background:#f1f5f9;color:#1e293b;font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#f1f5f9}
::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px}

/* ── Layout ── */
.container{max-width:1280px;margin:0 auto;padding:24px}
.header{background:linear-gradient(135deg,#1e40af 0%,#3b7de8 60%,#60a5fa 100%);
        color:#fff;padding:40px 48px 36px;border-radius:16px;margin-bottom:24px;
        box-shadow:0 8px 32px rgba(59,125,232,.35)}
.header h1{font-size:26px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px}
.header .meta{font-size:13px;opacity:.8;display:flex;gap:16px;flex-wrap:wrap}
.header .meta span{display:flex;align-items:center;gap:4px}

/* ── KPI Cards ── */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;margin-bottom:24px}
.kpi-card{background:#fff;border-radius:12px;padding:20px 24px;
          box-shadow:0 1px 4px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
          border:1px solid #e2e8f0;transition:transform .2s,box-shadow .2s;position:relative;overflow:hidden}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:12px 12px 0 0}
.kpi-card.blue::before{background:linear-gradient(90deg,#3b7de8,#60a5fa)}
.kpi-card.green::before{background:linear-gradient(90deg,#10b981,#34d399)}
.kpi-card.purple::before{background:linear-gradient(90deg,#8b5cf6,#a78bfa)}
.kpi-card.amber::before{background:linear-gradient(90deg,#f59e0b,#fcd34d)}
.kpi-card:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.10)}
.kpi-label{font-size:12px;color:#64748b;font-weight:500;letter-spacing:.04em;text-transform:none;margin-bottom:8px}
.kpi-value{font-size:32px;font-weight:700;letter-spacing:-.03em;line-height:1;font-variant-numeric:tabular-nums}
.kpi-value.blue{color:#3b7de8}.kpi-value.green{color:#10b981}
.kpi-value.purple{color:#8b5cf6}.kpi-value.amber{color:#f59e0b}
.kpi-sub{font-size:12px;color:#94a3b8;margin-top:6px}

/* ── Sections ── */
.section{background:#fff;border-radius:12px;padding:24px;
         box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e2e8f0;margin-bottom:20px}
.section-title{font-size:15px;font-weight:600;color:#1e293b;margin-bottom:18px;
               display:flex;align-items:center;gap:8px}
.section-title .dot{width:4px;height:16px;border-radius:2px;background:currentColor}
.section-title.blue .dot{color:#3b7de8}
.section-title.green .dot{color:#10b981}
.section-title.purple .dot{color:#8b5cf6}
.section-title.amber .dot{color:#f59e0b}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
@media(max-width:768px){.two-col{grid-template-columns:1fr}}
.chart-wrap{position:relative;height:280px}

/* ── Table ── */
.table-wrap{overflow-x:auto;border-radius:8px;border:1px solid #e2e8f0}
table{width:100%;border-collapse:collapse;font-size:13px}
thead{background:#f8fafc}
th{padding:10px 14px;text-align:left;font-size:12px;font-weight:600;color:#64748b;
   letter-spacing:.04em;white-space:nowrap;border-bottom:1px solid #e2e8f0;cursor:pointer;user-select:none}
th:hover{background:#f1f5f9;color:#1e293b}
th .sort-icon{margin-left:4px;opacity:.4}
td{padding:10px 14px;border-bottom:1px solid #f1f5f9;color:#334155;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#fafcff}
.hash-link{font-family:monospace;font-size:12px;color:#3b7de8;font-weight:600}
.model-badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;
             font-weight:500;background:#eff6ff;color:#3b7de8}
.lines-cell{font-variant-numeric:tabular-nums;white-space:nowrap}
.no-data{text-align:center;padding:48px 0;color:#94a3b8;font-size:13px}

/* ── Badge ── */
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:500}
.badge-ok{background:#f0fdf4;color:#16a34a}
.badge-warn{background:#fffbeb;color:#d97706}

/* ── Toolbar ── */
.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.search-box{flex:1;min-width:180px;max-width:320px;position:relative}
.search-box input{width:100%;padding:7px 12px 7px 34px;border:1px solid #e2e8f0;border-radius:8px;
                  font-size:13px;outline:none;transition:border-color .2s,box-shadow .2s;background:#fff}
.search-box input:focus{border-color:#3b7de8;box-shadow:0 0 0 3px rgba(59,125,232,.12)}
.search-box svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#94a3b8}
.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border:1px solid #e2e8f0;
     border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;background:#fff;
     color:#475569;transition:all .15s;white-space:nowrap}
.btn:hover{background:#f8fafc;border-color:#cbd5e1;color:#1e293b}
.btn.primary{background:#3b7de8;border-color:#3b7de8;color:#fff}
.btn.primary:hover{background:#2563eb;border-color:#2563eb}
.result-count{font-size:12px;color:#94a3b8;margin-left:auto}

/* ── Progress bar ── */
.prog{background:#f1f5f9;border-radius:4px;height:6px;overflow:hidden;margin-top:4px}
.prog-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#3b7de8,#60a5fa)}
.prog-fill.green{background:linear-gradient(90deg,#10b981,#34d399)}

/* ── Print ── */
@media print{
  body{background:#fff}
  .toolbar,.btn{display:none}
  .section{break-inside:avoid;box-shadow:none;border:1px solid #e2e8f0}
  .kpi-card{break-inside:avoid}
}
"""

    # ── 获取 Chart.js（本地缓存→多CDN→离线兜底）──────────────────────────────
    chartjs_inline = _get_chartjs_inline()

    # ── JS（plain string） ──────────────────────────────────────────────────────
    JS_RUNTIME = r"""
// ── 图表初始化 ────────────────────────────────────────────────────────────────
const PALETTE = ['#3b7de8','#10b981','#f59e0b','#8b5cf6','#ef4444','#06b6d4','#ec4899','#84cc16'];
Chart.defaults.font.family = '"PingFang SC","Microsoft YaHei UI",sans-serif';
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#64748b';

function initCharts(DATA) {
  // 月度趋势（柱状图 + 折线叠加）
  const mCtx = document.getElementById('chartMonthly');
  if (mCtx && DATA.monthly.labels.length) {
    new Chart(mCtx, {
      data: {
        labels: DATA.monthly.labels,
        datasets: [
          { type:'bar', label:'AI 生成行', data: DATA.monthly.ai_lines,
            backgroundColor:'rgba(59,125,232,.7)', borderRadius:4, yAxisID:'y' },
          { type:'line', label:'AI 提交数', data: DATA.monthly.ai,
            borderColor:'#10b981', backgroundColor:'rgba(16,185,129,.1)',
            tension:.4, fill:true, pointRadius:3, yAxisID:'y1' },
        ]
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        interaction:{mode:'index',intersect:false},
        plugins:{ legend:{position:'bottom'}, tooltip:{callbacks:{
          label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString()
        }}},
        scales:{
          y:  { type:'linear', position:'left',  grid:{color:'#f1f5f9'}, ticks:{callback:v=>v>=1000?v/1000+'k':v} },
          y1: { type:'linear', position:'right', grid:{drawOnChartArea:false} }
        }
      }
    });
  }

  // 模型分布（甜甜圈）
  const mdCtx = document.getElementById('chartModels');
  if (mdCtx && DATA.models.labels.length) {
    new Chart(mdCtx, {
      type:'doughnut',
      data:{ labels: DATA.models.labels, datasets:[{
        data: DATA.models.lines,
        backgroundColor: PALETTE.slice(0, DATA.models.labels.length),
        borderWidth:0, hoverOffset:8,
      }]},
      options:{
        responsive:true, maintainAspectRatio:false, cutout:'62%',
        plugins:{ legend:{position:'bottom'}, tooltip:{callbacks:{
          label: ctx => ctx.label+': '+ctx.parsed.toLocaleString()+' 行'
        }}}
      }
    });
  }

  // 文件类型（横向条）
  const ftCtx = document.getElementById('chartFileTypes');
  if (ftCtx && DATA.file_types.labels.length) {
    new Chart(ftCtx, {
      type:'bar',
      data:{ labels: DATA.file_types.labels, datasets:[{
        label:'修改次数', data: DATA.file_types.counts,
        backgroundColor: DATA.file_types.labels.map((_,i) => PALETTE[i%PALETTE.length]+'cc'),
        borderRadius:4,
      }]},
      options:{
        indexAxis:'y', responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{ x:{ grid:{color:'#f1f5f9'} }, y:{ grid:{display:false} } }
      }
    });
  }

  // 提交规模（竖向条）
  const sbCtx = document.getElementById('chartSizeBands');
  if (sbCtx) {
    new Chart(sbCtx, {
      type:'bar',
      data:{ labels: DATA.size_bands.labels, datasets:[{
        label:'提交次数', data: DATA.size_bands.counts,
        backgroundColor:'rgba(139,92,246,.7)', borderRadius:4,
      }]},
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{ x:{grid:{display:false}}, y:{grid:{color:'#f1f5f9'}, ticks:{precision:0}} }
      }
    });
  }
}

// ── 提交表格搜索与排序 ───────────────────────────────────────────────────────
let filteredCommits = [];
let sortKey = 'date', sortAsc = false;

function renderTable(data) {
  const tbody = document.getElementById('commitTbody');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="no-data">没有匹配的提交记录</td></tr>';
    document.getElementById('resultCount').textContent = '0 条';
    return;
  }
  document.getElementById('resultCount').textContent = data.length + ' 条';
  tbody.innerHTML = data.map(c => {
    const pct = c.total > 0 ? Math.round(c.ai_lines / c.total * 100) : 0;
    const pctColor = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#3b7de8';
    return `<tr>
      <td><span class="hash-link">${c.hash}</span></td>
      <td>${c.date}</td>
      <td>${c.author}</td>
      <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escHtml(c.subject)}">${escHtml(c.subject)}</td>
      <td>${c.model ? '<span class="model-badge">'+escHtml(c.model)+'</span>' : '-'}</td>
      <td class="lines-cell" style="color:#3b7de8">${c.ai_lines.toLocaleString()}</td>
      <td class="lines-cell" style="color:#ef4444">${c.deleted > 0 ? '-'+c.deleted.toLocaleString() : '-'}</td>
      <td class="lines-cell"><strong style="color:${pctColor}">${pct}%</strong></td>
      <td class="lines-cell">${c.files}</td>
    </tr>`;
  }).join('');
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function applyFilterSort() {
  const q = document.getElementById('searchInput').value.toLowerCase();
  let result = window.ALL_COMMITS.filter(c =>
    !q || c.hash.includes(q) || c.author.toLowerCase().includes(q) ||
    c.subject.toLowerCase().includes(q) || c.model.toLowerCase().includes(q) ||
    c.file_list.toLowerCase().includes(q)
  );
  result.sort((a, b) => {
    let va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'string') va = va.toLowerCase(), vb = vb.toLowerCase();
    return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });
  filteredCommits = result;
  renderTable(result);
}

function setSortKey(key) {
  if (sortKey === key) sortAsc = !sortAsc; else { sortKey = key; sortAsc = false; }
  document.querySelectorAll('th[data-sort]').forEach(th => {
    const icon = th.querySelector('.sort-icon');
    if (!icon) return;
    icon.textContent = th.dataset.sort === key ? (sortAsc ? '▲' : '▼') : '⇅';
  });
  applyFilterSort();
}

// ── 导出功能 ─────────────────────────────────────────────────────────────────
function exportCSV() {
  const headers = ['提交','日期','开发者','主题','模型','AI生成行','AI删除行','净增行','AI占比%','文件数','文件列表'];
  const rows = filteredCommits.map(c => {
    const pct = c.total > 0 ? Math.round(c.ai_lines / c.total * 100) : 0;
    return [c.hash, c.date, c.author, '"'+c.subject.replace(/"/g,'""')+'"',
            c.model, c.ai_lines, c.deleted, c.net, pct, c.files,
            '"'+c.file_list.replace(/"/g,'""')+'"'].join(',');
  });
  const blob = new Blob(['\uFEFF'+headers.join(',')+'\n'+rows.join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'ai-commits-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}

function exportJSON() {
  const blob = new Blob([JSON.stringify(filteredCommits, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'ai-commits-' + new Date().toISOString().slice(0,10) + '.json';
  a.click();
}
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 代码占比分析报告</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <h1>🤖 AI 代码占比分析报告</h1>
    <div class="meta">
      <span>📅 生成时间：{generated_at}</span>
      <span>📊 {range_text}{dev_text}</span>
      <span>📦 共 {len(commits)} 次提交</span>
    </div>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi-card blue">
      <div class="kpi-label">AI 辅助提交率</div>
      <div class="kpi-value blue">{ai_commit_pct}%</div>
      <div class="kpi-sub">{len(ai_commits)} / {len(commits)} 次提交</div>
      <div class="prog" style="margin-top:10px"><div class="prog-fill" style="width:{min(ai_commit_pct,100)}%"></div></div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-label">AI 代码占比（生成行）</div>
      <div class="kpi-value green">{ai_lines_pct}%</div>
      <div class="kpi-sub">{total_ai_lines:,} / {total_lines:,} 行</div>
      <div class="prog" style="margin-top:10px"><div class="prog-fill green" style="width:{min(ai_lines_pct,100)}%"></div></div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-label">AI 净增行数</div>
      <div class="kpi-value purple">{ai_net_lines:,}</div>
      <div class="kpi-sub">生成 {total_ai_lines:,} − 删除 {total_ai_lines_deleted:,}</div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-label">效率均值（行/次）</div>
      <div class="kpi-value amber">{avg_ai_lines:,}</div>
      <div class="kpi-sub">单次占比均值 {avg_ratio}%</div>
    </div>
  </div>

  <!-- Charts Row 1 -->
  <div class="two-col">
    <div class="section">
      <div class="section-title blue"><span class="dot"></span>月度趋势</div>
      <div class="chart-wrap"><canvas id="chartMonthly"></canvas></div>
    </div>
    <div class="section">
      <div class="section-title purple"><span class="dot"></span>AI 模型分布</div>
      <div class="chart-wrap"><canvas id="chartModels"></canvas></div>
    </div>
  </div>

  <!-- Charts Row 2 -->
  <div class="two-col">
    <div class="section">
      <div class="section-title green"><span class="dot"></span>文件类型分布 (Top 10)</div>
      <div class="chart-wrap"><canvas id="chartFileTypes"></canvas></div>
    </div>
    <div class="section">
      <div class="section-title amber"><span class="dot"></span>提交规模分布</div>
      <div class="chart-wrap"><canvas id="chartSizeBands"></canvas></div>
    </div>
  </div>

  <!-- Developer Stats (git) -->
  {'<div class="section"><div class="section-title blue"><span class="dot"></span>开发者贡献分解（来自 git trailers）</div><div class="table-wrap"><table><thead><tr><th>开发者</th><th>AI提交</th><th>生成行</th><th>删除行</th><th>净增行</th></tr></thead><tbody>' + dev_rows_html + '</tbody></table></div></div>' if len(dev_map) > 1 else ''}

  <!-- Session Stats -->
  {'<div class="section"><div class="section-title green"><span class="dot"></span>开发者 Session 统计（本地累计）</div><div class="table-wrap"><table><thead><tr><th>开发者</th><th>主机</th><th>模型</th><th>操作数</th><th>生成行</th><th>删除行</th><th>净增行</th><th>提交数</th><th>状态</th></tr></thead><tbody>' + session_rows_html + '</tbody></table></div></div>' if sessions else ''}

  <!-- Commits Table -->
  <div class="section">
    <div class="section-title blue"><span class="dot"></span>AI 提交记录</div>
    <div class="toolbar">
      <div class="search-box">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input id="searchInput" type="text" placeholder="搜索提交、开发者、文件…" oninput="applyFilterSort()">
      </div>
      <button class="btn" onclick="exportCSV()">⬇ 导出 CSV</button>
      <button class="btn" onclick="exportJSON()">⬇ 导出 JSON</button>
      <button class="btn" onclick="window.print()">🖨 打印</button>
      <span class="result-count" id="resultCount"></span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th data-sort="hash" onclick="setSortKey('hash')">提交 <span class="sort-icon">⇅</span></th>
            <th data-sort="date" onclick="setSortKey('date')">日期 <span class="sort-icon">▼</span></th>
            <th data-sort="author" onclick="setSortKey('author')">开发者 <span class="sort-icon">⇅</span></th>
            <th>主题</th>
            <th data-sort="model" onclick="setSortKey('model')">模型 <span class="sort-icon">⇅</span></th>
            <th data-sort="ai_lines" onclick="setSortKey('ai_lines')">生成行 <span class="sort-icon">⇅</span></th>
            <th data-sort="deleted" onclick="setSortKey('deleted')">删除行 <span class="sort-icon">⇅</span></th>
            <th>AI占比</th>
            <th data-sort="files" onclick="setSortKey('files')">文件数 <span class="sort-icon">⇅</span></th>
          </tr>
        </thead>
        <tbody id="commitTbody"><tr><td colspan="9" class="no-data">加载中…</td></tr></tbody>
      </table>
    </div>
  </div>

  <div style="text-align:center;padding:16px 0;color:#94a3b8;font-size:12px">
    由 <strong>AI 代码追踪系统</strong> 自动生成 · {generated_at}
  </div>
</div>

<script>{chartjs_inline}</script>
<script>
const CHART_DATA = {chart_data};
window.ALL_COMMITS = {commits_json};
{JS_RUNTIME}
document.addEventListener('DOMContentLoaded', function() {{
  initCharts(CHART_DATA);
  applyFilterSort();
}});
</script>
</body>
</html>"""
    return html


# ─── 入口 ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='AI 代码占比分析报告',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--since',         metavar='DATE', help='起始日期 YYYY-MM-DD')
    parser.add_argument('--developer', '--author', dest='developer',
                        metavar='NAME', help='按开发者过滤（用户名或 user@host，支持 --author 别名）')
    parser.add_argument('--format',        choices=['console', 'json', 'html'], default='console')
    parser.add_argument('--output',        metavar='FILE', help='HTML 报告输出路径（默认 ai-report.html）')
    parser.add_argument('--top',           type=int, default=10, metavar='N', help='显示最近 N 条 AI 提交')
    parser.add_argument('--sessions-only', action='store_true', help='只显示 session 文件统计，跳过 git log 分析')
    args = parser.parse_args()

    project_root = get_project_root()
    sessions     = load_session_files(project_root)

    if args.sessions_only:
        if not sessions:
            print(Y("⚠ ai-sessions/ 目录下没有找到 session 文件"))
            print("  请先运行：node scripts/ai-tracker/install.js")
            sys.exit(0)
        print(f"\n{BOLD('[ 开发者 Session 文件汇总 ]')}")
        print(f"  {'文件名':<40} {'操作数':>8} {'AI 行数':>8} {'提交数':>6}  最后更新")
        print(f"  {'-'*40} {'-'*8} {'-'*8} {'-'*6}  {'-'*19}")
        for s in sorted(sessions, key=lambda x: -(x.get('stats', {}).get('totalAiLines', 0))):
            stats = s.get('stats', {})
            print(f"  {C(s.get('_file', '?')):<48} "
                  f"{stats.get('totalOperations', 0):>8} "
                  f"{stats.get('totalAiLines', 0):>8} "
                  f"{stats.get('totalCommits', 0):>6}  "
                  f"{s.get('lastUpdated', '?')[:19]}")
        print()
        sys.exit(0)

    # 完整分析
    raw_log     = get_git_log(since=args.since)
    commits     = parse_commits(raw_log)
    total_lines = get_total_lines(since=args.since)

    if not commits:
        print(Y("⚠ 未找到任何提交记录"))
        sys.exit(0)

    if args.format == 'json':
        print_json_report(commits, total_lines, sessions)
    elif args.format == 'html':
        html = build_html_report(commits, total_lines, sessions, args.since, args.developer)
        output_file = args.output or 'ai-report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ HTML 报告已生成：{output_file}")
    else:
        print_report(commits, total_lines, sessions, args.since, args.developer, args.top)


if __name__ == '__main__':
    main()
