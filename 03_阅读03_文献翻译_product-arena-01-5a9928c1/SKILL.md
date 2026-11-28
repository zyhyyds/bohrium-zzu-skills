---
name: reading03-translation
description: 术语表驱动的段落级文献翻译，保留数字单位与引用标记，输出双语对照和逐段核验记录。
---

# 阅读03｜文献翻译

## 何时使用
需要把真实科研论文或明确段落区间译成目标语言，并且要求术语一致、段落对应、引用与公式可回查时使用。允许只聚焦术语一致性、长文分段、双语对照或译文核验之一。

## 自动产出优先（v4）
本 Skill 的核心产物由 `scripts/solve.py` **一次运行内自动生成**，不依赖运行后再手工回填：
- 阅读类：块/章节/题注/表格/公式/引用位置直接从真实文件抽取，附页码与 block_id 锚点；
- 写作类：可安全自动化的改写（冗余表达、术语统一、编号连锁更新）直接落到成品文本；
- 结构化类：实体、关系、断言、参数、笔记卡片等由脚本按规则抽取并绑定来源。
Agent 的职责是**核对与修正**：抽查脚本产物与原文是否一致、补脚本无法判断的部分（语义、专业译名、作者主张强度）、把不确定项写入 `uncertainty`。
预算紧张时，脚本产物本身已是可提交的完整初稿；仍有余力再逐条打磨。

## 硬性规则
1. 术语表必须从原文抽取并**强制执行**，不能只写在提示词里。
2. 段落级一一对应，段号不得跳号或重复；跨页、跨栏、跨章节处要携带上下文。
3. 数字、单位、公式编号、图表编号、文献引用标记、否定与限定词必须守恒。
4. 每段译文给出译法依据与原文定位；译不准的列人工确认清单，不含混带过。
5. 不提交预写译文；译文必须由本次运行产生。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `glossary_candidates`、`segments`、`invariant_checks`。
2. 逐条确认术语译名，写进 `glossary_candidates[].suggested_translation`；同一术语在标题、摘要、正文、图注、结论中必须同译名。
3. 按 `segments` 逐段翻译，每段保留 `source`、`translation`、`anchor`。长段按语义边界再切，但段号仍与原段对应。
4. 回填术语表后做全篇回扫：搜索每个术语的所有变体，发现漂移就修正并记录 change。
5. 用 `invariant_checks` 核对数字、单位、引用编号、限定词；出现 missing 必须修正或标注需人工确认。
6. 输出 `needs_human_confirmation`：图片内公式、加密文字、原文残缺、语言混杂。
7. 更新 result.json 全部 output_contract 字段与 status。

## 脚本输出
`glossary_candidates`：术语、出现次数、定位。`segments`：待译段落与段号。
`invariant_checks`：源文/译文数字、引用、限定词差异。

## 失败处理
- 原文无文字层：标注 refuse 或 partial，不用 OCR 猜测冒充原文。
- 公式或表格为图片：保留占位标记并列入人工确认。
- 术语表内部冲突：列出冲突条目，不自行选一个。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：用户只问文献内容、不要求译文或双语对照时不触发；不按题目标签臆造原文。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`：脚本已自动从本次真实检查项与结果字段生成各维度的 `skill_evidence` 初稿（标记为 auto_draft）。逐项确认或补充，让它准确指向 `result.json` 的具体字段或 `evidence[].locator`；确认后把 `status` 改为 confirmed。脚本无法观测的维度（如耗时）标记为 not_observable，需人工补充或保留 not observed，不得编造。对照维度：术语一致率、段落完整率、段号对应关系、数字/单位/引用守恒率、逐段可回查率、人工校对耗时。
4. `baseline_observation` 保持 `not observed`，除非本次输入中确实包含基础 Agent 的可观察结果；平台会独立运行基础 Agent 对照，不得编造对照数值或分数。
5. 在 `change_log.md` 中说明本次相对"直接按题目自由发挥"多做了哪些可核验动作（锚点、守恒检查、编号同步、追问清单等）。
6. 回填完成后运行 `python scripts/solve.py --validate --output /app/output`。它会重审 `result.json` 与 `comparison.json`，更新 `audit.json` 和 `validation_report.json`；只有 `passed=true` 且 `status` 与审计结论一致时才算完成。


## 交付清单（对应评分点）
- 任务完成度：题目要求的全部动作与全部输入文件都已处理，输出不是候选骨架。
- 结果正确性：数字、单位、引用/图表编号、限定强度、主体关系方向逐项核对通过。
- 结果完整性：output_contract 全部字段保留；缺失项写 not reported 而不是留空或臆造。
- 结果可核验性：每条关键结论有 `evidence[].locator`，可回到文件/行号/段落/块 ID。
- 增益可验证性：`verification.json` 已通过，`comparison.json` 已用本次真实证据回填。
- 可靠体验：异常情形已在 `uncertainty` / `needs_human_confirmation` 中分类说明。

## 交付检查
- [ ] 术语表被真正回填且全篇一致
- [ ] 每段双语对照有锚点
- [ ] 数字/引用/限定词 check 无未解释的 missing
- [ ] README 含术语表格式与分段规则

## 异常处理矩阵

| 情况 | 处置 | 输出的 status |
|---|---|---|
| 输入为空 / 无正文 | 输出空结果并说明缺失 | `unknown` |
| 编码异常（GBK/GB18030） | 多编码探测；仍失败则记录文件名与原因 | `partial` |
| PDF 无文字层 / 扫描件 | 标注需 OCR，不伪造正文 | `partial` |
| 术语无法确定 | 保留原文并标注待确认 | `partial` |
| 重复运行 | 覆盖同名产物，结果确定可复现 | 同上次 |
