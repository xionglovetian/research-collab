---
name: research-collab
description: Orchestrate a three-agent research pipeline in which Codex owns the research route and outline, DeepSeek Harness owns code, data, tooling and verification, and 豆包电脑版 owns Chinese academic prose plus narrative feedback on what the paper should say. The three exchange work through a shared read-only-by-convention folder and one append-only chat file in a single workspace, never through memory. Use for 三方协作、公共区、智能体对话、科研接力、跨工具分工、从选题到成稿的流水线, or whenever the user mentions Codex / 豆包 / DeepSeek 分工产出论文、基金本子、报告或 PPT 文本。
metadata:
  version: "0.1.0"
  license: "MIT"
  language: "zh-CN"
---

# 三方科研协作 — Router

本文件负责**通道、分工、公共区权限、阶段门和纪律**。模板与脚本按需加载，不要一次性全读。

## 0. 通道：一个公共区 + 一个对话文件

Codex 与豆包电脑版都是图形应用，三者之间**没有互相调用的接口，也没有共享对话记忆**；DSH 是唯一能可靠读写磁盘、执行代码、跑校验的一方。因此：

1. **通信通道 = 同一个工作目录里的文件。** 任何"上个工具说过什么"都不算数，只有落到文件里的才算数。
2. **`shared/` 是公共黑板。** 三方都能看；路线与大纲只有 Codex 能写；`chat.md` 是唯一例外，三方都追加。
3. **`shared/chat.md` 是三方对话。** 分歧、提问、进度、裁决都在这里留痕，替代"以为对方知道"。
4. **DSH 是调度者。** 只有它能读写工作区、跑脚本、对账，所以由它生成交接包、实施研究、代录豆包产出、把关数字。
5. **每次交接 = 四要素提示词包**：目标 + 输入 + 输出 + 禁区。缺一项这一棒就会跑偏。

## 1. 分工边界（越界是最常见的失败）

| 工具 | 负责 | 明确禁止 |
|---|---|---|
| **Codex** | 科研路线、技术路线、创新点、实验设计、章节大纲、**路线变更裁决**、以审稿人视角给意见 | 编造数据或文献；直接从零写大段正文；写代码 |
| **DSH**（当前 agent） | **按 Codex 路线实施研究**（代码/数据/统计/作图）、文献检索、结果台账、一致性校验、生成交接包、代豆包落盘、组装交付物、维护 `shared/chat.md` 格式 | 擅自改路线或大纲；凭空补数据；替豆包定稿文风 |
| **豆包电脑版** | ①**叙事反馈**：读研究产出，判断论文该写什么、主故事是什么、哪些结论现在还写不出来；②章节初稿、摘要、讨论、基金本子、科普、PPT 文案 | 新增数字、新增文献、新增结论；把假设写成实证；把相关写成因果 |

灰色地带判据：**需要跑代码或读文件吗？** 需要 → DSH；**需要长程推理做取舍、定研究什么？** → Codex；**需要判断"这些结果该怎么讲"或长文语感？** → 豆包。

DSH 的实施顺序永远服从 `shared/route.md`，不服从任何一方在聊天里临时说的想法——想法要先经过 Codex 变成路线变更，再实施。

## 2. 路由表

| 任务 | 首选 | 备注 |
|---|---|---|
| 选题、创新点、技术路线、实验设计 | Codex | 给 brief + 已有数据清单，不给全文 |
| 章节大纲、每节需要哪些证据 | Codex | 产出必须能被 DSH 翻译成 claim 需求 |
| 路线中途要改 | Codex | 先抛到 `chat.md`，Codex 裁决后写进 `route.md` 与 `changelog.md` |
| 代码、数据处理、统计、作图、检索 | DSH | 结果一律落 `04_results/` 并登记台账 |
| **结果解读：论文该写什么、先讲哪个发现** | **豆包** | 拿结果简报 + 台账，产出 `05_draft/narrative_<日期>.md` |
| 中文章节初稿与续写 | 豆包 | 一次一节，附该节 claim 清单 |
| 中文学术润色、去 AI 味、压缩字数 | 豆包 | 禁用清单要比字数要求更醒目 |
| 英文 SCI 语言润色 | DSH | 走已装的 `nature-polishing` / `nature-writing` 系列 |
| 数字与事实一致性核查 | DSH | `scripts/claim_check.py` |
| 路线对齐、审稿意见 | Codex | 拿大纲 + 成稿节 + 台账 + 叙事反馈 |
| 交付物组装（Word/LaTeX/PPT） | DSH | 走 `07_final/` |

