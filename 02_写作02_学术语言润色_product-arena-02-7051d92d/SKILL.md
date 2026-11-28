---
name: writing02-language-polish
description: 最小编辑式学术语言润色，输出润色全文与逐句修改说明，并守住限定强度、数据、单位和引用编号。
---

# 写作02｜学术语言润色

## 何时使用
需要对真实稿件做语法、术语、学术语气或中英文表达润色，且要求「润色后完整文本 + 逐句修改说明」时使用。只聚焦一个具体问题（如术语一致性或语义保持）。

## 自动产出优先（v4）
本 Skill 的核心产物由 `scripts/solve.py` **一次运行内自动生成**，不依赖运行后再手工回填：
- 阅读类：块/章节/题注/表格/公式/引用位置直接从真实文件抽取，附页码与 block_id 锚点；
- 写作类：可安全自动化的改写（冗余表达、术语统一、编号连锁更新）直接落到成品文本；
- 结构化类：实体、关系、断言、参数、笔记卡片等由脚本按规则抽取并绑定来源。
Agent 的职责是**核对与修正**：抽查脚本产物与原文是否一致、补脚本无法判断的部分（语义、专业译名、作者主张强度）、把不确定项写入 `uncertainty`。
预算紧张时，脚本产物本身已是可提交的完整初稿；仍有余力再逐条打磨。

## 硬性规则
1. 最小编辑，不整段重写；原意、限定强度、数据、单位、引用编号、图表指向守恒。
2. 每处修改给原文、改文、修改类型、理由，第三方能判断该不该改。
3. 术语表驱动全篇回扫，缩写首次出现形式统一。
4. 材料不足、目标文体不明、术语表冲突要明确标注，不自行补全。
5. 不提交预写改稿。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `polish_worklist`。
2. 对每条问题给 revised 与 reason；不认同脚本候选的也要写理由，不能静默忽略。
3. 用同一术语表回扫全文，补做脚本未覆盖的术语漂移。
4. 生成 `polished_text` 与 `change_log`；每条 change 含 before/after/type/reason。
5. 用 `invariant_checks` 核对数字、引用、限定词；missing 必须解释或修正。
6. 标 `needs_human_confirmation`：专业术语译法、目标期刊风格、作者主张强度。
7. 回填 result.json 全部字段与 status。

## 脚本输出
`polish_worklist`：问题类型、匹配文本、规则、定位。`invariant_checks`：守恒核对。

## 失败处理
- 纯内容问答：不触发润色。
- 超长输入：分章处理并标进度，不截断丢段。
- 编码混乱：先规范化编码再处理，记录转换过程。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：纯内容问答、事实核查、要求整段重写或代写时不触发润色；材料不足时不得自行补全。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`：脚本已自动从本次真实检查项与结果字段生成各维度的 `skill_evidence` 初稿（标记为 auto_draft）。逐项确认或补充，让它准确指向 `result.json` 的具体字段或 `evidence[].locator`；确认后把 `status` 改为 confirmed。脚本无法观测的维度（如耗时）标记为 not_observable，需人工补充或保留 not observed，不得编造。对照维度：语法硬错误修正率、术语一致率、限定强度守恒率、数据/引用/图表指向守恒率、逐句说明完整率、返修轮次。
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
- [ ] 完整润色文本 + 逐句说明
- [ ] 限定词与数据未被偷偷改掉
- [ ] README 含术语表与风格指南格式
