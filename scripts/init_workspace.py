#!/usr/bin/env python3
"""初始化一个三方科研协作工作区（research-collab skill）。

公共区（三方共读的目录）**不自动创建**，必须由使用者自己建好再传给 --shared-dir。
它可以放在项目里，也可以放在共享盘 / 网盘同步目录里，由你决定。

用法：
    # 1) 先自己建公共区（下面任选其一）
    mkdir "<项目目录>/shared"
    mkdir "D:/OneDrive/科研共享/我的项目"

    # 2) 再初始化，并告诉脚本公共区在哪
    python init_workspace.py "<项目目录>" --title "项目名" --shared-dir "<项目目录>/shared"
    python init_workspace.py "<项目目录>" --title "项目名" --shared-dir "D:/OneDrive/科研共享/我的项目"

    # 只建项目骨架、暂不接公共区
    python init_workspace.py "<项目目录>" --title "项目名"

    # 之后补齐/切换公共区
    python init_workspace.py "<项目目录>" --fill --shared-dir "<公共区路径>"

退出码：0 成功；1 目标目录已含工作区且未加 --fill；2 参数或模板错误；3 公共区目录不存在。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
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

# 项目骨架目录。公共区不在此列——它由使用者自己建立。
DIRS = [
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

# 模板 -> 项目内相对路径
PROJECT_FILES = {
    "brief.md": "00_brief/brief.md",
    "glossary.md": "00_brief/glossary.md",
    "claims.csv": "04_results/claims.csv",
    "state.yaml": "state.yaml",
}

# 模板 -> 公共区内的文件名
SHARED_FILES = {
    "route.md": "route.md",
    "outline.md": "outline.md",
    "chat.md": "chat.md",
    "decisions.md": "decisions.md",
}

CHANGELOG = """# 路线变更记录

> 仅在 Codex 写入。冻结后的 `route.md` / `outline.md` 若要改主线，先在 `chat.md` 裁决，
> 在此登记，再解冻修改，最后重新 `check_shared.py --freeze`。只增不改。

| 日期 | 提出者 | 改什么 | 为什么 | 影响范围 |
|---|---|---|---|---|
| | | | | |
"""

SHARED_README = """# 公共区（三方共读）

这个目录由项目所有者手工建立，三个智能体都从这里读写：

| 文件 | 谁写 |
|---|---|
| `route.md` `outline.md` `changelog.md` | 仅 Codex |
| `chat.md` | 三方都追加，永不修改 |
| `decisions.md` | DSH 沉淀 |
| `*.sha256` | 仅 DSH 冻结时生成 |

**这个目录由你决定放在哪**：项目内 `shared/`、共享盘、网盘同步目录都可以。
位置记在项目 `state.yaml` 的 `shared_dir` 字段里，脚本据此定位。

如果这里同时服务于多个项目，建议一个项目一个子目录，避免 `chat.md` 互相污染。
"""

README = """# {{TITLE}}

本项目由三个智能体分工协作，通过文件交接（不依赖对话记忆）。

## 角色

| 工具 | 负责 | 写入范围 |
|---|---|---|
| Codex | 科研路线、大纲、路线变更裁决、审稿意见 | 公共区里的路线类文件 |
| DeepSeek Harness | 按路线实施研究（代码/数据/统计/图）、台账、校验、组装、维护对话格式 | `02_data/` `03_code/` `04_results/` `handoffs/` |
| 豆包电脑版 | 叙事反馈（论文该写什么）、中文学术文本写作 | `05_draft/`（经 DSH 落盘） |

## 公共区

位置：`{{SHARED_DISPLAY}}`（记在 `state.yaml` 的 `shared_dir`）

三方都能看，**路线只有 Codex 能写**（契约 + 哈希）。`chat.md` 是唯一例外：三方都追加，永不修改。

| 文件 | 谁写 |
|---|---|
| `route.md` `outline.md` `changelog.md` | 仅 Codex |
| `chat.md` | 三方都追加 |
| `decisions.md` | DSH 沉淀 |
| `*.sha256` | 仅 DSH 冻结时生成 |

## 现在看哪里

