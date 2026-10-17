#!/usr/bin/env python3
"""生成 README 首页流程图 docs/flow.svg。

无第三方依赖：纯字符串拼接 SVG。改布局只需改下面常量。
生成后可用浏览器打开，或用 Edge/Chrome headless 截图成 PNG：

    msedge --headless --disable-gpu --screenshot=flow.png --window-size=1200,840 docs/flow.svg
"""

from __future__ import annotations

import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "flow.svg"

W, H = 1200, 840

INK = "#0f172a"
BODY = "#334155"
MUTED = "#64748b"
LINE = "#cbd5e1"
HAIR = "#e2e8f0"
PANEL = "#f8fafc"

CODEX = "#2563eb"
CODEX_BG = "#eff6ff"
DSH = "#059669"
DSH_BG = "#ecfdf5"
DB = "#ea580c"
DB_BG = "#fff7ed"
USER = "#64748b"
USER_BG = "#f1f5f9"

FONT = "'Microsoft YaHei','PingFang SC','Hiragino Sans GB','Noto Sans CJK SC','Source Han Sans SC','Segoe UI',sans-serif"
MONO = "'Cascadia Mono','Consolas','SF Mono','Menlo',monospace"

parts: list[str] = []


def add(s: str) -> None:
    parts.append(s)


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def text(
    x: float,
    y: float,
    s: str,
    size: float = 13,
    fill: str = BODY,
    weight: int = 400,
    anchor: str = "start",
    family: str = FONT,
    spacing: float | None = None,
) -> None:
    extra = f' letter-spacing="{spacing}"' if spacing is not None else ""
    add(
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{extra}>{esc(s)}</text>'
    )


def rect(x, y, w, h, rx=10, fill="#ffffff", stroke=None, sw=1.5) -> None:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}/>')