## 3. 公共区：由使用者自己建立

**公共区不随项目自动创建。** 它是三方交换文件的中枢，位置必须由使用者在 G0 阶段自己决定并手工建立：

- 可以放在项目内 `shared/`，也可以放在共享盘、网盘同步目录（`D:/OneDrive/科研共享/本项目`），只要三方都读得到；
- 建好后用 `init_workspace.py --shared-dir "<路径>"` 登记，路径写进 `state.yaml` 的 `shared_dir`；
- 脚本检测到目录不存在会**拒绝执行并给出 `mkdir` 指令**，不会替你创建。

`shared_dir` 是相对项目根的路径（如 `./shared`）或绝对路径。多个项目共用一个大目录时，务必一项目一个子目录，否则 `chat.md` 会互相污染。

> **读法约定**：本文件后续凡写作 `shared/xxx` 的地方，都指"**公共区里的** `xxx`"，真实路径一律以 `state.yaml` 的 `shared_dir` 为准。给 Codex / 豆包生成交接包时，`{公共区}` 必须替换成实际路径；**豆包读不到文件，给它的包里只能放内容、不能只放路径**。

**没有公共区就不要进入 G1**——路线、大纲、对话全都写在那里。

| 文件 | 谁写 | 其他人 |
|---|---|---|
| `route.md` | 仅 Codex | 只读 |
| `outline.md` | 仅 Codex | 只读 |
| `changelog.md` | 仅 Codex | 只读 |
| `route.sha256`、`outline.sha256` | 仅 DSH 冻结时写 | 只读 |
| `chat.md` | **三方都追加，永不修改** | — |
| `decisions.md` | DSH 沉淀 | 只读 |

**为什么不是操作系统权限**：三个工具跑在同一个 Windows 用户下，NTFS ACL 区分不了它们，"只有 Codex 能改"没有技术强制力。所以用可检查的约束替代：

1. **契约**：非 Codex 一律不写路线文件；DSH 即使被要求在对话里"顺手改一下路线"，也拒绝，改为提示走变更流程。
2. **哈希锚点**：路线/大纲定稿后跑 `python scripts/check_shared.py --freeze`，把 sha256 写进 `shared/*.sha256`。
3. **动工前校验**：DSH 每次开始实施前跑 `python scripts/check_shared.py --verify`。**哈希不符 → 立即停下、报告差异、问用户**，绝不在被改过的路线上继续实施。
4. **变更留痕**：真要改主线，Codex 在 `chat.md` 抛裁决，改完 `route.md` 后在 `changelog.md` 记一笔，DSH 重新 `--freeze`。

## 4. 对话文件：`shared/chat.md`

三方共用的对话流，**只能追加，不能修改或删除他人消息**。完整协议（编号、类型、@寻址、回应、关闭、归档）见 `references/chat-protocol.md`，要点：

- 每条消息固定头：`## #NNN · YYYY-MM-DD HH:MM · 作者 · 类型`
- 要让谁回应就 `@谁`；回应写 `回应: #NNN`；结束了写 `关闭: #NNN`
- 类型只用：提案 / 进度 / 提问 / 反馈 / 阻塞 / 裁决
- 只记**决定与分歧**，不记流水账；结论沉淀进 `decisions.md`
- **豆包读不到文件**，DSH 在给它的包里必须贴入相关消息原文

`python scripts/check_shared.py --for dsh` 会列出所有还在等 DSH 回应的消息，动工前先清空自己的待回应项。

## 5. 流水线与阶段门

```
G0 立项 ─► G1 路线(Codex) ─► G2 大纲(Codex) ─► G3 实施研究(DSH)
                                                    │
   G7 交付 ◄─ G6 审核(Codex) ◄─ G5 成稿(豆包) ◄─ G4 叙事反馈(豆包) ◄┘
```

