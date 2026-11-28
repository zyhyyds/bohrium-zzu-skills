#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reading15 knowledge-graph entrypoint (v5).

Design: entities are extracted with evidence; edges come from entity pairs that
co-occur in the same paragraph. When a relation verb is present the edge is typed,
otherwise it is labelled `co_occurs` — never invented.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_core import (autofill_contract, ResultBuilder, common_args, load_case,
                           read_text, sha256_file, text_files, finalize_with_checks)

SKILL_ID = "reading15-knowledge-graph"

ENT_RE = re.compile(r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+){0,3})\b")
ACRONYM_RE = re.compile(r"\b([A-Z]{2,10})\s*\(([^)]{2,80})\)")
JATS_RE = re.compile(r"<p[^>]*\bid\s*=\s*[\"']([^\"']+)[\"']", re.I)

REL_CUES = [
    ("based_on", re.compile(r"\b(?:based on|built on|derived from)\b", re.I)),
    ("uses", re.compile(r"\b(?:uses?|using|adopts?|employs?|leverag\w+)\b", re.I)),
    ("trained_on", re.compile(r"\b(?:trained on|fine-?tuned on)\b", re.I)),
    ("evaluated_on", re.compile(r"\b(?:evaluated on|tested on|benchmarked on)\b", re.I)),
    ("outperforms", re.compile(r"\b(?:outperforms?|surpasses?|beats?|better than|优于)\b", re.I)),
    ("improves", re.compile(r"\b(?:improves?|enhances?|increases?|提升)\b", re.I)),
    ("reduces", re.compile(r"\b(?:reduces?|decreases?|lowers?|降低)\b", re.I)),
    ("compares_with", re.compile(r"\b(?:versus|vs\.?|compared (?:to|with)|对照)\b", re.I)),
]
STOP_ENTITY = {"however", "therefore", "moreover", "furthermore", "all", "table",
               "figure", "fig", "results", "experiments", "section", "we", "our",
               "this", "these", "it", "they", "in", "on", "of", "abstract"}
PRONOUNS = {"we", "our", "this", "these", "it", "they", "the", "a", "an", "in", "on", "of"}
MAX_ENTITIES_PER_PARA = 12


def clean_para(text: str) -> str:
    lines = [l for l in text.splitlines() if not l.lstrip().startswith("#")]
    return " ".join(" ".join(lines).split())


def ok_entity(term: str) -> bool:
    t = term.strip()
    low = t.lower()
    if len(low) < 3 or low in PRONOUNS:
        return False
    if low in STOP_ENTITY or low.split()[0] in STOP_ENTITY:
        return False
    if len(term.split()) == 1 and term.isupper() and len(term) <= 3:
        return False
    return True


def relation_of(para: str) -> str:
    for name, rx in REL_CUES:
        if rx.search(para):
            return name
    return "co_occurs"


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return

    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)

    texts = text_files(files)
    nodes, edges = [], []
    surfaces = defaultdict(set)
    node_index = {}

    for si, p in enumerate(texts, 1):
        sid = "%s#S%d" % (p.stem, si)
        b.add_source(p, sha256_file(p), "independent-paper")
        raw = read_text(p)
        b.add_evidence(claim="论文来源", locator={"file": p.name}, quote=raw[:250], source_id=sid)

        jats = JATS_RE.findall(raw)
        paras = [x.strip() for x in re.split(r"\n\s*\n", raw) if x.strip()]

        for pi, para in enumerate(paras, 1):
            pid = jats[pi - 1] if pi <= len(jats) else "P%03d" % pi
            text = clean_para(para)
            if not text:
                continue

            for m in ACRONYM_RE.finditer(text):
                surfaces[m.group(2).strip()].add(sid)

            local = []
            for m in ENT_RE.finditer(text):
                e = m.group(1).strip()
                if not ok_entity(e):
                    continue
                surfaces[e].add(sid)
                if e not in node_index:
                    node_index[e] = "N%04d" % (len(nodes) + 1)
                    nodes.append({"node_id": node_index[e], "surface": e, "type": "concept",
                                  "source_id": sid, "paragraph_id": pid,
                                  "quote": text[:300], "status": "candidate"})
                if e not in local:
                    local.append(e)
                if len(local) >= MAX_ENTITIES_PER_PARA:
                    break

            if len(local) >= 2:
                rel = relation_of(text)
                for i in range(len(local) - 1):
                    s, o = local[i], local[i + 1]
                    if s == o:
                        continue
                    edges.append({
                        "edge_id": "E%04d" % (len(edges) + 1),
                        "subject": s,
                        "relation": rel,
                        "object": o,
                        "source_id": sid,
                        "paragraph_id": pid,
                        "quote": text[:300],
                        "status": "candidate",
                        "relation_basis": "verb_cue" if rel != "co_occurs" else "co_occurrence_only",
                    })

    seen, deduped = set(), []
    for e in edges:
        key = (e["subject"].lower(), e["relation"], e["object"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)
        if len(deduped) >= 300:
            break
    edges = deduped

    conflicts = [{"surface": s, "source_ids": sorted(ids)}
                 for s, ids in surfaces.items() if len(ids) > 1]
    queries = [
        {"query": "Q1: 列出所有候选实体及来源", "result": [n["surface"] for n in nodes[:30]]},
        {"query": "Q2: 列出带动词线索的关系（排除 co_occurs）",
         "result": [{"s": e["subject"], "r": e["relation"], "o": e["object"]}
                    for e in edges if e["relation"] != "co_occurs"][:30]},
        {"query": "Q3: 哪些表面形式跨篇出现", "result": conflicts[:30]},
    ]

    typed = sum(1 for e in edges if e["relation"] != "co_occurs")
    b.set("nodes", nodes)
    b.set("edges", edges)
    b.set("cross_source_conflicts", conflicts)
    b.set("queries", queries)
    b.set("graph_stats", {"nodes": len(nodes), "edges": len(edges), "typed_edges": typed,
                          "cooccurrence_edges": len(edges) - typed, "sources": len(texts)})
    b.set("merge_policy", "仅在别名、缩写、同对象证据都一致时才合并；不同论文的条件、样本、数据集与数值不得合成一个结论。")
    if len(texts) < 2:
        b.add_uncertainty("输入中识别到的独立文本少于 2 篇；题面要求两篇独立论文，需核对 corpus-manifest.json。")
    b.add_uncertainty("节点/边为候选，须由 Agent 逐条回原文确认；co_occurs 只表示同段共现，不表示因果关系。")
    b.add_confirm("核对别名合并依据与不得合并的跨篇对象。")
    b.add_check("two_papers", len(texts) >= 2,
                "识别到 %d 篇独立文本，题面要求两篇论文" % len(texts))
    b.add_check("edges_with_evidence", bool(edges),
                "候选边 %d 条（其中带动词线索 %d 条），每条须有 quote 与 paragraph_id" % (len(edges), typed))
    b.add_check("queries_live", bool(edges), "三个查询基于最终节点与边实际执行")

    autofill_contract(b, {"nodes": nodes, "entities": nodes, "edges": edges,
                          "relations": edges, "queries": queries,
                          "cross_source_conflicts": conflicts})
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json",
          "| nodes=", len(nodes), "| edges=", len(edges), "| typed=", typed)


AXES = ["实体真实出现率", "关系类型/方向准确率", "别名归一正确率", "节点与边证据覆盖率",
        "查询结果可复核率", "跨篇整理耗时"]

if __name__ == "__main__":
    main()
