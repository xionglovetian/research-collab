# 工作区结构与文件契约

一个项目 = 一个目录。三方只认这个目录和公共区，不认对话记忆。

**公共区由使用者自己建立**，位置不固定：可以在项目内 `shared/`，也可以在共享盘或网盘同步目录。实际位置记在 `state.yaml` 的 `shared_dir`（相对项目根或绝对路径），所有脚本据此定位。下面的目录树按"公共区在项目内"画，放在项目外时把它当作 `<shared_dir>/` 即可。

---

## 一、目录树

```
<项目根>/
├── state.yaml                 # ★ 唯一进度源：阶段、owner、shared_dir、冻结哈希、下一步
├── 00_brief/
│   ├── brief.md               # 题目、用途、刊物、语言、字数、约束
│   └── glossary.md            # 术语中英对照 + 计量口径
├── 02_data/raw/               # 原始数据，只读，永不修改
├── 03_code/
│   ├── src/                   # 分析脚本
│   ├── make_claims.py         # 结果 → 台账生成器（幂等）
│   └── logs/
├── 04_results/                # 一切数字的唯一出处
│   ├── tables/
│   ├── figures/
│   └── claims.csv             # ★ 证据台账
├── 05_draft/                  # 豆包领地
│   ├── narrative_<日期>.md    # 叙事反馈：论文该写什么（G4）
│   └── v<N>_<section>.md      # 正文（G5）
├── 06_review/
│   ├── review_<日期>.md       # Codex 审稿意见
│   └── claim_check_<日期>.md  # DSH 核查记录
├── 07_final/                  # 交付物：docx / tex / pptx
└── handoffs/                  # 每棒的提示词包存档
```

**为什么 `shared/` 不带编号**：它是跨阶段的（G1 定、G2 改、G3 实施要读、G4/G5 写作要读、G6 审稿要对照），编号会误导人以为它只属于某一阶段。

---

## 二、`shared/` 的读写契约

| 文件 | 写入方 | 读取方 | 规则 |
|---|---|---|---|
| `route.md` | 仅 Codex | 全部 | 冻结后改主线须先走 `chat.md` 裁决 + `changelog.md` 留痕 |
| `outline.md` | 仅 Codex | 全部 | 同上 |
| `changelog.md` | 仅 Codex | 全部 | 只增不改 |
| `chat.md` | 全部 | 全部 | 只追加，见 `chat-protocol.md` |
| `decisions.md` | DSH | 全部 | 只增不改，一行一条 |
| `*.sha256` | 仅 DSH | 全部 | `check_shared.py --freeze` 生成；人工不得编辑 |

**没有操作系统强制**：三个工具同属一个 Windows 用户，ACL 区分不了它们。约束靠契约 + 哈希：

```powershell
python check_shared.py --freeze    # Codex 定稿后冻结，写 sha256
python check_shared.py --verify    # DSH 每次动工前校验，不符即停手报告
```

---

## 三、`state.yaml` 全字段

```yaml
project: {项目名}
created: 2026-01-01
updated: 2026-01-05
owner_of_current_stage: codex | dsh | doubao | user
shared_dir: ./shared           # 公共区位置：相对项目根或绝对路径；null 表示尚未建立
stage:
  current: G3                 # G0..G7
  name: 实施研究
  gate_met: false
frozen:                       # sha256 前 12 位，未冻结为 null
  route: a1b2c3d4e5f6
  outline: null
  claims: null
deliverables:
  target: 中文核心期刊论文
  language: zh
  word_budget: 8000
open_questions:
  - 样本量是否够支撑分组比较？（已抛 #012 待 codex 裁决）
next_actions:                 # ★ 任何工具接手先看这里
  - who: doubao
    what: 读结果简报，产出叙事反馈
    out: 05_draft/narrative_20260105.md
    needs: [handoffs/G4_doubao_20260105.md, 04_results/claims.csv]
blocked_on:
  - 缺 2023 年产量数据（#002 待 codex 裁决）
changes:                      # 冻结内容的变更记录，只增不改
  - date: 2026-01-04
    ref: "#003"
    what: 第 3 阶段改为先做敏感性分析
    why: 样本量不足以支撑分组比较
```

只改需要改的字段，保留其余；`updated` 每次必改。`open_questions` / `blocked_on` 应尽量带 chat 编号，便于追溯。

---

## 四、关键文件契约

### `00_brief/brief.md`
必须能独立回答：做什么、给谁看、多长、什么时候要、有什么数据、不能碰什么。**G0 未填齐不要往下走。**

### `shared/route.md`
固定小节：研究问题 / 创新点（≤3 条，可证伪）/ 技术路线（阶段化，每阶段有验收标准）/ 需要的证据清单 / 风险与降级 / 不建议做的方向。
「需要的证据清单」是 DSH 建台账与排实施顺序的输入。

### `shared/outline.md`
每节一行表格：`序号 | 标题 | 目的 | 字数 | 需要 claim | 关键图表`。写 `需新增:xxx` 的条目在 G3 必须变成台账条目或被删节。

### `04_results/claims.csv`
见 `evidence-ledger.md`。铁律：**正文与叙事反馈里任何数字都必须在这里有一行**。

### `05_draft/narrative_<日期>.md`（G4，豆包）
不是正文，是**写作决策**。必须回答：

1. 主故事是什么（一句话），依据哪几个 claim 编号；
2. 每个章节该写什么、不该写什么；
3. 哪些结论**现在写不出来**（缺什么证据）；
4. 建议的图表顺序与各图要证明什么；
5. 与 `shared/outline.md` 的冲突点（如果有）。

### `05_draft/v<N>_<section>.md`（G5，豆包）
- 版本号递增，**从不覆盖**旧版本。
- 文件头 YAML 记来源：

```markdown
---
section: results
version: 1
author: doubao
saved_by: dsh
claims_used: [C01, C04, C07]
claim_check: pass | fail | pending
word_count: 1240
---
```

### `06_review/review_<日期>.md`（Codex）
固定结论档位：接收 / 小修 / 大修 / 重做 + 一句话理由。**必须逐条给「位置 + 问题 + 具体改法」**，否则豆包无法执行。

### `handoffs/*.md`
一棒一个文件，四要素齐全，带 `上游：` / `下一棒：` 两行。

---

## 五、命名与版本纪律

- 日期一律 `YYYYMMDD`，不用 `1.2`、`final2`、`最终版`。
- 文件名只用小写英文 + 下划线，不用空格和中文（避免跨工具乱码与命令行转义）；目录名可中文。
- `07_final/` 只保留 `manuscript.docx`、`manuscript.tex`、`figures/` 这类稳定名，历史版本留在 git 里。
- 建议 `git init`（初始化脚本默认执行）：三方协作最大的浪费是"上一版被覆盖了"。
