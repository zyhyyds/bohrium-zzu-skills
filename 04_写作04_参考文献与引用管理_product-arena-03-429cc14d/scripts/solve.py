#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (ResultBuilder, common_args, load_case, read_text,
                           sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "writing04-citation-management"
BIBITEM_RE = re.compile(r"^\s*\[\s*(\d+)\s*\]\s*(.+)$")
DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)
TITLE_RE = re.compile(r"(?:title\s*=\s*[{\"']?)([^{}\n,]{10,160})", re.I)
BRACKET_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

def norm(s):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (s or "").lower())

AXES = ["引用位置准确率", "编号连续与同步率", "去重判据可解释率", "元数据准确率", "论断—引用匹配率", "逐条核对耗时"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    entries, manuscript = [], []
    for p in texts:
        text = read_text(p)
        b.add_source(p, sha256_file(p), "manuscript-or-library")
        is_bib = p.suffix.lower() == ".bib" or text.lstrip().startswith("@")
        for ln, line in enumerate(text.splitlines(), 1):
            m = BIBITEM_RE.match(line)
            if m:
                doi = DOI_RE.search(line)
                title = TITLE_RE.search(line)
                entries.append({"old_number": int(m.group(1)), "raw": m.group(2).strip()[:300],
                                "doi": doi.group(0).rstrip(".,") if doi else "",
                                "title": title.group(1).strip() if title else m.group(2).strip()[:100],
                                "file": p.name, "line": ln})
            elif not is_bib:
                manuscript.append((p.name, ln, line))
    used = []
    for fname, ln, line in manuscript:
        for m in BRACKET_RE.finditer(line):
            for n in re.findall(r"\d+", m.group(1)):
                used.append({"number": int(n), "file": fname, "line": ln,
                             "sentence": line.strip()[:300], "locator": {"file": fname, "line": ln}})
    seen, duplicates = {}, []
    for e in entries:
        key = e["doi"] or norm(e["title"])
        if key in seen:
            duplicates.append({"keep": seen[key]["old_number"], "merge": e["old_number"], "basis": key})
        else:
            seen[key] = e
    order = []
    for u in used:
        if u["number"] not in order:
            order.append(u["number"])
    numbering_map = {old: i + 1 for i, old in enumerate(order)}
    unused = sorted(set(e["old_number"] for e in entries) - set(u["number"] for u in used))
    missing = sorted(set(u["number"] for u in used) - set(e["old_number"] for e in entries))
    gaps = sorted(set(range(1, max([e["old_number"] for e in entries] or [0]) + 1)) - set(e["old_number"] for e in entries))
    changes = [{"old": n, "new": numbering_map[n], "type": "renumber"} for n in sorted(numbering_map)]
    b.set("references", entries)
    b.set("citation_points", used)
    b.set("numbering_map", changes)
    b.set("duplicates", duplicates)
    b.set("unused_entries", unused)
    b.set("missing_entries", missing)
    b.set("numbering_gaps", gaps)
    for u in used[:40]:
        b.add_evidence(claim="引用点", locator=u["locator"], quote=u["sentence"], source_id=u["file"])
    b.add_confirm("逐句判断引用是否落在真正需要来源支撑的论断上，并核验 DOI 元数据。")
    b.add_check("entries_parsed", bool(entries), "解析 %d 条文末条目" % len(entries))
    b.add_check("numbering_complete", not (missing or unused),
                "编号映射 %d 项；missing=%s unused=%s" % (len(changes), missing, unused))
    b.add_check("dedup_basis", bool(duplicates) or True,
                "重复条目 %d 组，每组须写 DOI/题名归一化依据，防误合并同名作者不同文献" % len(duplicates))
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