1. `state.yaml` —— 在哪个阶段、谁负责、下一步做什么（**接手先看这个**）
2. 公共区的 `chat.md` 末尾 —— 最近发生了什么、有无未决分歧
3. 公共区的 `decisions.md` —— 已裁决结论

## 阶段

G0 立项 → G1 路线(Codex) → G2 大纲(Codex) → G3 实施研究(DSH) → G4 叙事反馈(豆包) → G5 成稿(豆包) → G6 审核(Codex) → G7 交付

## 铁律

- 公共区的路线类文件只有 Codex 改；其他人要改走 `chat.md` 裁决。
- DSH 每次动工前 `check_shared.py --verify`，哈希不符就停手问人。
- 正文与叙事反馈里任何数字都必须能在 `04_results/claims.csv` 查到一行。
- `chat.md` 只追加；只记决定与分歧，结论进 `decisions.md`。
- 改稿新建版本号，不覆盖旧稿。

## 常用命令

```powershell
python "<SKILL_DIR>/scripts/check_shared.py" --project . --verify
python "<SKILL_DIR>/scripts/check_shared.py" --project . --for dsh
python "<SKILL_DIR>/scripts/check_shared.py" --project . --freeze
python "<SKILL_DIR>/scripts/claim_check.py" --draft 05_draft/v1_results.md --claims 04_results/claims.csv
```
"""


def build_vars(args: argparse.Namespace, shared_display: str) -> dict[str, str]:
    today = _dt.date.today().isoformat()
    return {
        "{{TITLE}}": args.title,
        "{{TARGET}}": args.target,
        "{{LANGUAGE}}": args.language,
        "{{WORD_BUDGET}}": str(args.word_budget),
        "{{DEADLINE}}": args.deadline or "待定",
        "{{DATE}}": today,
        "{{SHARED_DIR}}": shared_display,
        "{{SHARED_DISPLAY}}": shared_display,
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


def patch_shared_dir(state_path: Path, value: str) -> bool:
    """把 state.yaml 的 shared_dir 改成 value（--fill 时 state.yaml 已存在，需要就地更新）。"""
    if not state_path.is_file():
        return False
    text = state_path.read_text(encoding="utf-8-sig", errors="replace")
    line = f"shared_dir: {value}"
    new_text, n = re.subn(r"^shared_dir:.*$", line, text, count=1, flags=re.M)
    if n == 0:
        # 老版本 state.yaml 没有这个字段：插在 owner_of_current_stage 之后，否则放到开头
        new_text, n = re.subn(
            r"^(owner_of_current_stage:.*)$", r"\1\n" + line, text, count=1, flags=re.M
        )
        if n == 0:
            new_text = line + "\n" + text
    if new_text != text:
        state_path.write_text(new_text, encoding="utf-8", newline="\n")
        return True
    return False


def display_shared(root: Path, shared: Path | None) -> str:
    if shared is None:
        return "null   # 尚未建立：自己建好目录后跑 --fill --shared-dir <路径>"
    try:
        rel = Path(os.path.relpath(shared, root))
        if not str(rel).startswith(".."):
            return f"./{rel.as_posix()}"
    except ValueError:
        pass
    return shared.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="初始化三方科研协作工作区（公共区需由使用者自行建立）"
    )
    parser.add_argument("target_dir", help="项目目录（不存在会自动创建）")
    parser.add_argument("--title", default="未命名项目", help="项目题目")
    parser.add_argument("--target", default="中文核心期刊论文", help="用途/目标刊物")
    parser.add_argument("--language", default="zh", choices=["zh", "en"], help="正文语言")
    parser.add_argument("--word-budget", type=int, default=8000, help="正文字数预算")
    parser.add_argument("--deadline", default=None, help="截止日期 YYYY-MM-DD")
    parser.add_argument(
        "--shared-dir",
        default=None,
        help="公共区目录。必须是已存在的目录（脚本不替你创建），可放在项目内或共享盘",
    )
    parser.add_argument("--fill", action="store_true", help="只补缺失文件，不报错")
    parser.add_argument("--no-git", action="store_true", help="不尝试 git init")
    args = parser.parse_args(argv)

    skill_dir = Path(__file__).resolve().parent.parent
    template_dir = skill_dir / "templates"
    if not template_dir.is_dir():
        print(f"[x] 找不到模板目录：{template_dir}", file=sys.stderr)
        return 2

    root = Path(args.target_dir).expanduser().resolve()

    # ---- 公共区：必须由使用者自己建好 ----
    shared: Path | None = None
    if args.shared_dir:
        shared = Path(args.shared_dir).expanduser().resolve()
        if not shared.exists():
            print(f"[x] 公共区目录不存在：{shared}", file=sys.stderr)
            print("    公共区必须由你自己建立，脚本不会替你创建。先建目录再重跑：", file=sys.stderr)
            print(f'      mkdir "{shared}"', file=sys.stderr)
            print(
                f'      python init_workspace.py "{root}" --title "{args.title}" '
                f'--shared-dir "{shared}"',
                file=sys.stderr,
            )
            print("    也可以放在共享盘 / 网盘同步目录，三方都读得到即可。", file=sys.stderr)
            return 3
        if not shared.is_dir():
            print(f"[x] --shared-dir 不是目录：{shared}", file=sys.stderr)
            return 2

    known = [root / d for d in DIRS] + [root / f for f in PROJECT_FILES.values()]
    if root.exists() and any(p.exists() for p in known) and not args.fill:
        print(f"[x] {root} 已含协作工作区文件。确认要只补缺失项，请加 --fill", file=sys.stderr)
        return 1

    root.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    shared_display = display_shared(root, shared)
    variables = build_vars(args, shared_display)
    written: list[str] = []

    for tpl_name, rel in PROJECT_FILES.items():
        tpl_path = template_dir / tpl_name
        if not tpl_path.is_file():
            print(f"[x] 缺少模板：{tpl_path}", file=sys.stderr)
            return 2
        content = render(tpl_path.read_text(encoding="utf-8"), variables)
        if write_file(root / rel, content) == "write":
            written.append(rel)

    # ---- 往使用者提供的公共区里放协作文件 ----
    if shared is not None:
        # state.yaml 可能是 --fill 之前就存在的，需要就地更新 shared_dir
        if patch_shared_dir(root / "state.yaml", shared_display):
            written.append("state.yaml  (更新 shared_dir)")
        for tpl_name, name in SHARED_FILES.items():
            tpl_path = template_dir / tpl_name
            if not tpl_path.is_file():
                print(f"[x] 缺少模板：{tpl_path}", file=sys.stderr)
                return 2
            content = render(tpl_path.read_text(encoding="utf-8"), variables)
            if write_file(shared / name, content) == "write":
                written.append(f"{name}  →  公共区")
        changelog = render(CHANGELOG, variables)
        if write_file(shared / "changelog.md", changelog) == "write":
            written.append("changelog.md  →  公共区")
        readme_shared = render(SHARED_README, variables)
        if write_file(shared / "README.md", readme_shared) == "write":
            written.append("README.md  →  公共区")

    if write_file(root / "README.md", render(README, variables)) == "write":
        written.append("README.md")

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

    print(f"项目：{root}")
    print(f"新建 {len(written)} 个文件：")
    for rel in written:
        print(f"  + {rel}")
    print()

    if shared is None:
        print("[!] 还没指定公共区。三方协作靠公共区交换文件，请你自己建立：")
        print(f'      mkdir "{root / "shared"}"')
        print("      # 也可以放在共享盘 / 网盘，例如 D:/OneDrive/科研共享/本项目")
        print("    然后补齐：")
        print(
            f'      python init_workspace.py "{root}" --title "{args.title}" '
            f'--fill --shared-dir "{root / "shared"}"'
        )
        print()
        print("在公共区就位之前，不要进入 G1（路线会被写到那里）。")
    else:
        print(f"公共区：{shared}")
        print("  - 三方共读；route.md / outline.md / changelog.md 只有 Codex 写")
        print("  - chat.md 三方追加，永不修改")
        print()
        print("下一棒（G0 立项，由你完成）：")
        print("  1. 填 00_brief/brief.md：研究问题、核心论点、已有数据、硬约束")
        print("  2. 填 00_brief/glossary.md：术语与计量口径")
        print("  3. 回到 DSH 说“开始 G1”，它会生成给 Codex 的路线提示词包")
        print()
        print("提示：state.yaml 的 next_actions 是三方共用的唯一进度源，每次交接后更新它。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
