#!/usr/bin/env python3
"""自动生成交接提示词包（research-collab skill）。

豆包读不到任何文件，所以给它的每一包都必须自足。这个脚本把项目里的
路线、大纲、证据台账拼成一份可直接粘贴的完整提示词，避免手工漏项。

用法：
    # G4：让豆包做叙事反馈（读结果，判断论文该写什么）
    python make_brief.py --project "<项目目录>" --stage G4 --to doubao

    # G5：让豆包写某一节
    python make_brief.py --project "<项目目录>" --stage G5 --to doubao --section "3.2"

    # G1：给 Codex 的路线包（路径型，它能自己读文件）
    python make_brief.py --project "<项目目录>" --stage G1 --to codex

输出写到 <项目>/handoffs/<stage>_<to>_<日期>.md，并打印路径。

退出码：0 成功；2 输入错误（缺项目文件）；4 找不到指定小节。
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def state_get(text: str, key: str) -> str:
    """取 YAML 里的标量值；允许缩进（deliverables 块内的字段是缩进的）。"""
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.+?)\s*(?:#.*)?$", text, re.M)
    if not m:
        return ""
    return m.group(1).strip().strip("\"'").strip()


def resolve_shared(project: Path, state_text: str) -> Path:
    raw = state_get(state_text, "shared_dir")
    if not raw or raw.lower() in {"null", "~", "none"}:
        return project / "shared"
    p = Path(raw).expanduser()
    return p if p.is_absolute() else (project / p).resolve()


def section(md: str, heading: str) -> str:
    """取出 `## heading` 到下一个同级或更高级标题之间的正文。"""
    pattern = rf"^##\s*{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, md, re.M | re.S)
    return m.group(1).strip() if m else ""


def find_section_row(outline: str, section_id: str) -> str | None:
    """在大纲表格里找某一节的行。"""
    for line in outline.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == section_id:
            return line.strip()
    return None


def strip_h1(md: str) -> str:
    """去掉 Markdown 一级标题，避免拼进包后层级打架。"""
    lines = [ln for ln in md.splitlines() if not re.match(r"^#\s+\S", ln)]
    return "\n".join(lines).strip()


def load_claims(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if (r.get("id") or "").strip()]


def fmt_value(value: str, unit: str) -> str:
    """92.3 + % → 92.3% ；180 + kg·hm-2 → 180 kg·hm-2"""
    if not value:
        return "—"
    if not unit:
        return value
    return f"{value}{unit}" if unit[0] in "%‰°℃" else f"{value} {unit}"


def claims_table(claims: list[dict], strength_filter=None) -> str:
    if not claims:
        return "_（台账为空：先按 references/evidence-ledger.md 建立条目，否则豆包无数字可写）_"
    lines = ["| 编号 | 事实 | 数值/口径 | 强度 | 出处 |", "|---|---|---|---|---|"]
    for c in claims:
        strength = (c.get("strength") or "").strip()
        if strength_filter and strength not in strength_filter:
            continue
        shown = fmt_value((c.get("value") or "").strip(), (c.get("unit") or "").strip())
        lines.append(
            f"| {(c.get('id') or '').strip()} | {(c.get('claim') or '').strip()} | "
            f"{shown} | {strength} | {(c.get('source') or '').strip()} |"
        )
    return "\n".join(lines)


def build_g4(ctx: dict, claims: list[dict]) -> str:
    return f"""# 角色
你是中文科研写作顾问。你读研究产出，判断这篇论文「该讲什么故事、每一节该写什么、哪些话现在还不能写」。
你不做研究判断、不补数据、不写正文。

# 项目
题目：{ctx['title']}
用途：{ctx['target']} ｜ 语言：{ctx['language']} ｜ 正文字数预算：{ctx['word_budget']}
研究问题（来自已冻结路线）：{ctx['research_question'] or '（route.md 中未找到，请 DSH 补）'}
创新点（来自已冻结路线）：{ctx['innovations'] or '（route.md 中未找到，请 DSH 补）'}

# 研究产出（DSH 实施结果，这是全部事实来源）
## 证据台账
{claims_table(claims)}

## 图表
{ctx['figures'] or '- （尚无图：请 DSH 补充每张图想证明哪个 claim）'}

