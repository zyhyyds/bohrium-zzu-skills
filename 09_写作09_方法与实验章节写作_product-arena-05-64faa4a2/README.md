# 写作09｜方法与实验章节写作

- 对应赛题 ID：`product-arena-05-64faa4a2`
- 主攻方向：参数来源表、复现清单与缺口追问清单
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
- `comparison.json`：脚本从真实检查项与结果字段自动生成的对照证据初稿（auto_draft）；Agent 逐项确认后把 status 改为 confirmed，baseline 未观察到就保持 `not observed`。
- `audit.json`：结果结构与锚点的审计结论；`passed=false` 时不得把 result.json 标为 success。

## 评分点对照
本题对照维度：六类要素齐全度、参数来源可追溯率、条件一致性、复现清单可执行率、缺口追问覆盖率、补写返工轮次。每项都要在 `comparison.json` 的 `skill_evidence` 中指向 `result.json` 的具体字段或证据锚点。

## 版本与维护
- 版本：v2（2026-11-26）。
- 依赖：Python 3.9+ 标准库；评测环境中的 pdf-text-tool / pdf-render-tool / ocr-tool / latex-compiler 按题面实际需要调用。
- 已知限制：脚本只做确定性盘点与自检，不替代对真实材料的阅读、翻译、写作判断或真实编译。
- 维护：更换学科/文体/模板时，优先更新术语表、字段模板与风格规则，锚点与审计机制保持不变。

## 评分维度对照与证据索引

下表把评分维度对应到仓库中可直接查看的证据，便于评审定位。

| 评分维度 | 本作品的对应证据 |
|---|---|
| 实际效果（任务完成度 / 正确性 / 完整性 / 可核验性） | `scripts/solve.py` 产出的主结果文件；每条结果带来源锚点（文件 + 段落/页码/行号） |
| 使用增益（质量 / 效率 / 可验证性） | 见下文“与基础 Agent 的对照”；`invariant_checks` / `audit.json` 为程序化核对记录 |
| 创新增益（新增能力 / 方法改进 / 证据） | 见下文“方法与创新点”，每条均对应到具体代码路径 |
| 可靠体验（易用性 / 稳定性 / 异常处理） | `SKILL.md` 的“异常处理矩阵”；仅依赖标准库，重复运行结果一致 |
| 生态贡献（文档 / 可复用性 / 分享价值） | `SKILL.md` + `README.md` + `docs/` + `examples/`；`examples/mini_example.md` 给出可跑通的最小调用 |

## 方法与创新点

- **参数表抽取**：从方法/实验段落抽参数名、值、单位与来源行号（`parameter_table`），可直接核对。
- **缺失类别清单**：对照可复现性要素（数据来源、划分、超参、评价指标、随机种子、算力）列出未出现的类别。
- **追问生成**：针对缺失项生成具体追问，而不是笼统建议“补充实验细节”。
- **不补造数值**：没有的参数一律标为缺失，不推断、不填默认值。

**边界（不做什么）**：参数语义需作者确认；跨表格的隐含参数（如由公式推导）不会自动反推。

**主要产物**：`parameter_table`、`missing_categories`、`followup_questions`

## 与基础 Agent 的对照（如何验证使用增益）

平台会用同一批固定案例分别运行“不加载 Skill 的基础 Agent”和“加载本 Skill 的 Agent”。本仓库不编造对照数字，只提供可复现的对照方法：

1. **基线条件**：把原始材料直接交给模型，要求完成同一任务，不提供本 Skill 的脚本与规则。
2. **Skill 条件**：按 `SKILL.md` 调用 `scripts/solve.py`，再按说明核对产物。
3. **可观察差异**（可自行复现，不依赖主观打分）：
   - 产物是否带可回查锚点（文件 + 段落/页码/行号）；
   - 关键约束是否被程序化核对（数字守恒、引用编号、限定词强度）；
   - 同一输入重复运行的结果是否一致；
   - 缺失与不确定项是否被显式列出，而不是被补写成事实。
4. **效率**：`audit.json` / `verification.json` 记录本次运行的检查项与耗时字段，可对比人工校对轮次。

> 说明：官方对照与分数由平台生成，本仓库只提供方法与可核验产物，不声称任何基准分数。

## 复用与维护

- **依赖**：仅 Python 3 标准库（`README.md` 中逐题注明）；不依赖网络与第三方包，可在离线评测环境运行。
- **路径约定**：`scripts/solve.py --input <输入目录> --output <输出目录>`；输入支持 `case.json` + `task.md` + 材料文件。
- **适用范围与限制**：见上文“边界”与 `SKILL.md` 的“触发边界”。
- **版本**：v4（脚本自动产出完整初稿，Agent 只做核对与修正）；改动记录见仓库提交历史。
- **维护入口**：`SKILL.md`（调用约定）、`scripts/solve.py`（主流程）、`scripts/evidence_core.py`（结果构建与审计）。
