---
name: reading14-nanopublication
description: 把论文结论拆成可独立判真的原子断言，绑定最小充分证据与来源元数据，导出机器可读结构。
---

# 阅读14｜Nanopublication

## 何时使用
需要把一段科研结论转成断言—证据—来源三元组结构时使用。可只做断言拆解、证据绑定、来源元数据、质量检查或结构化导出之一。

## 自动产出优先（v4）
本 Skill 的核心产物由 `scripts/solve.py` **一次运行内自动生成**，不依赖运行后再手工回填：
- 阅读类：块/章节/题注/表格/公式/引用位置直接从真实文件抽取，附页码与 block_id 锚点；
- 写作类：可安全自动化的改写（冗余表达、术语统一、编号连锁更新）直接落到成品文本；
- 结构化类：实体、关系、断言、参数、笔记卡片等由脚本按规则抽取并绑定来源。
Agent 的职责是**核对与修正**：抽查脚本产物与原文是否一致、补脚本无法判断的部分（语义、专业译名、作者主张强度）、把不确定项写入 `uncertainty`。
预算紧张时，脚本产物本身已是可提交的完整初稿；仍有余力再逐条打磨。

## 硬性规则
1. 一条断言只表达一个可判真假的命题，保留原始条件与限定范围。
2. 证据取最小充分片段，必须能回到原文位置；区分直接证据与间接推论。
3. 主体、关系方向、年份、版本、DOI 来自输入材料，不凭常识补全。
4. 找不到支撑片段的断言保留并标 unsupported，不删改原文。
5. 导出字段与序列化形态固定，下游无需人工清洗。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `assertion_candidates` 与 `export_schema`。
2. 逐条判定粒度：含并列、因果、转折的候选继续拆分，直到每条只有一个主体和一个关系。
3. 为每条断言填 subject、relation、qualifier；关系类型用受控词表（support / improve / use / compare / contradict）。
4. 绑定最小证据片段：必须是原文连续短引 + source_id + 位置；间接推论标 indirect。
5. 补来源元数据：论文标识、作者、年份、版本、DOI，只取输入里真实存在的值。
6. 跑质量检查：断言过宽、证据不足、主体混淆、关系方向错误、来源缺失，逐条写判定依据。
7. 回填 result.json 全部字段与 status。

## 脚本输出
`assertion_candidates`：候选断言、来源、位置。`export_schema`：固定导出字段。`quality_rules`：检查规则。

## 失败处理
- 无文本层：status=unknown，不生成断言。
- 证据跨图表：标 indirect 并列入人工确认。
- 源内冲突：两条都保留，不合并。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：用户只要段落摘要或泛泛结论时不触发；无文本层时不得凭常识生成断言。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`：脚本已自动从本次真实检查项与结果字段生成各维度的 `skill_evidence` 初稿（标记为 auto_draft）。逐项确认或补充，让它准确指向 `result.json` 的具体字段或 `evidence[].locator`；确认后把 `status` 改为 confirmed。脚本无法观测的维度（如耗时）标记为 not_observable，需人工补充或保留 not observed，不得编造。对照维度：断言原子化粒度、主体/关系方向准确率、最小充分证据命中率、来源元数据完整率、导出可直接解析率、人工拆分耗时。
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
- [ ] 20 条以上断言样例或题集可复用
- [ ] 每条断言有主体、关系、限定、证据、来源
- [ ] 受控词表与字段字典齐全
