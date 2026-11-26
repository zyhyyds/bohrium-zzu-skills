---
name: reading01-pdf-parsing
description: 解析真实科研 PDF 为带锚点的结构化块，聚焦一种版式问题，逐字保留原文并标出无法读取处。
---

# 阅读01｜文献文档解析

## 何时使用
给到科研 PDF 或论文文本，要求提取正文、章节、表格、公式、图表题注，并要求结果能回到原文页码或区块时使用。只聚焦一种版式问题（多栏顺序、跨页表格、章节层级、公式符号、扫描件 OCR 之一），不要试图做完整 PDF 系统。

## 硬性规则
1. 只读 `/input` 里的实际材料；不按题目标签猜内容，不凭常识补原文。
2. 每个解析块都必须带 `source` 与 `block_id` 锚点；不能定位的结论不要写。
3. 图表与公式按结构元素识别，不解释科学含义。
4. 加密、无文字层、乱码、图片型表格分别标注，不混为一类。
5. `status` 用 success / partial / unknown / refuse；部分完成要写明限制。
6. 不提交预写答案，所有结果必须由本次运行在 `/app/output` 生成。

## 工作流
1. 运行 `python scripts/solve.py --input /input --output /app/output`，得到 `inventory`、`blocks`、`structure_summary`。
2. 若输入有 PDF：用平台提供的 pdf-text-tool 读取文字层；低分辨率或扫描页用 pdf-render-tool + ocr-tool；把真实读取结果回填到 `blocks`，不要用脚本的文本清单冒充解析结果。
3. 针对你选的一个版式问题做修正：双栏按版面坐标排序；跨页表格合并行列并标 `continued_from`；章节按多级编号建树；公式保留上下标与希腊字母原文；OCR 结果逐行对照页面图像。
4. 逐块核对：正文、题注、脚注、参考文献是否逐字一致；页眉页脚是否误入正文；相邻段落是否被拼成一句。
5. 在 `result.json` 中回填题目 `output_contract` 要求的全部字段，并把每个解析块写进证据数组，锚点含文件名、页码或区块 ID。
6. 更新 `status` 与 `uncertainty`；无法判断的写 not reported，不写成事实。
7. 写 `README.md` 的适用范围、依赖、版本、限制；`GITHUB_URL.txt` 填公开链接。

## 脚本输出
`blocks`：块 ID、类型、文本、首行、来源文件。`structure_summary`：标题/题注/表格计数。
`order_checks`：标题与题注顺序，用于自检串栏或错序。

## 失败处理
- PDF 无文字层：走 OCR，并在 uncertainty 记录识别置信与人工核对项。
- 加密 PDF：status=refuse，说明无法读取的具体原因。
- 表格跨页：标 `continued_from` 与列对齐依据，不擅自合并不同表。

## 触发边界
- 触发：输入目录存在真实科研材料（论文文本、PDF、稿件、文献库、配置/日志或 LaTeX 工程），且任务要求产出本次运行的结构化结果并能回到原文/源码定位。
- 不触发：纯内容问答、不要求回到原文的改写请求、要求提交预写答案时，不触发本题流程。
- 触发后先运行脚本建立锚点与候选清单，再由 Agent 读取真实材料逐条核对与回填；不得跳过后一步直接交付脚本骨架。

## 增益证据与自检闸门
1. 脚本会在输出目录同时生成 `result.json`、`verification.json`、`comparison.json`、`audit.json`、`run.log`、`change_log.md`。
2. 检查 `audit.json`：`passed=false` 时禁止把 `result.json` 的 `status` 写成 `success`；先修复或写入 `uncertainty`，再重跑脚本。
3. 打开 `comparison.json`，按以下对照维度逐项回填 `skill_evidence`，让它指向 `result.json` 中的具体字段或 `evidence[].locator`：逐字提取完整率、阅读顺序正确率、表格行列归属准确率、公式符号保真率、锚点可回查率、人工校对耗时。
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
- [ ] SKILL.md 有 name/description frontmatter
- [ ] result.json 保留 output_contract 全部字段并含 case_id
- [ ] 每条关键结论有锚点
- [ ] README 含版本、依赖、限制、自查方法
- [ ] GITHUB_URL.txt 已填公开链接（无登录浏览器可打开）
