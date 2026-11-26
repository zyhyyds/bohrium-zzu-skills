# 阅读01｜文献文档解析

- 对应赛题 ID：`product-arena-08-3027d350`
- 主攻方向：多栏/表格/公式/章节结构之一，逐块回原文定位
- 交付形态：可被 Agent 加载的 Skill（不是预写答案）

## 文件
- `SKILL.md`：Skill 本体，含触发条件、硬规则、工作流、失败处理。
- `scripts/evidence_core.py`：十题共用的确定性内核（输入盘点、锚点、不变量、结果构建）。
- `scripts/solve.py`：本题专用检查与骨架生成脚本，Python 3 标准库即可运行。
- `templates/result_template.json`：输出字段骨架；实际字段以 case.json 的 output_contract 为准。
- `examples/mini_example.md`：格式示意，明确标注为示例，不是正式案例答案。
- `GITHUB_URL.txt`：提交前必须替换为真实 GitHub 公开链接。

## 本地试跑
```bash
python scripts/solve.py --input ./sample_input --output ./sample_output
```
容器内默认读取 `/input`，写入 `/app/output`；也可用 `BOHRIUM_INPUT`、`BOHRIUM_OUTPUT` 环境变量覆盖。

## 依赖与限制
- Python 3.9+ 标准库；不需要第三方包。
- 脚本只做确定性盘点和检查，不替代 Agent 对真实材料的阅读与判断。
- 正式案例、白板与对照结果由平台提供，本目录不含也不应包含预写答案。

## 提交前检查
1. `result.json` 保留 output_contract 全部字段并含 case_id。
2. 每个关键结论有真实锚点；不确定项写进 uncertainty。
3. README 的版本、依赖、适用范围、限制与自查方法与实际一致。
4. 用未登录浏览器验证 GITHUB_URL.txt 的链接可见。

## 评分点对照与可复用资源
- `docs/QUALITY_RUBRIC.md`：官方评分维度、本题对照维度与六步自查流程。
- `docs/FIELD_DICTIONARY.md`：字段字典、锚点格式与状态约定。
- `docs/INNOVATION.md`：新增能力、方法改进、价值边界与对照设计。
- `templates/comparison_template.json`：使用增益证据的回填模板。
- `examples/case_set.md`：三组格式演示（非官方案例答案）。

## 确定性产物说明
运行 `scripts/solve.py` 后，输出目录会多出三个文件：
- `verification.json`：脚本可判定的检查项（passed=true/false/null）。
- `comparison.json`：对照维度骨架，须由 Agent 用本次真实产物回填，baseline 未观察到就保持 `not observed`。
- `audit.json`：结果结构与锚点的审计结论；`passed=false` 时不得把 result.json 标为 success。

## 评分点对照
本题对照维度：逐字提取完整率、阅读顺序正确率、表格行列归属准确率、公式符号保真率、锚点可回查率、人工校对耗时。每项都要在 `comparison.json` 的 `skill_evidence` 中指向 `result.json` 的具体字段或证据锚点。

## 版本与维护
- 版本：v2（2026-11-26）。
- 依赖：Python 3.9+ 标准库；评测环境中的 pdf-text-tool / pdf-render-tool / ocr-tool / latex-compiler 按题面实际需要调用。
- 已知限制：脚本只做确定性盘点与自检，不替代对真实材料的阅读、翻译、写作判断或真实编译。
- 维护：更换学科/文体/模板时，优先更新术语表、字段模板与风格规则，锚点与审计机制保持不变。
