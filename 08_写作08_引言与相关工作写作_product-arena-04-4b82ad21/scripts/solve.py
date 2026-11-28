#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (autofill_contract, ResultBuilder, CITE_RE, common_args, load_case,
                           locate, read_text, sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "writing08-intro-related-work"
LIMIT = re.compile(r"\b(however|limited|remains|challenge|difficult|lack|rarely|little|unresolved)\b|尚未|局限|不足|难以|没有解决", re.I)
CONTRIB = re.compile(r"\b(we propose|we present|this paper proposes|this work presents|our contribution)\b|本文提出|本文设计|我们的贡献", re.I)
SENT = re.compile(r"(?<=[.!?。！？])\s+")

AXES = ["转述准确率", "分组合理性", "空白推导成立率", "贡献—证据对齐率", "引用覆盖率", "成稿返工轮次"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    claims, gaps, contributions = [], [], []
    for p in texts:
        text = read_text(p)
        b.add_source(p, sha256_file(p), "source-material")
        for s in SENT.split(text):
            s = s.strip()
            if len(s) < 25:
                continue
            item = {"text": s[:800], "source_id": p.stem, "locator": locate(text, s[:100]) or {},
                    "citations": CITE_RE.findall(s), "topic_terms": re.findall(r"\b[A-Z][A-Za-z-]{3,}\b", s)[:6],
                    "status": "pending"}
            if LIMIT.search(s):
                gaps.append(dict(item, gap_type="limitation_or_unresolved"))
            if CONTRIB.search(s):
                contributions.append(dict(item))
            claims.append(item)
    for x in gaps[:60] + contributions[:30]:
        b.add_evidence(claim=x["text"][:160], locator=x["locator"], quote=x["text"][:300], source_id=x["source_id"])
    b.set("claim_table", claims[:200])
    b.set("gap_candidates", gaps)
    b.set("contribution_candidates", contributions)
    b.set("grouping_axis", ["问题设定", "方法路线", "数据与评价方式"])
    b.set("writing_rules", ["相关工作按问题/方法/数据分组比较，不按时间罗列", "研究空白必须由已引文献共同限制推出",
                            "每条贡献能在正文图表找到对应证据", "断言与引用一一对应"])
    if not gaps:
        b.add_uncertainty("输入中未检出显式限制词；研究空白需由 Agent 从引文覆盖范围与实验条件推导，不得凭空写。")
    b.add_confirm("核对每条转述是否与所引文献原文一致。")
    b.add_check("claim_table", bool(claims), "论断表 %d 条" % len(claims))
    b.add_check("gap_grounded", bool(gaps) or bool(b.data.get("uncertainty")),
                "空白候选 %d 条；无显式限制词时必须写明从引文覆盖/实验条件的推导链" % len(gaps))
    b.add_check("contribution_evidence", None,
                "每条贡献须在正文图表或实验中找到对应证据，找不到就降级或删除")
    autofill_contract(b, {
        "claims": claims,
        "claim_table": claims,
        "gaps": gaps,
        "gap_candidates": gaps,
        "contributions": contributions,
        "contribution_candidates": contributions,
        "related_work_groups": {a: [] for a in ["问题设定", "方法路线", "数据与评价方式"]},
    })
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
