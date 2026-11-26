---
name: writing04-citation-management
description: 稿件引用定位、编号连锁更新、文献去重、格式映射与来源核验，交付可继续编辑的稿件和同步文献表。
---

# 写作04｜参考文献与引用管理

## 何时使用
需要把真实稿件与真实文献库做引用插入、编号更新、去重、格式转换或来源核验时使用。可只做一个具体问题，优先做编号同步或去重。

## 硬性规则
1. 引用插到真正需要来源支撑的论断句，不整段末尾或图表注附近。
2. 插入、删除、调序后，正文编号与文末列表同步，编号连续、样式统一。
3. 去重给出可解释合并判据（DOI、题名、预印本/正式版），避免误合并同名作者不同文献。
4. 每条引用真实存在、元数据准确；论断与所引文献主题结论匹配。
5. 不提交预写结果。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `references`、`citation_points`、`numbering_map`、`duplicates`、`unused_entries`、`missing_entries`、`numbering_gaps`。
2. 逐句判断 `citation_points` 位置是否恰当；需要移动的记录 change 与理由。
3. 按 `numbering_map` 执行连锁重排，同步正文标记、文末列表、图表注与附录引用。
4. 对 `duplicates` 逐条确认依据，写出保留项与合并项；不确定的列人工确认。
5. 用 DOI 或原文核对元数据；无法解析 DOI 的标 unknown，不编造。
6. 输出可编辑稿件与同步文献表，附来源/修改记录。
7. 回填 result.json 全部字段与 status。

## 脚本输出
全部为确定性检查结果，详见上一步列表；`changes` 需由 Agent 执行后回填。

## 失败处理
- DOI 解析失败：保留原条目并标 unknown。
- 编号冲突：先输出冲突列表，不自动改。
- 文献库字段缺失：列人工补全项。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：用户只要文献摘要、不要求引用整理或稿件编辑时不触发；DOI 解析失败不得编造元数据。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`，按以下对照维度逐项回填 `skill_evidence`，让它指向 `result.json` 中的具体字段或 `evidence[].locator`：引用位置准确率、编号连续与同步率、去重判据可解释率、元数据准确率、论断—引用匹配率、逐条核对耗时。
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
- [ ] 正文与文末编号一致
- [ ] 去重依据可解释
- [ ] 每条引用能回到真实文献记录
