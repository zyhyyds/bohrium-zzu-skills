#!/usr/bin/env python3
import re
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (autofill_contract, ResultBuilder, CITE_RE, common_args, find_key, invariant_report,
                           load_case, locate, read_text, sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "reading03-translation"
ACRONYM_RE = re.compile(r"\b([A-Z]{2,10})\s*\(([^)]{2,80})\)")
CAP_RE = re.compile(r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+){0,3})\b")

AXES = ["术语一致率", "段落完整率", "段号对应关系", "数字/单位/引用守恒率", "逐段可回查率", "人工校对耗时"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    source = "\n\n".join(read_text(p) for p in texts) if texts else ""
    target = find_key(case, "target_text") or find_key(case, "translation") or ""
    if not isinstance(target, str):
        target = ""
    counts = Counter()
    first_seen = {}
    for m in ACRONYM_RE.finditer(source):
        term = m.group(2).strip()
        counts[term] += 1
        first_seen.setdefault(term, m.group(1))
    for m in CAP_RE.finditer(source):
        term = m.group(1).strip()
        if len(term) > 3 and not term.isupper():
            counts[term] += 1
            first_seen.setdefault(term, term)
    glossary = []
    for term, n in counts.most_common(40):
        glossary.append({"term": term, "occurrences": n, "suggested_translation": "",
                         "fixed_by_skill": True, "locator": locate(source, term) or {}})
    segments = []
    for i, para in enumerate([x.strip() for x in re.split(r"\n\s*\n", source) if x.strip()], 1):
        segments.append({"segment_id": "S%03d" % i, "source": para[:2000], "translation": "",
                         "anchor": {"paragraph_index": i}, "status": "pending"})
    checks = invariant_report(source, target) if target else {"note": "未提供译文文本，无法做数字/引用/限定词守恒检查。"}
    b.set("source_inventory", [{"path": str(p), "sha256": sha256_file(p)} for p in texts])
    b.set("glossary_candidates", glossary)
    b.set("segments", segments)
    b.set("invariant_checks", checks)
    b.set("citation_markers_in_source", CITE_RE.findall(source))
    for p in texts:
        b.add_source(p, sha256_file(p), "source")
        b.add_evidence(claim="术语抽取来源", locator={"file": p.name}, quote=read_text(p)[:200], source_id=p.name)
    if not target:
        b.add_uncertainty("case.json 中未找到 target_text / translation，译文与守恒检查需由 Agent 按 SKILL.md 流程生成后回填。")
    b.add_confirm("核对每个术语在标题、摘要、正文、图注和结论中的译法是否一致。")
    b.add_check("glossary_extracted", bool(glossary), "抽取 %d 个术语候选" % len(glossary))
    b.add_check("glossary_locked", all(x.get("suggested_translation") for x in glossary) if glossary else None,
                "术语表必须逐条回填 suggested_translation 才算真正锁定")
    b.add_check("segment_coverage", bool(segments), "段号 %d 个，不得跳号或重复" % len(segments))
    b.add_check("invariant_clear", not ((b.data.get("invariant_checks") or {}).get("numbers_missing")),
                "数字缺失必须为零或在 uncertainty 中逐项解释")
    autofill_contract(b, {
        "glossary": glossary,
        "segments": segments,
        "translated_segments": segments,
        "translations": [{"segment_id": s["segment_id"], "translation": s.get("translation", ""),
                          "anchor": s.get("anchor")} for s in segments],
        "source_text": source,
        "invariant_checks": checks,
    })
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
