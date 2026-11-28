---
name: reading15-knowledge-graph
description: 从两篇独立论文抽实体关系、绑定逐边证据，支持至少三个真实查询，并处理跨篇别名与冲突。
---

# 阅读15｜文献知识图谱构建

## 何时使用
需要围绕一个主题从论文集合抽实体与关系、做别名归一、绑定来源并执行查询时使用。可只做实体识别、实体对齐、关系抽取、来源绑定或图谱查询之一。

## 自动产出优先（v4）
本 Skill 的核心产物由 `scripts/solve.py` **一次运行内自动生成**，不依赖运行后再手工回填：
- 阅读类：块/章节/题注/表格/公式/引用位置直接从真实文件抽取，附页码与 block_id 锚点；
- 写作类：可安全自动化的改写（冗余表达、术语统一、编号连锁更新）直接落到成品文本；
- 结构化类：实体、关系、断言、参数、笔记卡片等由脚本按规则抽取并绑定来源。
Agent 的职责是**核对与修正**：抽查脚本产物与原文是否一致、补脚本无法判断的部分（语义、专业译名、作者主张强度）、把不确定项写入 `uncertainty`。
预算紧张时，脚本产物本身已是可提交的完整初稿；仍有余力再逐条打磨。

## 硬性规则
1. 实体必须是论文里真实出现的科研对象，不从常识补全。
2. 关系必须有证据支持，区分使用、比较、优于、支持、矛盾；共现不算关系。
3. 每个节点与每条边带独立 source_id、paragraph_id 与原文短引。
4. 位置是组织方 JATS 段落 ID，不是 PDF 页码；本包无 PDF 页码，不得把自建第 1 页称原 PDF 页。
5. 别名不强迫合并；不同论文的条件、样本、数值结果不得合成一个结论。
6. 不推断图像像素、补充附件、底层临床或实验数据。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到候选 nodes、edges、cross_source_conflicts 与 3 个查询结果。
2. 核对 `corpus-manifest.json`：确认两篇论文的 DOI、作者、来源哈希与许可证；根 DOI/标题/作者只属于第一篇。
3. 逐条验证候选实体与关系，删掉无证据项；关系类型与方向按原文判定。
4. 处理别名：给合并依据；同名但不同对象标 conflict，不合并。
5. 执行至少 3 个真实查询，展示结果子图、支撑证据与无法确定关系。
6. 导出可读图谱文件（JSON / GraphML 之一）并写增量更新规则。
7. 回填 result.json 全部字段与 status。

## 脚本输出
`nodes` / `edges`：带 source_id、paragraph_id、quote 的候选。`queries`：三个实际执行的查询。
`cross_source_conflicts`：跨篇同形但未必同对象的表面形式。

## 失败处理
- PDF 无法解析：标 unknown，不生成节点。
- 关系证据冲突：两条都保留并说明冲突。
- 查询无结果：返回空结果 + 原因，不编造。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：单篇论文的普通问答不触发；不得把 PDF 页码伪装成 JATS 段落 ID，不得推断图像像素或底层数据。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`：脚本已自动从本次真实检查项与结果字段生成各维度的 `skill_evidence` 初稿（标记为 auto_draft）。逐项确认或补充，让它准确指向 `result.json` 的具体字段或 `evidence[].locator`；确认后把 `status` 改为 confirmed。脚本无法观测的维度（如耗时）标记为 not_observable，需人工补充或保留 not observed，不得编造。对照维度：实体真实出现率、关系类型/方向准确率、别名归一正确率、节点与边证据覆盖率、查询结果可复核率、跨篇整理耗时。
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
- [ ] 两篇论文来源不串台
- [ ] 至少 3 个查询有结果与证据
- [ ] 别名合并与不合并都有依据