| 门 | 名称 | 通过条件 | 谁判 |
|---|---|---|---|
| **G0** | 立项 | ①使用者已**自己建立公共区目录**并用 `--shared-dir` 登记进 `state.yaml`；②`00_brief/brief.md` 填齐：题目、用途、目标刊物/字数、语言、已有数据、deadline、术语表 | 用户 |
| **G1** | 路线 | `shared/route.md` 含研究问题、创新点、分阶段技术路线（每阶段有验收标准）、证据需求清单；用户确认后 `--freeze` | 用户 |
| **G2** | 大纲 | `shared/outline.md` 每节标明目的、字数、需要的 claim；与 route 一致 | DSH 对照 route |
| **G3** | 实施研究 | 按 route 逐阶段实施；每个阶段产出进 `04_results/`、数字进 `claims.csv`、进度发 `chat.md`；大纲所有 claim 需求或有结果、或被明确标为缺口 | DSH |
| **G4** | 叙事反馈 | 豆包读结果简报，产出 `05_draft/narrative_<日期>.md`：主故事、各节该写什么、哪些结论还写不出来、缺哪些证据 | 用户 + Codex 复核 |
| **G5** | 成稿 | 豆包按 narrative + outline 逐节产出 `05_draft/v<N>_<section>.md`，每节 `claim_check.py` 通过 | DSH |
| **G6** | 审核 | Codex 出 `06_review/review_<日期>.md`（对齐性 + 过度声称 + 审稿追问）；问题回 G5 局部重写 | 用户 |
| **G7** | 交付 | `07_final/` 组装完成，格式与图注检查通过，终稿数字与台账一致 | 用户 |

**G4 是这条流水线的关键改进**：Codex 定的是"研究什么"，豆包定的是"这些结果该怎么讲"。两者分开，才不会出现"数据做出来了但论文写成流水账"或"大纲很漂亮但没有结果支撑"。

G4 之后若豆包指出关键证据缺失，允许回到 G3 补做一次；但补做范围只能来自 route 或其变更裁决，不许临时起意开新方向。

## 6. 证据纪律（本 Skill 的核心价值）

写作环节最大的风险不是文笔，是**数字漂移**：为了句子通顺，把 `92.3%` 写成"超过九成"、把"估计"写成"证明"、把"某地样本"写成"普遍规律"。

1. **一切可写进正文的数字，必须先登记进 `04_results/claims.csv`**，字段见 `references/evidence-ledger.md`。没登记的数字，豆包不许写。
2. **每条 claim 带强度标签**，决定它允许出现在哪、允许用什么动词：

   | 强度 | 含义 | 允许措辞 | 允许位置 |
   |---|---|---|---|
   | `measured` | 本实验/本数据直接测得 | 提高/降低/达到（可给数值） | 结果、摘要、讨论 |
   | `derived` | 由 measured 计算或推断 | 据此推算/折算（需注明口径） | 结果、讨论 |
   | `literature` | 来自他人文献 | 已有研究表明（必须带引文） | 引言、讨论 |
   | `assumption` | 假设或估算 | 估计/假定/大约 | 讨论、局限性；**禁止进摘要结论** |

3. **禁止外推梯度**：相关→因果、观察到→已证明、小样本→普遍、本地区→全国。要升级必须有 DSH 的统计结果支撑。
4. **叙事反馈同样受约束**：豆包在 G4 说"论文主张 X"，必须附 claim 编号作依据；提不出编号的主张，只能写成"建议补做"，不能写成"主要发现"。
5. **每个数值必须可追溯**到 `04_results/` 下的文件。豆包交稿后跑 `python scripts/claim_check.py --draft <file> --claims 04_results/claims.csv`，未匹配数字视为疑似幻觉。

## 7. 每次交接怎么做（DSH 的操作序列）

1. **读状态**：`state.yaml` → 当前阶段 → 本棒 owner。
2. **读对话**：`shared/chat.md` 末尾若干条 + `check_shared.py --for dsh`，把等自己回应的项处理掉或在包中带上。
3. **验完整性**：`check_shared.py --verify`。路线哈希不符 → 停手问用户。
4. **备课**：只挑这一棒需要的输入（给 Codex 别塞全文；给豆包只给本节大纲 + 本节 claim 清单 + 术语表 + 相关 chat 原文）。
5. **出包**：写 `handoffs/<阶段>_<目标>_<日期>.md`，四要素齐全。**能用脚本就别手搓**：

   ```powershell
   python scripts/make_brief.py --project . --stage G4 --to doubao                # 叙事反馈包
   python scripts/make_brief.py --project . --stage G5 --to doubao --section 3.2  # 某节初稿包
   python scripts/make_brief.py --project . --stage G1 --to codex                # 路线包
   ```

   它从 `state.yaml`、公共区的 `route.md` / `outline.md`、`04_results/claims.csv` 自动拼装，给豆包的包必定带全内容与禁写清单（**只写路径的包等于没给**）。写正文时 `assumption` 类证据会被自动排除在可用证据之外。手写时按 `references/handoff-templates.md` 的模板，豆包的包必须含**禁用清单**和 `[待补:xxx]` 占位符。
