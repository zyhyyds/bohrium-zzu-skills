# 字段字典｜13_写作13_LaTeX写作与编译_product-arena-07-865de7e4

本字典描述 `result.json` 的字段含义。业务字段以 `/input/case.json` 的 `output_contract` 为准，脚本输出的中间结构仅为工作底稿，不能冒充最终答案。

| 字段 | 含义 | 填写责任 |
| - | - | - |
| `case_id` | string | 从 case.json 原样读取的案例标识，不得改写 |
| `skill_id` | string | SKILL.md frontmatter 中的 name |
| `status` | enum | success / partial / unknown / refuse；audit.json 未通过时不得写 success |
| `generated_at` | string | 本次运行 UTC 时间，由脚本生成 |
| `result` | object | output_contract 字段快照；实际字段以 case.json 为准 |
| `evidence` | array | 关键结论 + locator + quote + source_id + strength |
| `sources` | array | 输入文件路径、sha256 与角色 |
| `uncertainty` | array | 未报告、无法判断、材料冲突 |
| `changes` | array | before/after/type/reason 四元组 |
| `needs_human_confirmation` | array | 必须交回作者确认的条目 |
| `issues` | 本题 solve.py 产出的中间结构，需 Agent 按真实材料核对并回填；字段形态以 result.json 为准 | 脚本生成骨架，Agent 回填终值 |
| `compile_plan` | 本题 solve.py 产出的中间结构，需 Agent 按真实材料核对并回填；字段形态以 result.json 为准 | 脚本生成骨架，Agent 回填终值 |
| `environment_record` | 本题 solve.py 产出的中间结构，需 Agent 按真实材料核对并回填；字段形态以 result.json 为准 | 脚本生成骨架，Agent 回填终值 |

## 锚点格式

`locator` 推荐字段：`file`（输入文件名）、`line`（行号）、`section_id` / `paragraph_id`、`block_id`、`page`（仅当材料确有页码）。没有真实页码时写 `not reported`，不得把自建页码当原 PDF 页码。

## 状态约定

`success`：全部必填字段已回填且 audit 通过；`partial`：部分完成并逐项写明限制；`unknown`：材料无法判断；`refuse`：加密/权限受限等无法读取。
