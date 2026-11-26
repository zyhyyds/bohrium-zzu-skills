---
name: reading10-structured-notes
description: 按论文原章节生成字段化、可检索、可回链的文献笔记，保留研究问题、数据、方法条件、发现与局限。
---

# 阅读10｜文献总结与结构化笔记

## 何时使用
需要把一篇真实论文变成可继续复用的结构化笔记，而不是通读摘要时使用。可选择章节总结、论文卡片、知识点提取或来源保留之一作为主攻方向。

## 硬性规则
1. 笔记骨架跟论文自身章节与论证顺序，不套通用摘要模板。
2. 五个字段必填：research_question、data、method_conditions、main_findings、limitations；缺失写 not reported。
3. 每条关键笔记带锚点：章节、段落、页码或图表位置。
4. 尤其保留让结论成立的前提条件，不把限定条件丢掉。
5. 不提交预写笔记。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到按章节切分的 `notes` 骨架。
2. 逐节读取原文，回填 `summary` 与五个字段；字段内容必须与原文数值、变量、条件一致。
3. 每条笔记补 `anchor`：优先用原文 JATS 段落 ID 或真实页码；没有就写文件名 + 行号，不自造页码。
4. 合并重复知识点时保留所有来源锚点，不把不同论文的条件合成一个结论。
5. 建立 `search_index_hint` 所需的关键词、缩写与同义表述映射。
6. 用 `needs_human_confirmation` 标记扫描件、图表公式缺失、超长文截断等情况。
7. 回填 result.json 全部字段与 status。

## 脚本输出
`notes`：note_id、章节、锚点、原文引文、空字段骨架。`field_dictionary`：字段定义。

## 失败处理
- 无章节标题：按段落聚类并在 uncertainty 说明切分依据。
- 双栏错序：先按版面顺序修复再抽笔记，锚点指向修复后的块。
- 非中文论文：保留原文术语并给译名，译名进人工确认。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：只需一句话概括、不要求结构化字段与来源回链时不触发；不套通用摘要模板替代论文自身结构。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`，按以下对照维度逐项回填 `skill_evidence`，让它指向 `result.json` 中的具体字段或 `evidence[].locator`：章节骨架对齐度、五字段完整率、论断/数值准确率、锚点可回查率、笔记可检索性、单篇整理耗时。
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
- [ ] 笔记骨架与论文章节对齐
- [ ] 每条关键笔记可回到原文
- [ ] 局限字段不是套话，指向具体条件
