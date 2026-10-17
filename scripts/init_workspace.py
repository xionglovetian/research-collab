#!/usr/bin/env python3
"""初始化一个三方科研协作工作区（research-collab skill）。

用法：
    python init_workspace.py <项目目录> --title "项目名" --target "中文核心期刊" --language zh
    python init_workspace.py <项目目录> --fill      # 只补缺失文件，不动已有内容

退出码：0 成功；1 目标目录已含工作区且未加 --fill；2 参数或模板错误。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

DIRS = [
    "shared",
    "00_brief",
    "02_data/raw",
    "03_code/src",
    "03_code/logs",
    "04_results/tables",
    "04_results/figures",
    "05_draft",
    "06_review",
    "07_final",
    "handoffs",
]

# 模板文件 -> 目标相对路径
FILES = {
    "brief.md": "00_brief/brief.md",
    "glossary.md": "00_brief/glossary.md",
    "route.md": "shared/route.md",
    "outline.md": "shared/outline.md",
    "chat.md": "shared/chat.md",
    "decisions.md": "shared/decisions.md",
    "claims.csv": "04_results/claims.csv",
    "state.yaml": "state.yaml",
}

CHANGELOG = """# 路线变更记录

> 仅在 Codex 写入。冻结后的 `route.md` / `outline.md` 若要改主线，先在 `chat.md` 裁决，
> 在此登记，再解冻修改，最后重新 `check_shared.py --freeze`。只增不改。

| 日期 | 提出者 | 改什么 | 为什么 | 影响范围 |
|---|---|---|---|---|
| | | | | |
"""

README = """# {{TITLE}}

本项目由三个智能体分工协作，通过本目录下的文件交接（不依赖对话记忆）。

## 角色

| 工具 | 负责 | 写入范围 |
|---|---|---|
| Codex | 科研路线、大纲、路线变更裁决、审稿意见 | `shared/` 的路线类文件 |
| DeepSeek Harness | 按路线实施研究（代码/数据/统计/图）、台账、校验、组装、维护对话格式 | `02_data/` `03_code/` `04_results/` `handoffs/` |
| 豆包电脑版 | 叙事反馈（论文该写什么）、中文学术文本写作 | `05_draft/`（经 DSH 落盘） |

## 公共区 `shared/`

三方都能看，**路线只有 Codex 能写**（契约 + 哈希，见下）。`chat.md` 是唯一例外：三方都追加。

| 文件 | 谁写 |
|---|---|
| `route.md` `outline.md` `changelog.md` | 仅 Codex |
| `chat.md` | 三方都追加，永不修改 |
| `decisions.md` | DSH 沉淀 |
| `*.sha256` | 仅 DSH 冻结时生成 |

## 现在看哪里

1. `state.yaml` —— 在哪个阶段、谁负责、下一步做什么（**接手先看这个**）
2. `shared/chat.md` 末尾 —— 最近发生了什么、有无未决分歧
3. `shared/decisions.md` —— 已裁决结论

## 阶段

G0 立项 → G1 路线(Codex) → G2 大纲(Codex) → G3 实施研究(DSH) → G4 叙事反馈(豆包) → G5 成稿(豆包) → G6 审核(Codex) → G7 交付

## 铁律

- `shared/` 路线类文件只有 Codex 改；其他人要改走 `chat.md` 裁决。
- DSH 每次动工前 `check_shared.py --verify`，哈希不符就停手问人。
- 正文与叙事反馈里任何数字都必须能在 `04_results/claims.csv` 查到一行。
- `chat.md` 只追加；只记决定与分歧，结论进 `decisions.md`。
- 改稿新建版本号，不覆盖旧稿。

## 常用命令

