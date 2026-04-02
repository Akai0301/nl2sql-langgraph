#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
usql_runner.py - usql 助手脚本
自动从 .env.dev 读取数据库配置，调用 usql.exe 执行 SQL 操作。

Python 环境优先级（自动探测）：
  1. 项目虚拟环境（venv/ 或 .venv/ 目录下的 python）
  2. 系统 Python（py / python3 / python）

用法：
  py usql_runner.py --sql "SELECT * FROM sys_user LIMIT 5"
  py usql_runner.py --file ./scripts/init.sql
  py usql_runner.py --interactive
  py usql_runner.py --env .env.prod --sql "SHOW TABLES"
  py usql_runner.py --sql "SELECT * FROM sys_user" --format csv
  py usql_runner.py --sql "SELECT * FROM sys_user" --output ./output.csv --format csv
"""
import os
import re
import sys
import subprocess
import argparse
from pathlib import Path
from urllib.parse import quote


# ──────────────────────────────────────────────
# 虚拟环境自动探测（脚本第一件事）
# ──────────────────────────────────────────────

def ensure_project_venv() -> None:
    """
    检查当前 Python 是否在项目虚拟环境中。
    若不在，则自动查找项目 venv 并用它重新执行本脚本。

    探测顺序（Windows 优先，兼容 Linux/macOS）：
      1. {project_root}/venv/Scripts/python.exe
      2. {project_root}/.venv/Scripts/python.exe
      3. {project_root}/venv/bin/python
      4. {project_root}/.venv/bin/python
      5. {project_root}/env/Scripts/python.exe
      6. {project_root}/env/bin/python

    项目根目录判定：向上遍历父目录，找到含 .env.dev 或 requirements.txt 的目录。
    """
    # 已在虚拟环境中（sys.prefix != sys.base_prefix），直接跳过
    if sys.prefix != sys.base_prefix:
        return

    # 找项目根目录（沿脚本路径向上最多 5 层）
    script_dir = Path(__file__).parent.resolve()
    project_root: Path | None = None
    for parent in [script_dir] + list(script_dir.parents)[:4]:
        if (parent / '.env.dev').exists() or (parent / 'requirements.txt').exists():
            project_root = parent
            break

    if project_root is None:
        return  # 未找到项目根，使用当前 Python

    venv_candidates = [
        project_root / 'venv'  / 'Scripts' / 'python.exe',   # Windows venv
        project_root / '.venv' / 'Scripts' / 'python.exe',   # Windows .venv
        project_root / 'venv'  / 'bin'     / 'python',       # Linux/macOS venv
        project_root / '.venv' / 'bin'     / 'python',       # Linux/macOS .venv
        project_root / 'env'   / 'Scripts' / 'python.exe',   # Windows env
        project_root / 'env'   / 'bin'     / 'python',       # Linux/macOS env
    ]

    for venv_python in venv_candidates:
        if venv_python.exists():
            print(f"[INFO] 切换到项目虚拟环境: {venv_python}", file=sys.stderr)
            # os.execv 替换当前进程，不会返回
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)

    # 未找到 venv，打印提示后继续（不报错，使用当前 Python）
    print(f"[INFO] 未找到项目虚拟环境，使用系统 Python: {sys.executable}", file=sys.stderr)


# ──────────────────────────────────────────────
# 配置读取
# ──────────────────────────────────────────────

def load_env(env_file: str = '.env.dev') -> dict:
    """
    从 .env 文件读取配置，支持以下格式：
      KEY = 'value'
      KEY = value
      KEY=value
    """
    config: dict = {}
    config_path = Path(env_file)

    # 若是相对路径，则从当前目录、父目录逐级查找
    if not config_path.is_absolute():
        search_roots = [Path('.'), Path('..'), Path('../..')]
        for root in search_roots:
            candidate = root / env_file
            if candidate.exists():
                config_path = candidate.resolve()
                break

    if not config_path.exists():
        print(f"[ERROR] 找不到配置文件: {env_file}", file=sys.stderr)
        print(f"        请在项目根目录执行本脚本，或用 --env 指定配置文件路径", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=\s*['\"]?(.*?)['\"]?\s*$", line)
            if match:
                key, value = match.group(1), match.group(2).strip()
                config[key] = value

    return config


def build_dsn(config: dict) -> str:
    """
    根据 .env 配置构建 usql DSN 连接字符串。

    MySQL:      mysql://user:pass@host:port/dbname
    PostgreSQL: postgres://user:pass@host:port/dbname
    """
    db_type  = config.get('DB_TYPE',     'mysql').lower().strip("'\"")
    host     = config.get('DB_HOST',     '127.0.0.1').strip("'\"")
    port     = config.get('DB_PORT',     '3306').strip("'\"")
    username = config.get('DB_USERNAME', '').strip("'\"")
    password = config.get('DB_PASSWORD', '').strip("'\"")
    database = config.get('DB_DATABASE', '').strip("'\"")

    # URL 编码密码/用户名中的特殊字符（@ # / : 等）
    encoded_password = quote(password, safe='')
    encoded_username = quote(username, safe='')

    scheme_map = {
        'mysql':      'mysql',
        'postgresql': 'postgres',
        'postgres':   'postgres',
        'sqlite':     'sqlite',
        'sqlserver':  'sqlserver',
        'mssql':      'sqlserver',
    }
    scheme = scheme_map.get(db_type, db_type)

    if scheme == 'sqlite':
        return f"sqlite:{database}"

    return f"{scheme}://{encoded_username}:{encoded_password}@{host}:{port}/{database}"


# ──────────────────────────────────────────────
# usql.exe 路径解析
# ──────────────────────────────────────────────

def find_usql() -> Path:
    """
    查找 usql 可执行文件：
    1. 优先使用本脚本同级目录下的 usql.exe / usql
    2. 其次查找系统 PATH
    """
    script_dir = Path(__file__).parent.resolve()
    candidates = [
        script_dir / 'usql.exe',
        script_dir / 'usql',
    ]
    for c in candidates:
        if c.exists():
            return c

    import shutil
    found = shutil.which('usql') or shutil.which('usql.exe')
    if found:
        return Path(found)

    print("[ERROR] 找不到 usql 可执行文件", file=sys.stderr)
    print(f"        请将 usql.exe 放置到: {script_dir}", file=sys.stderr)
    print("        下载地址: https://github.com/xo/usql/releases", file=sys.stderr)
    sys.exit(1)


# ──────────────────────────────────────────────
# 主逻辑
# ──────────────────────────────────────────────

def run_usql(usql_bin: Path, dsn: str, args: argparse.Namespace) -> int:
    """构建并执行 usql 命令。"""
    cmd = [str(usql_bin), dsn]

    # 输出格式
    if args.format:
        fmt = args.format.lower()
        if fmt == 'csv':
            cmd += ['-P', 'format=csv']
        elif fmt == 'json':
            cmd += ['-P', 'format=json']
        elif fmt == 'table':
            pass  # 默认即为表格格式
        else:
            cmd += ['-P', f'format={fmt}']

    # 输出到文件
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd += ['-o', str(output_path)]

    # 执行模式
    if args.interactive:
        print(f"[INFO] 进入交互模式，连接: {_mask_dsn(dsn)}")
        result = subprocess.run(cmd)
        return result.returncode

    elif args.sql:
        cmd += ['-c', args.sql]
        print(f"[INFO] 执行 SQL: {args.sql[:80]}{'...' if len(args.sql) > 80 else ''}")

    elif args.file:
        sql_file = Path(args.file)
        if not sql_file.exists():
            print(f"[ERROR] SQL 文件不存在: {args.file}", file=sys.stderr)
            sys.exit(1)
        cmd += ['-f', str(sql_file)]
        print(f"[INFO] 执行 SQL 文件: {args.file}")

    else:
        # 无参数：进入交互模式
        print(f"[INFO] 进入交互模式，连接: {_mask_dsn(dsn)}")
        result = subprocess.run(cmd)
        return result.returncode

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def _mask_dsn(dsn: str) -> str:
    """隐藏 DSN 中的密码，用于日志显示。"""
    return re.sub(r'(:)([^:@]+)(@)', r'\1****\3', dsn)


# ──────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────

def main():
    # 第一步：确保使用正确的 Python 环境
    ensure_project_venv()

    parser = argparse.ArgumentParser(
        description='usql 助手脚本 - 自动读取 .env.dev 配置并执行 SQL（优先使用项目虚拟环境）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --sql "SHOW TABLES"
  %(prog)s --sql "SELECT * FROM sys_user LIMIT 5"
  %(prog)s --sql "DESCRIBE sys_role"
  %(prog)s --file ./scripts/init.sql
  %(prog)s --interactive
  %(prog)s --env .env.prod --sql "SELECT COUNT(*) FROM sys_user"
  %(prog)s --sql "SELECT * FROM sys_user" --format csv --output ./users.csv
        """.strip()
    )
    parser.add_argument('--env',         default='.env.dev', help='环境配置文件路径（默认: .env.dev）')
    parser.add_argument('--sql',         default=None,       help='要执行的 SQL 语句')
    parser.add_argument('--file',        default=None,       help='要执行的 SQL 文件路径')
    parser.add_argument('--interactive', action='store_true', help='进入 usql 交互模式')
    parser.add_argument('--format',      default=None,       help='输出格式: table（默认）/ csv / json')
    parser.add_argument('--output',      default=None,       help='输出结果到文件')
    parser.add_argument('--dsn',         default=None,       help='直接指定 DSN（跳过 .env 读取）')
    parser.add_argument('--show-dsn',    action='store_true', help='仅显示 DSN（不执行，用于调试）')

    args = parser.parse_args()

    # 确定 DSN
    if args.dsn:
        dsn = args.dsn
    else:
        config = load_env(args.env)
        dsn = build_dsn(config)

    if args.show_dsn:
        print(f"DSN: {_mask_dsn(dsn)}")
        print(f"DSN (raw): {dsn}")
        return

    # 查找 usql
    usql_bin = find_usql()
    print(f"[INFO] usql: {usql_bin}")
    print(f"[INFO] 连接: {_mask_dsn(dsn)}")

    exit_code = run_usql(usql_bin, dsn, args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
