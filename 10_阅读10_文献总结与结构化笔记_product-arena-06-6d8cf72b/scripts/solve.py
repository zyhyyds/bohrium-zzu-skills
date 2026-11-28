#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (autofill_contract, ResultBuilder, common_args, load_case, read_text,
                           sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "reading10-structured-notes"
HEAD_RE = re.compile(r"^(?:#{1,6}\s|\d+(?:\.\d+)*\s+|Abstract\b|摘要|Introduction\b|Methods?\b|Results?\b|Discussion\b|Conclusion\b|References\b|参考文献)", re.I)
FIELDS = ["research_question", "data", "method_conditions", "main_findings", "limitations"]

AXES = ["章节骨架对齐度", "五字段完整率", "论断/数值准确率", "锚点可回查率", "笔记可检索性", "单篇整理耗时"]


FIELD_CUES = {
    "research_question": r"(?:we (?:study|investigate|ask|address|examine)|this paper|本文|研究问题|\?)",
    "data": r"(?:dataset|corpus|benchmark|samples?|queries|数据集|语料)",
    "method_conditions": r"(?:we (?:use|train|evaluate|run|tune)|batch size|learning rate|GPU|A100|方法|实验设置)",
    "main_findings": r"(?:results? show|we (?:find|observe|achieve|reach)|improves?|outperforms?|accuracy|nDCG|结果|提升)",
    "limitations": r"(?:limitation|we (?:do not|only)|future work|cannot|局限|不足)",
}


def sentences(text):
    parts = re.split(r"(?<=[.!?。！？])\s+", " ".join(text.split()))
    return [s.strip() for s in parts if len(s.strip()) >= 12]


def fill_card(raw):
    """Fill the five fields with the sentences that actually mention them."""
    sents = sentences(raw)
    fields = {}
    for key, cue in FIELD_CUES.items():
        rx = re.compile(cue, re.I)
        hits = [s for s in sents if rx.search(s)]
        fields[key] = " ".join(hits[:2])[:600]
    summary = " ".join(sents[:2])[:600] if sents else ""
    filled = sum(1 for v in fields.values() if v)
    return summary, fields, filled


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    for p in texts:
        b.add_source(p, sha256_file(p), "paper-text")
    notes = []
    for p in texts:
        lines = read_text(p).splitlines()
        current = {"section_id": "SEC000", "title": "(preamble)", "file": p.name,
                   "start_line": 1, "raw": []}
        for ln, line in enumerate(lines, 1):
            if HEAD_RE.match(line.strip()):
                if current["raw"]:
                    notes.append(current)
                current = {"section_id": "SEC%03d" % (len(notes) + 1), "title": line.strip()[:200],
                           "file": p.name, "start_line": ln, "raw": []}
            else:
                current["raw"].append(line)
        if current["raw"]:
            notes.append(current)
    cards = []
    for n in notes:
        raw = "\n".join(n["raw"]).strip()
        summary, fields, filled = fill_card(raw)
        card = {"note_id": "N%03d" % (len(cards) + 1), "section_id": n["section_id"],
                "section_title": n["title"], "anchor": {"file": n["file"], "line": n["start_line"], "section_id": n["section_id"]},
                "quote": raw[:500], "summary": summary, "fields": fields,
                "fields_filled": filled,
                "status": "auto_filled" if filled >= 3 else ("partial" if filled else "pending")}
        cards.append(card)
        b.add_evidence(claim=n["title"], locator=card["anchor"], quote=raw[:300], source_id=n["file"])
    b.set("notes", cards)
    b.set("fill_stats", {"cards": len(cards),
                         "auto_filled": sum(1 for c in cards if c["status"] == "auto_filled"),
                         "partial": sum(1 for c in cards if c["status"] == "partial"),
                         "pending": sum(1 for c in cards if c["status"] == "pending")})
    b.set("field_dictionary", {k: "从原文该章节抽取，缺失写 not reported，不得推断。" for k in FIELDS})
    b.set("search_index_hint", "按 section_title、fields 中的术语与 anchor.section_id 建立检索。")
    if not cards:
        b.add_uncertainty("输入中未识别到章节结构，需由 Agent 依据实际材料人工切分。")
    b.add_confirm("逐条确认笔记锚点是否指向真实章节、段落或图表位置。")
    b.add_check("notes_sections", bool(cards), "章节笔记骨架 %d 条" % len(cards))
    b.add_check("fields_filled", None if cards else False,
                "research_question/data/method_conditions/main_findings/limitations 五字段须由 Agent 按原文回填，缺失写 not reported")
    b.add_check("quote_anchors", all(x.get("anchor", {}).get("file") for x in cards),
                "每条笔记的 anchor 必须指向真实文件与行号/段落")
    autofill_contract(b, {
        "notes": cards,
        "sections": cards,
        "note_cards": cards,
        "field_dictionary": b.data.get("field_dictionary") or {},
    })
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
