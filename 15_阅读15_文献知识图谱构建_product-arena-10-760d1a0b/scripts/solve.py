#!/usr/bin/env python3
import re
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (ResultBuilder, common_args, load_case, read_text,
                           sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "reading15-knowledge-graph"
ENT_RE = re.compile(r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+){0,3})\b")
ACRONYM_RE = re.compile(r"\b([A-Z]{2,10})\s*\(([^)]{2,80})\)")
USE_RE = re.compile(r"([A-Z][\w -]{1,60})\s+(?:uses|using|adopts|adopted|基于|采用)\s+([A-Z][\w -]{1,60})", re.I)
IMPROVE_RE = re.compile(r"([A-Z][\w -]{1,60})\s+(?:improves|outperforms|achieves|reduces|优于|提升|降低)\s+([A-Z][\w -]{1,60})", re.I)
JATS_RE = re.compile(r"<p[^>]*\bid\s*=\s*[\"']([^\"']+)[\"']", re.I)

AXES = ["实体真实出现率", "关系类型/方向准确率", "别名归一正确率", "节点与边证据覆盖率", "查询结果可复核率", "跨篇整理耗时"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    nodes, edges, surfaces = [], [], defaultdict(set)
    for si, p in enumerate(texts, 1):
        sid = "%s#S%d" % (p.stem, si)
        b.add_source(p, sha256_file(p), "independent-paper")
        text = read_text(p)
        b.add_evidence(claim="论文来源", locator={"file": p.name}, quote=text[:250], source_id=sid)
        jats = JATS_RE.findall(text)
        paras = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
        for pi, para in enumerate(paras, 1):
            pid = jats[pi - 1] if pi <= len(jats) else "P%03d" % pi
            for m in ACRONYM_RE.finditer(para):
                surfaces[m.group(2).strip()].add(sid)
            for m in ENT_RE.finditer(para):
                e = m.group(1).strip()
                if len(e) < 3:
                    continue
                surfaces[e].add(sid)
                nodes.append({"node_id": "N%04d" % (len(nodes) + 1), "surface": e, "type": "concept",
                              "source_id": sid, "paragraph_id": pid, "quote": para[:300], "status": "candidate"})
            for m in USE_RE.finditer(para):
                edges.append({"edge_id": "E%04d" % (len(edges) + 1), "subject": m.group(1).strip(),
                              "relation": "uses", "object": m.group(2).strip(), "source_id": sid,
                              "paragraph_id": pid, "quote": m.group(0)[:300], "status": "candidate"})
            for m in IMPROVE_RE.finditer(para):
                edges.append({"edge_id": "E%04d" % (len(edges) + 1), "subject": m.group(1).strip(),
                              "relation": "improves", "object": m.group(2).strip(), "source_id": sid,
                              "paragraph_id": pid, "quote": m.group(0)[:300], "status": "candidate"})
    conflicts = [{"surface": s, "source_ids": sorted(ids)} for s, ids in surfaces.items() if len(ids) > 1]
    queries = [
        {"query": "Q1: 列出所有候选实体及来源", "result": [n["surface"] for n in nodes[:30]]},
        {"query": "Q2: 列出所有带证据的关系", "result": [e["relation"] for e in edges[:30]]},
        {"query": "Q3: 哪些表面形式跨篇出现", "result": conflicts[:30]},
    ]
    b.set("nodes", nodes)
    b.set("edges", edges)
    b.set("cross_source_conflicts", conflicts)
    b.set("queries", queries)
    b.set("merge_policy", "仅在别名、缩写、同对象证据都一致时才合并；不同论文的条件、样本、数据集与数值不得合成一个结论。")
    if len(texts) < 2:
        b.add_uncertainty("输入中识别到的独立文本少于 2 篇；知识图谱题面要求两篇独立论文，需核对 corpus-manifest.json。")
    b.add_uncertainty("节点/边为候选，须由 Agent 逐条回原文确认；JATS 段落 ID 不是 PDF 页码，不得换算。")
    b.add_confirm("核对别名合并依据与不得合并的跨篇对象。")
    b.add_check("two_papers", len(texts) >= 2, "识别到 %d 篇独立文本，题面要求两篇论文" % len(texts))
    b.add_check("edges_with_evidence", bool(edges),
                "候选边 %d 条，每条须有 quote 与 paragraph_id；共现不算关系" % len(edges))
    b.add_check("queries_live", None,
                "三个查询须由 Agent 基于最终节点与边实际执行并回填结果子图与支撑证据，不得使用脚本占位查询")
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
