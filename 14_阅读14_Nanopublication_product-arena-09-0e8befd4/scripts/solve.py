#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (ResultBuilder, common_args, load_case, locate, read_text,
                           sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "reading14-nanopublication"
CONNECT = re.compile(r"\b(and|but|however|therefore|because|whereas|although|while|thus)\b|以及|但是|因此|然而|同时|并且", re.I)
SENT = re.compile(r"(?<=[.!?。！？])\s+")

AXES = ["断言原子化粒度", "主体/关系方向准确率", "最小充分证据命中率", "来源元数据完整率", "导出可直接解析率", "人工拆分耗时"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    candidates = []
    for p in texts:
        text = read_text(p)
        src = p.stem
        b.add_source(p, sha256_file(p), "source-paper")
        for s in SENT.split(text):
            s = s.strip()
            if len(s) < 30:
                continue
            parts = [x.strip() for x in CONNECT.split(s) if x and x.strip()]
            atomic = parts if len(parts) > 1 else [s]
            for a in atomic:
                if len(a) < 15:
                    continue
                item = {"assertion_id": "A%03d" % (len(candidates) + 1), "text": a[:1200],
                        "source_id": src, "locator": locate(text, a) or {},
                        "subject": "", "relation": "", "qualifier": "",
                        "evidence_quote": "", "evidence_strength": "unverified",
                        "status": "pending"}
                candidates.append(item)
                b.add_evidence(claim=a[:160], locator=item["locator"], quote=a[:300], source_id=src, strength="candidate")
    b.set("assertion_candidates", candidates)
    b.set("quality_rules", [
        "一条断言只表达一个可独立判真的命题，保留条件与限定范围。",
        "证据取最小充分片段，区分直接证据与间接推论。",
        "主体、关系方向、年份、版本、DOI 必须来自输入材料，不从常识补全。",
        "找不到支撑片段的断言保留并标 status=unsupported，不得删除或改写原文。"
    ])
    b.set("export_schema", ["assertion_id", "text", "subject", "relation", "qualifier",
                            "source_id", "locator", "evidence_quote", "evidence_strength", "confidence_basis"])
    if not candidates:
        b.add_uncertainty("未从输入中切分出有效断言候选，需由 Agent 依据实际材料拆分。")
    b.add_confirm("逐条确认断言粒度、主体关系方向与最小证据片段。")
    b.add_check("assertion_candidates", bool(candidates), "候选断言 %d 条" % len(candidates))
    b.add_check("atomic_grain", None if candidates else False,
                "含并列/因果/转折的候选须拆到单一主体与单一关系，再回填 subject/relation/qualifier")
    b.add_check("export_schema", bool(b.data.get("export_schema")), "导出字段固定为 %d 项" % len(b.data.get("export_schema") or []))
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
