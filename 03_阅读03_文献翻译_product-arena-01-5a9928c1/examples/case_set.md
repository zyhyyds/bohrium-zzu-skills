# 最小调用示例（格式演示，非官方案例答案）

以下三个示例只演示接口与产物形态，输入内容均为虚构，不能作为任何正式案例答案提交。

## 示例 A｜标准输入

- 输入：`/input/case.json`（含 case_id 与 output_contract）、`/input/task.md`、`/input/material.txt`
- 调用：`python scripts/solve.py --input /input --output /app/output`
- 输出：`result.json`（业务字段：`source_inventory`、`glossary_candidates`、`segments`、`invariant_checks`、`citation_markers_in_source`）、`verification.json`、`comparison.json`、`audit.json`

## 示例 B｜材料缺失

- 输入：只有 case.json 与 task.md，正文材料为空
- 预期：`status=unknown`，`uncertainty` 写明缺失材料，`audit.json` 提示 contract 未回填
- 处置：不得补造正文；列出需补充的文件清单并停止生成关键结论

## 示例 C｜重复运行

- 输入：与示例 A 相同
- 预期：`sources[].sha256` 一致、`block_id` / `segment_id` 等编号稳定、结论不漂移
- 处置：若 `comparison.json` 已回填，重复运行应保留该文件不被骨架覆盖

## 示例 result.json 片段

```json
{
  "case_id": "example-case-001",
  "status": "partial",
  "result": {"your_contract_field": "按实际 output_contract 填写"},
  "evidence": [{"claim": "示例结论", "locator": {"file": "material.txt", "line": 12}, "quote": "示例短引", "source_id": "material"}],
  "uncertainty": ["示例：原文该处无文字层，未做判断"],
  "needs_human_confirmation": []
}
```