```powershell
python "<SKILL_DIR>/scripts/check_shared.py" --verify     # 路线是否被人动过
python "<SKILL_DIR>/scripts/check_shared.py" --for dsh   # 谁在等我回应
python "<SKILL_DIR>/scripts/check_shared.py" --freeze    # Codex 定稿后冻结
python "<SKILL_DIR>/scripts/claim_check.py" --draft 05_draft/v1_results.md --claims 04_results/claims.csv
```
"""


def build_vars(args: argparse.Namespace) -> dict[str, str]:
    today = _dt.date.today().isoformat()
    return {
        "{{TITLE}}": args.title,
        "{{TARGET}}": args.target,
        "{{LANGUAGE}}": args.language,
        "{{WORD_BUDGET}}": str(args.word_budget),
        "{{DEADLINE}}": args.deadline or "待定",
        "{{DATE}}": today,
    }


def render(text: str, variables: dict[str, str]) -> str:
    for key, value in variables.items():
        text = text.replace(key, value)
    return text


def write_file(path: Path, content: str) -> str:
    """只创建缺失文件，永不覆盖已有内容——协作中最贵的错误是覆盖别人那一棒。"""
    if path.exists():
        return "skip"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return "write"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="初始化三方科研协作工作区")
    parser.add_argument("target_dir", help="项目目录（不存在会自动创建）")
    parser.add_argument("--title", default="未命名项目", help="项目题目")
    parser.add_argument("--target", default="中文核心期刊论文", help="用途/目标刊物")
    parser.add_argument("--language", default="zh", choices=["zh", "en"], help="正文语言")
    parser.add_argument("--word-budget", type=int, default=8000, help="正文字数预算")
    parser.add_argument("--deadline", default=None, help="截止日期 YYYY-MM-DD")
    parser.add_argument("--fill", action="store_true", help="只补缺失文件，不报错")
    parser.add_argument("--no-git", action="store_true", help="不尝试 git init")
    args = parser.parse_args(argv)

    skill_dir = Path(__file__).resolve().parent.parent
    template_dir = skill_dir / "templates"
    if not template_dir.is_dir():
        print(f"[x] 找不到模板目录：{template_dir}", file=sys.stderr)
        return 2

    root = Path(args.target_dir).expanduser().resolve()
    known = [root / d for d in DIRS] + [root / f for f in FILES.values()]
    if root.exists() and any(p.exists() for p in known) and not args.fill:
        print(f"[x] {root} 已含协作工作区文件。确认要只补缺失项，请加 --fill", file=sys.stderr)
        return 1

    root.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    variables = build_vars(args)
    written: list[str] = []
    for tpl_name, rel in FILES.items():
        tpl_path = template_dir / tpl_name
        if not tpl_path.is_file():
            print(f"[x] 缺少模板：{tpl_path}", file=sys.stderr)
            return 2
        content = render(tpl_path.read_text(encoding="utf-8"), variables)
        if write_file(root / rel, content) == "write":
            written.append(rel)

    extra = {
        "shared/changelog.md": render(CHANGELOG, variables),
        "README.md": render(README, variables),
    }
    for rel, content in extra.items():
        if write_file(root / rel, content) == "write":
            written.append(rel)

    if not args.no_git and shutil.which("git") and not (root / ".git").exists():
        try:
            subprocess.run(
                ["git", "init", "-q"],
                cwd=root,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            gitignore = root / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text(
                    "02_data/raw/\n*.tmp\n~$*\n__pycache__/\n.venv/\n", encoding="utf-8"
                )
                written.append(".gitignore")
        except Exception:
            print("[!] git init 失败，跳过（不影响使用）", file=sys.stderr)

    print(f"工作区：{root}")
    print(f"新建文件 {len(written)} 个：")
    for rel in written:
        print(f"  + {rel}")
    print()
    print("下一棒（G0 立项，由你完成）：")
    print("  1. 填 00_brief/brief.md：研究问题、核心论点、已有数据、硬约束")
    print("  2. 填 00_brief/glossary.md：术语与计量口径（同一指标只留一种写法）")
    print("  3. 回到 DSH，说“开始 G1”，它会生成给 Codex 的路线提示词包")
    print()
    print("公共区 shared/：三方共读；路线只有 Codex 写；chat.md 三方追加（详见 references/chat-protocol.md）。")
    print("state.yaml 的 next_actions 是三方共用的唯一进度源，每次交接后更新它。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