def vline(x, y1, y2, color=LINE, both=True, sw=1.6) -> None:
    """竖向连线，both=True 时两端都带箭头。"""
    add(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="{sw}"/>')
    if both:
        add(f'<path d="M {x} {y2} l -4.5 -8 l 9 0 z" fill="{color}"/>')
        add(f'<path d="M {x} {y1} l -4.5 8 l 9 0 z" fill="{color}"/>')
    else:
        add(f'<path d="M {x} {y2} l -4.5 -8 l 9 0 z" fill="{color}"/>')


def harrow(x1, x2, y, color=LINE, sw=1.6) -> None:
    add(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="{sw}"/>')
    add(f'<path d="M {x2} {y} l -9 -4.5 l 0 9 z" fill="{color}"/>')


# ------------------------------------------------------------------ 画布
add(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" role="img" '
    f'aria-label="research-collab 三方科研协作流程图">'
)
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# ------------------------------------------------------------------ 标题
text(60, 56, "research-collab", 28, INK, 700)
text(
    60,
    84,
    "三个没有共享记忆的 AI 工具，靠文件协作写出一篇数字不出错的论文",
    14.5,
    MUTED,
)
text(1140, 52, "v0.1.0", 12.5, MUTED, 400, "end")

# ------------------------------------------------------------------ 公共区
rect(60, 110, 1080, 152, 14, "#0f172a")
text(88, 143, "shared/  ·  公共区", 15.5, "#f8fafc", 700)
text(88, 164, "三方共读；路线只有 Codex 能写，被改动会被 sha256 锚点发现", 12, "#94a3b8")

cards = [
    (88, 316, "route.md · outline.md", "科研路线与大纲 — 仅 Codex 写入"),
    (420, 316, "chat.md", "三方对话 — append-only，@寻址 · 回应 · 关闭"),
    (752, 360, "decisions.md · *.sha256", "已裁决结论 · 冻结锚点"),
]
for cx, cw, title, sub in cards:
    rect(cx, 180, cw, 68, 10, "#1e293b")
    text(cx + 18, 208, title, 13.5, "#f1f5f9", 600)
    text(cx + 18, 229, sub, 11.5, "#94a3b8")

# ------------------------------------------------------------------ 公共区 → 三方
for cx in (225, 600, 945):
    vline(cx, 266, 296, "#94a3b8")

# ------------------------------------------------------------------ 三方卡片
AGENTS = [
    (
        60,
        "C",
        "Codex",
        "定科研路线与大纲",
        CODEX,
        CODEX_BG,
        ["研究问题 · 创新点 · 技术路线", "实验设计与风险降级", "路线变更裁决 · 审稿意见"],
        "不做：写代码 · 编数据 · 写正文",
    ),
    (
        450,
        "D",
        "DeepSeek Harness",
        "实施研究 · 对账",
        DSH,
        DSH_BG,
        ["代码 · 数据 · 统计 · 作图", "证据台账 claims.csv", "数字核查 · 组装交付"],
        "不做：擅改路线 · 补数据 · 定文风",
    ),
    (
        840,
        "豆",
        "豆包电脑版",
        "定怎么讲 · 写正文",
        DB,
        DB_BG,
        ["叙事反馈：论文该写什么", "章节初稿 · 摘要 · 讨论", "中文润色 · 基金本子"],
        "不做：新增数字 · 文献 · 结论",
    ),
]

for x, icon, name, role, color, bg, duties, forbid in AGENTS:
    rect(x, 300, 300, 220, 14, bg, color)
    rect(x, 300, 300, 6, 3, color)
    add(f'<circle cx="{x + 48}" cy="356" r="22" fill="{color}"/>')
    text(x + 48, 363, icon, 16, "#ffffff", 700, "middle")
    text(x + 82, 350, name, 17.5, INK, 700)
    text(x + 82, 372, role, 11.5, MUTED)
    add(
        f'<line x1="{x + 22}" y1="392" x2="{x + 278}" y2="392" '
        f'stroke="{HAIR}" stroke-width="1"/>'
    )
    for i, duty in enumerate(duties):
        text(x + 24, 416 + i * 21, "·", 13, color, 700)
        text(x + 38, 416 + i * 21, duty, 12.5, BODY)
    text(x + 24, 493, forbid, 11.5, "#b91c1c")

# ------------------------------------------------------------------ 卡片间交接
harrow(366, 444, 468)
text(405, 456, "路线 · 大纲", 10.5, MUTED, 400, "middle")
harrow(756, 834, 468)
text(795, 456, "结果简报", 10.5, MUTED, 400, "middle")

# ------------------------------------------------------------------ 流水线
text(60, 566, "流水线", 14, INK, 700)
text(132, 566, "每一棒有明确的产出文件与通过条件", 12, MUTED)

STAGES = [
    ("G0", "立项", "user", USER, USER_BG),
    ("G1", "路线", "Codex", CODEX, CODEX_BG),
    ("G2", "大纲", "Codex", CODEX, CODEX_BG),
    ("G3", "实施研究", "DSH", DSH, DSH_BG),
    ("G4", "叙事反馈", "豆包", DB, DB_BG),
    ("G5", "成稿", "豆包", DB, DB_BG),
    ("G6", "审核", "Codex", CODEX, CODEX_BG),
    ("G7", "交付", "DSH", DSH, DSH_BG),
]
for i, (gid, label, owner, color, bg) in enumerate(STAGES):
    x = 60 + i * 136
    rect(x, 586, 124, 78, 10, bg, color, 1.2)
    text(x + 62, 610, gid, 11.5, color, 700, "middle")
    text(x + 62, 636, label, 14, INK, 600, "middle")
    text(x + 62, 655, owner, 10.5, MUTED, 400, "middle")

# ------------------------------------------------------------------ 三条防线
GUARDS = [
    ("路线完整性", "sha256 冻结锚点，动工前 check_shared --verify"),
    ("证据台账", "正文与叙事反馈的每个数字都可追溯到 claims.csv"),
    ("对话留痕", "chat.md 只追加，谁在等谁可判定"),
]
for i, (title, sub) in enumerate(GUARDS):
    x = 60 + i * 366
    rect(x, 700, 348, 62, 10, PANEL, HAIR, 1)
    text(x + 20, 726, title, 12.5, INK, 700)
    text(x + 20, 746, sub, 11.5, MUTED)

# ------------------------------------------------------------------ 页脚
text(60, 802, "安装", 12, MUTED, 700)
text(96, 802, "Windows", 10.5, "#94a3b8", 400, "start", FONT)
text(156, 802, r".\install.ps1 -Codex", 12, BODY, 400, "start", MONO)
text(376, 802, "macOS / Linux", 10.5, "#94a3b8", 400, "start", FONT)
text(486, 802, "./install.sh --codex", 12, BODY, 400, "start", MONO)
text(1140, 802, "MIT License", 12, MUTED, 400, "end")

add("</svg>")

OUT.write_text("\n".join(parts), encoding="utf-8", newline="\n")
print(f"已生成 {OUT}  ({OUT.stat().st_size} B)")
