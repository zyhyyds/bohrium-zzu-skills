---
name: writing13-latex-compile
description: LaTeX 工程静态检查、编译错误定位与修复闭环，交付可编译可维护的 .tex 源码与复现记录。
---

# 写作13｜LaTeX 写作与编译

## 何时使用
需要把稿件迁入模板、修复编译错误、对齐公式表格引用或建立可重复构建时使用。可只做一个具体问题，如引用收敛或宽表处理。

## 硬性规则
1. 交付可编辑 .tex 源码，不把 PDF、截图或无法编译的片段当结果。
2. 报错定位到文件、行号、根因，不只贴第一条错误。
3. 公式符号与编号、表格数值与列宽、交叉引用与参考文献、模板必填项都要对齐原文意图与模板要求。
4. 记录 TeX 发行版、宏包与字体版本、编译命令与轮次。
5. 不提交预写编译结果。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `issues`、`compile_plan`、`environment_record`。
2. 按 severity 处理 issues；环境不匹配、缺宏包、缺字体分别记录，不混为一类。
3. 用平台 latex-compiler 按 `compile_plan` 真实编译；读完整日志定位级联错误根因。
4. 每修一处写 change：修改前、修改后、原因、影响的编译错误。
5. 检查 \cite/\ref 多遍编译收敛，.bib 条目与正文对应。
6. 对宽表、跨页表、公式长行做版式检查，输出真实渲染 PDF/PNG 预览。
7. 回填 result.json 全部字段与 status，附编译日志。

## 脚本输出
`issues`：文件、行号、严重性、类型、详情。`compile_plan`：建议编译轮次。`environment_record`：需记录的环境字段。

## 失败处理
- 模板类文件缺失：status=unknown，说明缺失项。
- 宏包不可用：给替代方案与版本记录，不静默删除引用。
- 编译超时：保存部分产物与日志，标 partial。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：只要公式含义解释、不要求可编译源码时不触发；不得把 PDF 或截图当交付物。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`，按以下对照维度逐项回填 `skill_evidence`，让它指向 `result.json` 中的具体字段或 `evidence[].locator`：编译成功率、错误根因定位准确率、修复正确率、公式/表格/引用对齐率、可复现构建记录完整率、定位报错耗时。
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
- [ ] 真实编译通过或有完整失败日志
- [ ] 源码可维护、结构清楚
- [ ] 环境与编译轮次可复现
