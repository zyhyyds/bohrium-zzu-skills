---
name: writing08-intro-related-work
description: 基于给定材料写引言与相关工作，按问题/方法/数据分组比较，从已引文献推导研究空白并核对贡献证据。
---

# 写作08｜引言与相关工作写作

## 何时使用
需要起草可直接入稿的研究背景、相关工作、研究空白与贡献表述时使用。可只做相关工作分组或贡献表述核对之一。

## 硬性规则
1. 背景指向真实研究脉络与具体未解决问题，不写「近年来受到广泛关注」式空转。
2. 相关工作按问题、方法或技术路线分组比较，不逐篇摘要拼接。
3. 研究空白从已引文献的共同限制推出，并说明本文如何填补。
4. 贡献表述与本文方法、图表、实验结果一一对应，不夸大适用范围。
5. 引用元数据真实，论断与引用一一对应；不提交预写成稿。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `claim_table`、`gap_candidates`、`contribution_candidates`。
2. 逐条核对 claim 的转述是否与原文一致；保留 locator 与 citations。
3. 按 `grouping_axis` 把相关工作分组，并用同一比较维度写取舍，不按时间罗列。
4. 从 gap_candidates 推导研究空白；无显式限制词时从引文覆盖与实验条件推导，并写明推导链。
5. 把 contribution_candidates 与正文图表/实验对应；找不到支撑的降级或删除。
6. 生成成稿 + `claim_table` 来源映射 + 引用核对清单。
7. 回填 result.json 全部字段与 status。

## 脚本输出
`claim_table`：论断、来源、引用标记、主题词。`gap_candidates`：限制/未解决线索。`contribution_candidates`：贡献句。

## 失败处理
- 文献库为空：status=partial，只写能由材料支撑的背景。
- 引用查不到原文：列入人工确认，不作为事实。
- 目标期刊格式未知：采用输入指定格式或列出待确认项。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：用户只要文献清单、不要求成稿或贡献核对时不触发；文献库为空时不得编造相关工作。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`，按以下对照维度逐项回填 `skill_evidence`，让它指向 `result.json` 中的具体字段或 `evidence[].locator`：转述准确率、分组合理性、空白推导成立率、贡献—证据对齐率、引用覆盖率、成稿返工轮次。
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
- [ ] 四部分齐全且彼此承接
- [ ] 空白由已引文献推出
- [ ] 贡献有正文证据