# 章节大纲（Codex 已定，你可以提出冲突但不许自行改写）
{ctx['outline'] or '（outline.md 为空，请 DSH 补齐后重生成）'}

# 只回答这五个问题
1. **主故事**：这篇论文一句话在讲什么？依据哪几个 claim 编号？（必须给编号）
2. **每节该写什么**：按大纲逐节，写"这一节要证明什么、用哪几个 claim、不要写什么"。
3. **现在写不出来的**：哪些结论缺证据、只能写"提示"不能写"证明"、或必须删掉？
4. **叙事顺序与图表**：建议的论证顺序，图 1/2/3 各自承担什么。
5. **与大纲的冲突**：大纲要求但结果支撑不了的，逐条列出，并给"删 / 降级 / 补做"建议。

# 严禁
1. 不得新增任何数字、样本量、年份；需要数字时只能引用上表编号。
2. 不得新增文献。
3. 不得把 assumption 写成"发现"，不得把相关写成因果。
4. 不得直接写正文段落（这一棒只出决策）。
5. 不得改写大纲；有冲突只提建议。

# 输出格式
## 主故事
## 分节写作决策
| 节 | 要证明什么 | 用哪些 claim | 不要写什么 |
## 现在写不出来的
## 建议图表顺序
## 与大纲的冲突
"""


def build_g5(ctx: dict, claims: list[dict], section_id: str, row: str | None) -> str:
    per_section = int(ctx["word_budget"] / 8) if ctx["word_budget"] else 1000
    return f"""# 角色
你是中文学术写作助手，负责把已确定的证据写成通顺、克制、可发表的正文。你不做研究判断，不补充事实。

# 写作对象
题目：{ctx['title']} ｜ 期刊/用途：{ctx['target']}
语体：学术书面语，第三人称，不过度使用破折号与排比
全文字数预算：{ctx['word_budget']}；本节预算：约 {per_section} 字（允许 ±10%）

# 本次只写这一节
章节：{section_id}
本节大纲要求：{row or '（outline.md 中未找到该节，请 DSH 确认节号）'}
上一节结尾（衔接参考）：{ctx['prev_tail'] or '（无）'}

# 可用证据（只许使用以下事实，编号必须出现在引用处）
{claims_table(claims, strength_filter={'measured', 'derived', 'literature'})}

# 叙事决策（来自 G4，已由用户确认）
{ctx['narrative'] or '（尚无 narrative 文件：建议先做 G4，否则容易写成流水账）'}

# 严禁
1. 不得新增任何数字、百分比、年份、样本量——包括"约""近""超过"这类模糊化改写。
2. 不得新增文献引用；需要而证据表里没有的，写 [待补:文献-xxx]。
3. 不得改变强度：assumption 只能写"估计/假定"，不得写成"表明/证明"。
4. 不得把相关写成因果；不得从单一样本外推到整体。
5. 不得使用"众所周知""毋庸置疑""具有重大意义"等空泛评价。
6. 不得出现"作为 AI 模型""根据您提供的资料"等元话语。

# 输出格式
- Markdown，从 `### ` 三级标题开始（不要自带一级标题）。
- 每段只承担一个论点，段首句即论点。
- 首次出现某证据时用「（C01）」标注。
- 数据不足处保留占位符 [待补:...]，不要自己填。
"""


def build_g1_codex(ctx: dict) -> str:
    return f"""# 角色
你是本项目的科研规划者。你只负责研究路线与大纲，不写代码、不写正文、不编造数据。

# 项目
题目：{ctx['title']}
用途：{ctx['target']}
语言与字数：{ctx['language']} / 正文约 {ctx['word_budget']} 字
已有数据：见 02_data/raw/（DSH 已整理清单）
公共区（三方共读，你唯一可写）：{ctx['shared_display']}

# 本次目标
产出一份可执行的技术路线：研究问题、创新点、分阶段实验设计、风险与降级方案。

# 输出：写入 {ctx['shared_display']}/route.md
## 研究问题
## 创新点（≤3 条，每条一句可证伪的断言）
## 技术路线（分阶段，每阶段：输入→方法→产出→验收标准）
## 需要的证据清单（供 DSH 建台账与排实施顺序）
## 风险与降级方案
## 不建议做的方向

# 然后
在 {ctx['shared_display']}/chat.md 追加一条消息，类型 `进度`，`@dsh @doubao`。

