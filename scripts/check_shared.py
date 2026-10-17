#!/usr/bin/env python3
"""校验公共区完整性与三方对话待办（research-collab skill）。

三个工具跑在同一个 Windows 用户下，ACL 无法区分它们，所以"路线只有 Codex 能改"
靠契约 + 哈希锚点来保障：DSH 每次动工前校验，不符即停手问人。

用法：
    python check_shared.py --verify              # 路线/大纲是否被人动过（动工前必跑）
    python check_shared.py --freeze              # Codex 定稿后冻结，写 sha256
    python check_shared.py --for dsh            # 还有谁在等我回应
    python check_shared.py --tail 5             # 看最近 5 条对话
    python check_shared.py --json               # 机器可读

退出码：0 正常；1 哈希不符（公共区被未授权改动）；2 输入错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

PROTECTED = ("route.md", "outline.md")
HEADER_RE = re.compile(r"^##\s+#(\d+)\s*·\s*([^·\n]+?)\s*·\s*(\S+)\s*·\s*(.+?)\s*$", re.M)
AUTHORS = ("codex", "dsh", "doubao", "user")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_shared_from_state(project: Path) -> Path | None:
    """从 state.yaml 的 shared_dir 读取公共区位置（公共区可能在项目之外）。"""
    state = project / "state.yaml"
    if not state.is_file():
        return None
    text = state.read_text(encoding="utf-8-sig", errors="replace")
    m = re.search(r"^shared_dir:\s*(.+?)\s*(?:#.*)?$", text, re.M)
    if not m:
        return None
    raw = m.group(1).strip().strip("\"'").strip()
    if not raw or raw.lower() in {"null", "~", "none"}:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (project / path).resolve()
    return path


def resolve_shared(project: Path, explicit: str | None) -> Path:
    """定位公共区：命令行 --shared > state.yaml 的 shared_dir > <project>/shared"""
    if explicit:
        return Path(explicit).expanduser().resolve()
    found = read_shared_from_state(project)
    return found if found is not None else project / "shared"


# ---------------------------------------------------------------- 对话解析

class Message:
    __slots__ = ("num", "when", "author", "kind", "body")

    def __init__(self, num: int, when: str, author: str, kind: str, body: str):
        self.num = num
        self.when = when
        self.author = author
        self.kind = kind
        self.body = body

    def mentions(self) -> set[str]:
        return {m.lower() for m in re.findall(r"@(\w+)", self.body)}


def parse_chat(path: Path) -> list[Message]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    matches = list(HEADER_RE.finditer(text))
    messages: list[Message] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        messages.append(
            Message(int(m.group(1)), m.group(2).strip(), m.group(3).strip().lower(), m.group(4).strip(), text[start:end])
        )
    return messages


def chat_state(messages: list[Message]) -> dict:
    replied: set[int] = set()
    closed: set[int] = set()
    for msg in messages:
        replied |= {int(x) for x in re.findall(r"回应:\s*#(\d+)", msg.body)}
        closed |= {int(x) for x in re.findall(r"关闭:\s*#(\d+)", msg.body)}
    nums = [m.num for m in messages]
    duplicates = sorted({n for n in nums if nums.count(n) > 1})
    dangling = sorted((replied | closed) - set(nums))
    return {
        "count": len(messages),
        "next_number": (max(nums) + 1) if nums else 1,
        "duplicates": duplicates,
        "dangling_refs": dangling,
        "settled": replied | closed,
    }


def open_for(messages: list[Message], agent: str, settled: set[int]) -> list[Message]:
    agent = agent.lower()
    return [
        m
        for m in messages
        if m.author != agent and agent in m.mentions() and m.num not in settled
    ]


# ---------------------------------------------------------------- 动作

def do_freeze(shared: Path) -> int:
    frozen = []
    for name in PROTECTED:
        target = shared / name
        if not target.is_file():
            print(f"[·] {name} 不存在，跳过")
            continue
        digest = sha256_of(target)
        (shared / f"{name}.sha256").write_text(digest + "\n", encoding="utf-8", newline="\n")
        frozen.append((name, digest))
    for name, digest in frozen:
        print(f"[✓] 已冻结 {name}  {digest[:12]}")
    if frozen:
        print()
        print("提示：重新冻结前，确认 chat.md 已有裁决、changelog.md 已记录变更。")
        print("冻结后任何改动都会被 --verify 报出来。")
    return 0


def do_verify(shared: Path) -> int:
    print(f"== 公共区完整性：{shared} ==")
    if not shared.is_dir():
        print(f"[x] 找不到公共区目录：{shared}", file=sys.stderr)
        return 2

    mismatch = False
    for name in PROTECTED:
        target = shared / name
        anchor = shared / f"{name}.sha256"
        if not target.is_file():
            print(f"[·] {name} 尚未创建")
            continue
        if not anchor.is_file():
            print(f"[·] {name} 未冻结（Codex 定稿后跑 --freeze）")
            continue
        expected = anchor.read_text(encoding="utf-8").strip()
        actual = sha256_of(target)
        if expected == actual:
            print(f"[✓] {name}  匹配 {actual[:12]}")
        else:
            mismatch = True
            print(f"[!] {name} 与冻结版本不一致——公共区被改动过")
            print(f"    冻结时 {expected[:12]}   当前 {actual[:12]}")
            print("    非 Codex 改动会导致此结果。停手：先问用户，或查 changelog.md / chat.md。")

    if mismatch:
        print()
        print("结论：不通过——不要在哈希不符的路线上继续实施。")
        return 1
    print()
    print("结论：通过")
    return 0


def do_for(shared: Path, agent: str, messages: list[Message], state: dict, tail: int) -> int:
    waiting = open_for(messages, agent, state["settled"])
    print(f"== 等待 @{agent} 回应的消息 ==")
    if not waiting:
        print("无。可以开始本棒工作。")
    else:
        for m in waiting:
            first = " ".join(m.body.split())[:90]
            print(f"  #{m.num:03d} · {m.when} · {m.author} · {m.kind}")
            print(f"        {first}")
    if state["duplicates"]:
        print(f"[!] 编号重复：{state['duplicates']}（会让「回应:」指错对象，需修正）")
    if state["dangling_refs"]:
        print(f"[!] 回应/关闭指向不存在的消息：{state['dangling_refs']}")
    print(f"\n共 {state['count']} 条消息，下一个编号 #{state['next_number']:03d}")

    if tail > 0:
        print(f"\n== 最近 {min(tail, len(messages))} 条 ==")
        for m in messages[-tail:]:
            print(f"#{m.num:03d} · {m.when} · {m.author} · {m.kind}")
            for line in m.body.strip().splitlines():
                if line.strip():
                    print(f"    {line.strip()[:110]}")
            print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验公共区完整性与对话待办")
    parser.add_argument("--project", default=".", help="项目根目录，默认当前目录")
    parser.add_argument(
        "--shared",
        default=None,
        help="公共区目录；省略时读 state.yaml 的 shared_dir，再退到 <project>/shared",
    )
    parser.add_argument("--chat", default=None, help="对话文件，默认 <shared>/chat.md")
    parser.add_argument("--freeze", action="store_true", help="冻结路线/大纲，写 sha256")
    parser.add_argument("--verify", action="store_true", help="校验哈希（默认动作）")
    parser.add_argument("--for", dest="agent", metavar="AGENT", help="列出等待该 agent 回应的消息")
    parser.add_argument("--tail", type=int, default=0, metavar="N", help="附带显示最近 N 条对话")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args(argv)

    project = Path(args.project).expanduser().resolve()
    shared = resolve_shared(project, args.shared)
    chat_path = Path(args.chat).expanduser().resolve() if args.chat else shared / "chat.md"

    if not shared.is_dir():
        print(f"[x] 找不到公共区：{shared}", file=sys.stderr)
        print("    公共区由使用者自己建立。先建目录，再初始化时用 --shared-dir 登记：", file=sys.stderr)
        print(f'      mkdir "{shared}"', file=sys.stderr)
        print(
            f'      python init_workspace.py "{project}" --fill --shared-dir "{shared}"',
            file=sys.stderr,
        )
        print("    或用 --shared 直接指定它现在的位置。", file=sys.stderr)
        return 2

    messages = parse_chat(chat_path)
    state = chat_state(messages)

    if args.json:
        waiting = open_for(messages, args.agent, state["settled"]) if args.agent else []
        payload = {
            "shared": str(shared),
            "chat": str(chat_path),
            "chat_state": {
                k: (sorted(v) if isinstance(v, set) else v) for k, v in state.items()
            },
            "waiting_for": args.agent,
            "waiting": [
                {"num": m.num, "when": m.when, "author": m.author, "kind": m.kind}
                for m in waiting
            ],
            "integrity": {
                name: (
                    "missing"
                    if not (shared / name).is_file()
                    else "unfrozen"
                    if not (shared / f"{name}.sha256").is_file()
                    else "match"
                    if (shared / f"{name}.sha256").read_text(encoding="utf-8").strip()
                    == sha256_of(shared / name)
                    else "mismatch"
                )
                for name in PROTECTED
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if "mismatch" in payload["integrity"].values() else 0

    if args.freeze:
        return do_freeze(shared)
    if args.agent:
        return do_for(shared, args.agent, messages, state, args.tail)
    return do_verify(shared)


if __name__ == "__main__":
    raise SystemExit(main())
