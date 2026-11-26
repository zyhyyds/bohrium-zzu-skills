# 格式示例（非官方案例答案）

本文件只演示 result.json 的写法，内容全部是虚构占位，不能作为任何正式案例的答案提交。

```json
{
  "case_id": "example-case-001",
  "status": "partial",
  "result": { "your_contract_field": "按实际 output_contract 填写" },
  "evidence": [
    { "claim": "示例结论", "locator": {"file": "paper.txt", "line": 42}, "quote": "示例原文短引", "source_id": "paper" }
  ],
  "uncertainty": ["示例：原文该处无文字层，未做判断"],
  "changes": [{ "before": "示例原文", "after": "示例改文", "type": "示例类型", "reason": "示例理由" }],
  "needs_human_confirmation": ["示例：请作者确认术语译名"]
}
```
