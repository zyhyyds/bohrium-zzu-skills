# Bohrium 郑大站 · 第一期十题 Skill 提交包

十个相互独立的 Skill，分别对应 The Playground 郑大站（Campus Challenge · ZZU station）第一期的十个 Challenge。每个目录都是一份可独立安装的 Skill，不是预写答案；平台在 3 个固定案例上分别运行基础 Agent 与加载本 Skill 的 Agent，以实际产物和提交材料评分。

赛期：2026-11-27 至 2026-12-03（具体提交开放时间以赛事通知为准）。

## 目录索引

| # | 题目 | Challenge ID | 目录 | 主攻方向 |
| - | - | - | - | - |
| 1 | 阅读01｜文献文档解析 | `product-arena-08-3027d350` | `01_阅读01_文献文档解析_product-arena-08-3027d350` | 多栏顺序 / 跨页表 / 章节树 / 公式符号 / OCR，逐块回原文定位 |
| 2 | 写作02｜学术语言润色 | `product-arena-02-7051d92d` | `02_写作02_学术语言润色_product-arena-02-7051d92d` | 最小编辑与限定强度守恒，逐句修改说明 |
| 3 | 阅读03｜文献翻译 | `product-arena-01-5a9928c1` | `03_阅读03_文献翻译_product-arena-01-5a9928c1` | 术语表驱动的双语段落对齐与守恒核验 |
| 4 | 写作04｜参考文献与引用管理 | `product-arena-03-429cc14d` | `04_写作04_参考文献与引用管理_product-arena-03-429cc14d` | 引用定位、编号连锁更新、去重与来源核验 |
| 5 | 写作08｜引言与相关工作写作 | `product-arena-04-4b82ad21` | `08_写作08_引言与相关工作写作_product-arena-04-4b82ad21` | 相关工作分组、空白推导与贡献证据对齐 |
| 6 | 写作09｜方法与实验章节写作 | `product-arena-05-64faa4a2` | `09_写作09_方法与实验章节写作_product-arena-05-64faa4a2` | 参数来源表、复现清单与缺口追问清单 |
| 7 | 阅读10｜文献总结与结构化笔记 | `product-arena-06-6d8cf72b` | `10_阅读10_文献总结与结构化笔记_product-arena-06-6d8cf72b` | 按论文章节生成字段化笔记与来源回链 |
| 8 | 写作13｜LaTeX 写作与编译 | `product-arena-07-865de7e4` | `13_写作13_LaTeX写作与编译_product-arena-07-865de7e4` | 静态检查 + 真实编译闭环与可复现构建记录 |
| 9 | 阅读14｜Nanopublication | `product-arena-09-0e8befd4` | `14_阅读14_Nanopublication_product-arena-09-0e8befd4` | 原子断言拆解、最小证据绑定与机器可读导出 |
| 10 | 阅读15｜文献知识图谱构建 | `product-arena-10-760d1a0b` | `15_阅读15_文献知识图谱构建_product-arena-10-760d1a0b` | 双篇论文实体关系抽取、跨篇冲突处理与查询 |

## 评分结构（官方 guide）

| 维度 | 分值 | 主要内容 |
| - | - | - |
| 实际效果 | 40 | 任务完成度 15、结果正确性 15、完整性 5、可核验性 5 |
| 使用增益 | 25 | 质量增益 15、效率增益 5、增益可验证性 5 |
| 创新增益 | 15 | 新增能力 5、方法改进 5、创新证据 5 |
| 可靠体验 | 10 | 调用与易用性 3、运行稳定性 4、异常处理 3 |
| 生态贡献 | 10 | 文档完整性 3、资源可复用性 4、分享推广价值 3 |

GitHub 公开作品链接另加最高 5 分。各题提交目录根部的 `GITHUB_URL.txt` 第一行填写仓库/目录 URL，第二行可填本题相对路径。

## 统一运行流程

```bash
# 1. 生成锚点、候选与审计骨架
python scripts/solve.py --input /input --output /app/output

# 2. Agent 读取真实材料，核对并回填 result.json 与 comparison.json

# 3. 终审：复核结构、锚点与对照证据
python scripts/solve.py --validate --output /app/output
```

运行时输出：`result.json`（含 `output_contract` 全字段与 `case_id`）、`verification.json`（确定性检查）、`comparison.json`（增益证据）、`audit.json` / `validation_report.json`（审计结论）、`run.log`、`change_log.md`。`audit.json` 的 `passed=false` 时不得把状态写成 `success`。

## 资源约定

每题目录含：`SKILL.md`、`scripts/evidence_core.py`、`scripts/solve.py`、`templates/result_template.json`、`templates/comparison_template.json`、`examples/mini_example.md`、`examples/case_set.md`、`README.md`、`GITHUB_URL.txt`、`docs/FIELD_DICTIONARY.md`、`docs/INNOVATION.md`、`docs/QUALITY_RUBRIC.md`。

依赖仅为 Python 3.9+ 标准库；评测环境中的 pdf-text-tool / pdf-render-tool / ocr-tool / latex-compiler 按题面实际需要调用。`examples/` 与 `templates/` 均为格式演示，不是官方案例答案。