# 禁区
- 不编造数据、文献或已有结果。
- 不输出大段论文正文；需要时只给结构骨架。
- 证据清单里每条必须能被数据支撑或被标为"需新增实验"。
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成交接提示词包")
    parser.add_argument("--project", default=".", help="项目根目录")
    parser.add_argument("--stage", required=True, choices=["G1", "G4", "G5"], help="阶段")
    parser.add_argument("--to", required=True, choices=["doubao", "codex"], help="目标工具")
    parser.add_argument("--section", default=None, help="G5 用：章节号，如 3.2")
    parser.add_argument("--out", default=None, help="输出路径，默认 <项目>/handoffs/...")
    args = parser.parse_args(argv)

    project = Path(args.project).expanduser().resolve()
    state_path = project / "state.yaml"
    if not state_path.is_file():
        print(f"[x] 找不到 {state_path}；先初始化项目", file=sys.stderr)
        return 2

    state_text = read_text(state_path)
    shared = resolve_shared(project, state_text)
    if not shared.is_dir():
        print(f"[x] 找不到公共区：{shared}", file=sys.stderr)
        print("    公共区由使用者自己建立，位置记在 state.yaml 的 shared_dir", file=sys.stderr)
        return 2

    route_md = read_text(shared / "route.md") if (shared / "route.md").is_file() else ""
    outline_md = read_text(shared / "outline.md") if (shared / "outline.md").is_file() else ""
    claims = load_claims(project / "04_results" / "claims.csv")

    # 最近一份 narrative（G4 产出），给 G5 用
    narrative = ""
    draft_dir = project / "05_draft"
    if draft_dir.is_dir():
        cands = sorted(draft_dir.glob("narrative_*.md"))
        if cands:
            narrative = read_text(cands[-1]).strip()

    figures = ""
    fig_dir = project / "04_results" / "figures"
    if fig_dir.is_dir():
        figs = sorted(p.name for p in fig_dir.iterdir() if p.is_file())
        if figs:
            figures = "\n".join(f"- {name}" for name in figs)

    try:
        word_budget = int(state_get(state_text, "word_budget") or 0)
    except ValueError:
        word_budget = 0

    ctx = {
        "title": state_get(state_text, "project") or project.name,
        "target": "（未填）",
        "language": "zh",
        "word_budget": word_budget,
        "shared_display": str(shared),
        "research_question": section(route_md, "研究问题"),
        "innovations": section(route_md, "创新点"),
        "outline": strip_h1(outline_md),
        "figures": figures,
        "narrative": narrative,
        "prev_tail": "",
    }
    # deliverables 段里的 target / language
    m = re.search(r"^deliverables:\s*$((?:\n\s+.*)+)", state_text, re.M)
    if m:
        block = m.group(1)
        ctx["target"] = state_get(block, "target") or ctx["target"]
        ctx["language"] = state_get(block, "language") or ctx["language"]

    if args.stage == "G4":
        body = build_g4(ctx, claims)
    elif args.stage == "G5":
        if not args.section:
            print("[x] G5 需要 --section，例如 --section 3.2", file=sys.stderr)
            return 2
        row = find_section_row(outline_md, args.section)
        if row is None:
            print(f"[!] 大纲里没找到节 {args.section}，请确认节号（见 outline.md）", file=sys.stderr)
            return 4
        body = build_g5(ctx, claims, args.section, row)
    else:  # G1
        body = build_g1_codex(ctx)

    today = _dt.date.today().strftime("%Y%m%d")
    suffix = f"_{args.section.replace('.', '')}" if args.section else ""
    out = Path(args.out) if args.out else project / "handoffs" / f"{args.stage}_{args.to}_{today}{suffix}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    header = f"<!-- 由 make_brief.py 生成 · {args.stage} → {args.to} · {today} -->\n\n"
    out.write_text(header + body, encoding="utf-8", newline="\n")

    print(f"已生成：{out}")
    print(f"  目标：{args.to}   阶段：{args.stage}")
    print(f"  证据：{len(claims)} 条   公共区：{shared}")
    if args.to == "doubao":
        print()
        print("  豆包读不到文件：把整份内容复制进豆包对话框即可，不要只给路径。")
        print("  收回来后交给 DSH 落盘 + claim_check。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
