# 评分点对照与自查表｜14_阅读14_Nanopublication_product-arena-09-0e8befd4

官方评分维度：实际效果 40（完成度 15 / 正确性 15 / 完整性 5 / 可核验性 5）、使用增益 25（质量 15 / 效率 5 / 可验证性 5）、创新增益 15、可靠体验 10、生态贡献 10；GitHub 公开链接另加最高 5 分。

## 本题对照维度

- 断言原子化粒度
- 主体/关系方向准确率
- 最小充分证据命中率
- 来源元数据完整率
- 导出可直接解析率
- 人工拆分耗时

## 自查步骤

1. 运行 `python scripts/solve.py --input /input --output /app/output`。
2. 读 `audit.json`：有 `issues` 或 `failed_checks` 时先修复，不得直接标 success。
3. 读 `verification.json`：pending 项须由 Agent 按真实材料回填或写入 uncertainty。
4. 读 `comparison.json`：逐项回填 skill_evidence，保留 not observed 的 baseline。
5. 核对 `result.json`：output_contract 全字段、case_id、evidence 锚点、status。
6. 核对 `change_log.md`：每处改动有原文、改文/终值、类型与理由。
