---
name: writing09-methods-experiments
description: 从代码、配置、日志和数据说明抽取方法与实验要素，生成参数表、复现清单与缺口追问清单。
---

# 写作09｜方法与实验章节写作

## 何时使用
需要把零散实验材料写成可执行的方法与实验章节，或补写参数、数据集、对照与限制条件时使用。可只做参数来源、数据集与划分或复现清单之一。

## 硬性规则
1. 步骤、参数、数据集版本、划分、训练与评测条件必须与实际配置/日志/代码一致。
2. 不为段落顺畅补数值；材料缺口生成追问清单，不编造。
3. 参数表字段固定：名称、取值、单位、作用对象、来源（文件+行号或作者确认）。
4. 限制条件指向具体失效场景，不写套话。
5. 不提交预写章节。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `parameter_table`、`missing_categories`、`followup_questions`。
2. 逐条核实参数来源，`source_type` 写 config / log / code / author_confirmed；不在材料里的标 not reported。
3. 把零散记录整理成有序步骤，每步写输入、操作、输出、判断条件。
4. 训练/验证/测试流程分开写，硬件、软件版本、随机种子、重复次数分开列。
5. 对照实验写清基线对象与版本、是否同预算、评价指标与统计方式。
6. 生成复现清单与具体限制场景；把缺口整理成 `needs_human_confirmation`。
7. 回填 result.json 全部字段与 status。

## 脚本输出
`parameter_table`：参数名、值、来源文件与行号。`missing_categories`：未见的要素类别。`followup_questions`：追问清单。

## 失败处理
- 配置冲突：保留两版本并标冲突，不自行选一个。
- 数据集版本不明：列人工确认，不猜版本。
- 权限不足：status=partial，说明无法读取的材料。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：用户只要概念解释、不要求可执行章节与参数来源时不触发；配置冲突不得自行选一个。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`，按以下对照维度逐项回填 `skill_evidence`，让它指向 `result.json` 中的具体字段或 `evidence[].locator`：六类要素齐全度、参数来源可追溯率、条件一致性、复现清单可执行率、缺口追问覆盖率、补写返工轮次。
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
- [ ] 六类要素齐全（步骤/设置/参数/数据/对照/复现限制）
- [ ] 每个参数有来源
- [ ] 缺口都进追问清单
