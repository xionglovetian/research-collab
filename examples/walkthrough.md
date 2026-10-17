# 一次完整的端到端演练

下面是一次真实跑通的流程（输出为实际终端结果，项目名已脱敏）。你可以照着走一遍，判断这套东西是否适合你的工作方式。

---

## 0. 初始化

```powershell
python "$env:USERPROFILE\.agents\skills\research-collab\scripts\init_workspace.py" `
  "C:\Users\me\Desktop\水稻氮肥" --title "施肥强度对水稻产量稳定性的影响" `
  --target "中文核心期刊" --language zh --word-budget 8000
```

```
工作区：C:\Users\me\Desktop\水稻氮肥
新建文件 10 个：
  + 00_brief/brief.md
  + 00_brief/glossary.md
  + shared/route.md
  + shared/outline.md
  + shared/chat.md
  + shared/decisions.md
  + 04_results/claims.csv
  + state.yaml
  + shared/changelog.md
  + README.md
```

填完 `00_brief/brief.md`（研究问题、核心论点、已有数据、硬约束）才算过 G0。

---

## 1. G1 路线：Codex 出方案

DSH 生成 `handoffs/G1_codex_20261017.md`（四要素齐全），你复制进 Codex。Codex 把结果写进 `shared/route.md`，并在 `chat.md` 留一条消息：

```markdown
## #001 · 2026-10-17 10:05 · codex · 进度

@dsh @doubao

路线与大纲已写入 `shared/route.md`、`shared/outline.md`。

- 研究问题：施肥强度如何影响产量及其稳定性
- 证据需求：见 route「需要的证据清单」，共 6 条
- 请 @dsh 在 G3 前判断哪些缺数据；请 @doubao 在 G4 前看完大纲准备叙事反馈
```

你确认路线后，DSH 冻结：

```powershell
python check_shared.py --freeze
```

```
[✓] 已冻结 route.md  594e8077f787
[✓] 已冻结 outline.md  a5d3256ac063

提示：重新冻结前，确认 chat.md 已有裁决、changelog.md 已记录变更。
```

**从此任何人改动 `route.md` 都会被 DSH 发现。**

---

## 2. 中途遇阻：走对话，不走私下

DSH 实施时发现证据需求第 4 条没有数据，抛一条阻塞：

```markdown
## #002 · 2026-10-17 11:20 · dsh · 阻塞

@codex
回应: #001

证据需求第 4 条（2023 年产量）在 02_data/raw/ 中不存在，无法实施。
① 确认删去该节；② 授权我用公开统计年鉴替代并在台账标 literature。
```

Codex 裁决，DSH 照办并重新冻结：

```markdown
## #003 · 2026-10-17 12:02 · codex · 裁决

@dsh
回应: #002

走方案 ②，只用省级年鉴，台账 strength 标 literature，allowed_in 只给 intro;discussion。
route.md 已同步更新，请重新 freeze。
```

查看还有谁在等自己：

```powershell
python check_shared.py --for dsh
```

```
== 等待 @dsh 回应的消息 ==
  #003 · 2026-10-17 12:02 · codex · 裁决
        走方案 ②，只用省级年鉴，台账 strength 标 literature…

共 3 条消息，下一个编号 #004
```

---

## 3. G3 实施研究

DSH 按 route 逐阶段写代码、跑统计、作图，产出进 `04_results/`，并把每个可信数字登记进台账：

| id | claim | value | unit | strength | source | allowed_in |
|---|---|---|---|---|---|---|
| C01 | 处理组平均产量 | 92.3 | % | measured | tables/main.csv:row2 | results;abstract;discussion |
| C02 | 产量较对照提升幅度 | 18.6 | % | measured | tables/main.csv:row3 | results;abstract;discussion |
| C04 | 氮肥利用率区间 | 85–93 | % | derived | tables/n.csv:row7 | results |
| C05 | 预计 2030 年产量提升 | 12.5 | % | assumption | 情景推算 | discussion |

然后报一条进度，@豆包：

```markdown
## #004 · 2026-10-17 16:40 · dsh · 进度

@codex @doubao
回应: #003

G3 完成。产出 04_results/tables/main.csv、台账 12 条（C01–C12）。
关键结果：处理组产量 92.3%，较对照高 18.6%（C01、C02，measured）。
@doubao 结果简报见 handoffs/G4_doubao_20261017.md
```

---

## 4. G4 叙事反馈：豆包定"该写什么"

这一棒**不写正文**。DSH 把结果简报整理进 `handoffs/G4_doubao_*.md`（豆包读不到文件，所以要把表格和图描述都贴进去），豆包回答五个问题：

```markdown
## 主故事
产量提升主要来自穗数而非粒重。依据：C03、C05（均 measured）。

## 现在写不出来的
机制解释缺中介变量证据——台账无对应条目，讨论里只能写"提示"，不能写"证明"。

## 与大纲的冲突
大纲 4.2 节要求解释生理机制，现有结果支撑不了。建议：降级为"讨论中的提示"，
或将机制检验列为后续工作。
```

冲突项由 DSH 抛回 `chat.md`，Codex 裁决，结论沉淀进 `shared/decisions.md`。

---

## 5. G5 成稿 → 数字核查

豆包写完结果节，DSH 落盘 `05_draft/v1_results.md` 并核查：

```powershell
python claim_check.py --draft 05_draft/v1_results.md --claims 04_results/claims.csv
```

正常稿：

```
== 草稿核对：05_draft/v1_results.md ==
   字数约 1240，数值 14 个，占位符 0 处
[✓] 已追溯 14 个数值
[✓] 所有数值均可追溯到台账
[✓] 无 claim 强度升级
[·] 台账未使用条目 1 条（确认是否有发现漏写）
结论：通过
```

出问题的稿：

```
[✗] 未匹配数值 1 处 —— 疑似编造，必须逐条处理：
    · 87.5  …本研究证明，处理组产量提升了 87.5%…
[!] 强度违规 2 处：
    · [assumption-in-abstract] C05 强度为 assumption，不得出现在摘要/结论中
    · [strength-upgrade] C05（assumption）被写成「证明」
[·] 待补占位符 1 处（成稿前必须清零）：
    · [待补:2024年验证数据]
结论：不通过
```

退出码 `1`，可直接串进流水线当门禁。

---

## 6. G6 审核 → G7 交付

Codex 拿到「冻结路线 + 大纲 + 叙事反馈 + 成稿 + 台账」，只查四类问题：对齐、过度声称、证据缺口、审稿人会追问什么。问题回 G5 局部重写，不整篇重来。

最后 DSH 在 `07_final/` 组装 Word / LaTeX，并复核终稿数字与台账一致。

---

## 整轮下来文件长什么样

```
水稻氮肥/
├── state.yaml                 # G7，owner: user
├── shared/
│   ├── route.md  route.sha256 # 冻结哈希 594e8077f787
│   ├── outline.md
│   ├── chat.md                # 12 条消息，议题全部关闭
│   ├── decisions.md           # 3 条已裁决结论
│   └── changelog.md           # 1 条路线变更
├── 04_results/claims.csv      # 12 条证据
├── 05_draft/narrative_20261017.md
├── 05_draft/v1_results.md  v2_results.md  v1_abstract.md
├── 06_review/review_20261018.md
├── 07_final/manuscript.docx
└── handoffs/                  # 每一步的提示词包，可复盘
```

任何一个工具换新会话，只要读 `state.yaml` → `chat.md` 末尾 → `decisions.md`，就能接着干。
