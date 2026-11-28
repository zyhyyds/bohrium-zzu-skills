#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (autofill_contract, ResultBuilder, common_args, invariant_report, load_case,
                           locate, read_text, sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "writing02-language-polish"
ISSUES = [
    ("wordy", re.compile(r"\bin order to\b|\bdue to the fact that\b|\bfor the purpose of\b", re.I), "改用 to / because / for，减少冗余"),
    ("vague", re.compile(r"\b(very|quite|extremely|really|a lot of)\b", re.I), "替换为可核验的定量或限定表达"),
    ("overclaim", re.compile(r"\b(obviously|clearly|certainly|proves|definitely)\b", re.I), "降低断言强度，保留原文限定"),
    ("chinese_english", re.compile(r"\bmake\s+\w+\s+to\b|\bas we all know\b|\bwith the development of\b", re.I), "按目标语域重写，避免直译腔"),
    ("article", re.compile(r"\b(the|a|an)\s+(the|a|an)\b", re.I), "检查冠词重复"),
]

AXES = ["语法硬错误修正率", "术语一致率", "限定强度守恒率", "数据/引用/图表指向守恒率", "逐句说明完整率", "返修轮次"]


ACRONYM_DEF = re.compile(r"([A-Z][A-Za-z][A-Za-z\s-]{4,80})\s*\(([A-Z]{2,10})\)")
HYPHEN = re.compile(r"\b([a-z]{3,})-(?=[a-z]{3,}\b)")


def terminology_scan(text):
    """Find terminology inconsistencies: re-defined acronyms, hyphen variants, case drift."""
    issues, canon = [], {}

    # 1) acronym re-definition with a different expansion
    for m in ACRONYM_DEF.finditer(text):
        _w = " ".join(m.group(1).split()).lower().split()
        exp, ac = " ".join(_w[-6:]), m.group(2)
        if ac in canon and canon[ac] != exp:
            issues.append({"term": ac, "issue": "redefined", "forms": [canon[ac], exp],
                           "advice": "同一缩写只保留一个全称，首次定义后不再重复定义"})
        canon.setdefault(ac, exp)

    # 2) hyphen / non-hyphen variants of the same compound
    low = text.lower()
    seen = set()
    for m in HYPHEN.finditer(low):
        h = low[m.start():m.start() + len(m.group(1)) + 1 + 6]
        mm = re.match(r"([a-z]{3,})-([a-z]{3,})", h)
        if not mm:
            continue
        joined = mm.group(1) + mm.group(2)
        if re.search(r"\b" + re.escape(joined) + r"\b", low):
            key = tuple(sorted([mm.group(0), joined]))
            if key in seen:
                continue
            seen.add(key)
            issues.append({"term": joined, "issue": "hyphen_variant",
                           "forms": [mm.group(0), joined],
                           "advice": "全篇统一为带连字符或不带连字符的一种写法"})

    # 3) acronym case drift (e.g. "Llm" where "LLM" dominates)
    for ac in canon:
        for m in re.finditer(r"\b" + re.escape(ac) + r"\b", text, re.I):
            got = m.group(0)
            if got != ac and got.upper() == ac:
                issues.append({"term": ac, "issue": "case_drift", "forms": [ac, got],
                               "advice": "缩写保持全大写"})
                break
    return issues


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    worklist = []
    for p in texts:
        text = read_text(p)
        b.add_source(p, sha256_file(p), "manuscript")
        b.add_evidence(claim="润色输入来源", locator={"file": p.name}, quote=text[:250], source_id=p.name)
        for kind, pat, rule in ISSUES:
            for m in pat.finditer(text):
                s = max(0, m.start() - 80)
                e = min(len(text), m.end() + 80)
                sent = text[s:e].replace("\n", " ")
                worklist.append({"file": p.name, "issue_type": kind, "matched": m.group(0),
                                 "sentence": sent, "rule": rule, "locator": locate(text, m.group(0)) or {},
                                 "revised": "", "reason": "", "status": "pending"})
    source = "\n\n".join(read_text(p) for p in texts)

    # Conservative rule-based polish: only substitutions that cannot change
    # meaning. Anything requiring judgement stays as a suggestion in worklist.
    SAFE = [
        (re.compile(r"\bin order to\b", re.I), "to"),
        (re.compile(r"\bdue to the fact that\b", re.I), "because"),
        (re.compile(r"\bfor the purpose of\b", re.I), "for"),
        (re.compile(r"\ba large number of\b", re.I), "many"),
        (re.compile(r"\ba lot of\b", re.I), "many"),
        (re.compile(r"\bit is worth noting that\b", re.I), "notably,"),
        (re.compile(r"\bin the event that\b", re.I), "if"),
    ]
    polished = source
    applied = []
    for pat, rep in SAFE:
        def _sub(m, _rep=rep):
            # Preserve sentence-initial capitalisation of the replaced phrase.
            original = m.group(0)
            new = _rep
            if original[:1].isupper():
                new = new[:1].upper() + new[1:]
            return new
        for m in list(pat.finditer(polished)):
            new = _sub(m)
            applied.append({"before": m.group(0), "after": new,
                            "type": "wordy", "reason": "改用更简洁的学术表达，语义不变"})
        polished = pat.sub(_sub, polished)

    for w in worklist:
        if w["issue_type"] == "wordy":
            for a in applied:
                if w["matched"].lower() == a["before"].lower():
                    w["revised"] = a["after"]
                    w["reason"] = a["reason"]
                    w["status"] = "revised_auto"

    term_issues = terminology_scan(source)
    b.set("terminology_consistency", term_issues)
    b.set("terminology_stats", {"issues": len(term_issues),
                                "redefined": sum(1 for x in term_issues if x["issue"] == "redefined"),
                                "hyphen_variant": sum(1 for x in term_issues if x["issue"] == "hyphen_variant"),
                                "case_drift": sum(1 for x in term_issues if x["issue"] == "case_drift")})
    for x in term_issues:
        worklist.append({"file": "", "issue_type": "terminology", "matched": x["term"],
                         "sentence": " / ".join(x["forms"]), "rule": x["advice"],
                         "locator": {}, "revised": "", "reason": "", "status": "pending"})

    target = polished
    b.set("polish_worklist", worklist)
    b.set("polished_text", polished)
    b.set("invariant_checks", invariant_report(source, target))
    b.set("auto_applied_changes", applied)
    if polished.strip() and polished != source:
        b.finalize("success")
    b.set("rules", ["最小编辑：不整段重写", "限定强度、因果/相关、否定范围、数字单位、引用编号、图表指向必须守恒",
                    "每处修改给出原文、改文、类型、理由", "术语表驱动全篇回扫"])
    if not worklist:
        b.add_uncertainty("未检出预设语言问题模式；仍需人工通读术语一致性与语域贴合度。")
    b.add_confirm("逐句核对改写是否改变限定强度或专业含义。")
    b.add_check("worklist_generated", bool(worklist), "检出 %d 处候选问题" % len(worklist))
    b.add_check("invariant_runtime", "numbers_missing" not in (b.data.get("invariant_checks") or {}),
                "守恒检查：数字缺失必须为零或在 uncertainty 中解释")
    b.add_check("changes_documented", bool(applied),
                "已自动应用 %d 处安全改写，均含 before/after/type/reason" % len(applied))
    autofill_contract(b, {
        "changes": applied,
        "polished_text": polished,
        "text": polished,
        "worklist": worklist,
        "invariant_checks": b.data.get("invariant_checks"),
        "glossary": b.data.get("glossary") or [],
        "terminology": term_issues,
    })
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