6. **收产出**：豆包若不能存文件，让用户贴回对话，由 DSH 写入并在文件头记 `saved-by: dsh`。
7. **入库校验**：文件名、章节层级、字数、占位符残留、数字一致性；不过则附具体修改指令退回。
8. **发进度**：在 `chat.md` 追加一条 `进度` 或 `反馈`，让 Codex 与豆包（经 DSH 转述）知道发生什么。
9. **更新状态**：推进 `state.yaml` 的 stage 与 `next_actions`。这一步做完才算交接结束。

## 8. 恢复（新会话 / 换工具接手）

按序读，禁止凭记忆：

1. `state.yaml` — 在哪一棒、谁负责、卡在哪
2. `shared/chat.md` 末尾 — 最近发生了什么、是否有未决分歧
3. `shared/decisions.md` — 已裁决结论
4. 只读当前阶段需要的文件 + 上游冻结产物

**"下一步做什么"永远写在 `state.yaml.next_actions` 里**，因为它是唯一对三方都可见的进度源。

## 9. 反模式（出现即停手）

- ❌ 非 Codex 直接改 `shared/route.md`（包括 DSH "顺手优化一下"）→ 破坏唯一权威路线。
- ❌ DSH 不校验哈希就在被改过的路线上实施 → 返工找不出原因。
- ❌ 绕过 `chat.md`，在各自窗口里"私聊" → 换工具即丢，等于没说过。
- ❌ chat.md 变成流水账 → 只记决定与分歧，结论进 `decisions.md`。
- ❌ 让豆包"顺便补一下数据"或"把这段实验补完整" → 必进幻觉。数据只能来自 DSH。
- ❌ 没建台账就让豆包写结果节或做叙事反馈 → 数字漂移无法定位。
- ❌ 把原始数据丢给豆包让它自己找重点 → 它读不到文件；必须给结果简报。
- ❌ 把一篇稿子丢给单个工具一次生成 → 不可追溯，审稿必挂。
- ❌ 改稿时整篇重写 → 只重写被判问题的那一节。
- ❌ 把 Codex 的意见直接当定论执行 → 冲突时用户裁决，并记进 `chat.md`。

## 10. 首次使用 / 新项目初始化

**第一步：使用者自己建立公共区**（脚本不代建）

```powershell
mkdir "<项目目录>\shared"                 # 或放在共享盘：mkdir "D:\OneDrive\科研共享\本项目"
```

**第二步：初始化项目并登记公共区**

```powershell
python "${SKILL_DIR}/scripts/init_workspace.py" "<项目目录>" `
  --title "项目名" --target "中文核心期刊" --language zh `
  --shared-dir "<项目目录>\shared"
```

会建好 `00_brief/ … 07_final/`、`state.yaml`、台账表头与项目模板，**并往你建的公共区里放入** `route.md`、`outline.md`、`chat.md`、`decisions.md`、`changelog.md`，最后打印下一棒。

- 若 `--shared-dir` 指向的目录不存在，脚本**报错退出（exit 3）并给出 `mkdir` 指令**，绝不替你创建。
- 不传 `--shared-dir` 时只建项目骨架，并提示你去建公共区；之后用 `--fill --shared-dir <路径>` 补齐。
- 已有内容默认拒绝覆盖；`--fill` 只补缺失文件，但会更新 `state.yaml` 的 `shared_dir`。

常用校验（公共区位置从 `state.yaml` 自动读取，也可用 `--shared` 覆盖）：

```powershell
python "${SKILL_DIR}/scripts/check_shared.py" --project "<项目目录>" --verify    # 路线是否被人动过
python "${SKILL_DIR}/scripts/check_shared.py" --project "<项目目录>" --for dsh  # 谁在等我回应
python "${SKILL_DIR}/scripts/check_shared.py" --project "<项目目录>" --freeze   # Codex 定稿后冻结
python "${SKILL_DIR}/scripts/claim_check.py" --draft 05_draft/v1_results.md --claims 04_results/claims.csv
```

## 11. 按需加载

| 需要什么 | 读哪个 |
|---|---|
| 对话文件协议：编号、类型、@寻址、回应/关闭、归档 | `references/chat-protocol.md` |
| 给 Codex / 豆包的确切提示词模板、收取与退回话术 | `references/handoff-templates.md` |
| 豆包装不了 Skill，它怎么参与（常驻纪律 + 粘贴包） | `integrations/doubao.md` |
| 台账字段、强度判定、如何从结果生成台账 | `references/evidence-ledger.md` |
| 目录树、每个文件的契约、`state.yaml` 全字段 | `references/workspace-layout.md` |
| 初始化 / 生成交接包 / 完整性校验 / 数字核查 | `scripts/*.py` |

按当前阶段取一个文件即可，不要为"读全"而加载 `references/`。
