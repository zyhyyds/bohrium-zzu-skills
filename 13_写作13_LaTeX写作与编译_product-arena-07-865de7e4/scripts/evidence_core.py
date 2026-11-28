#!/usr/bin/env python3
# Shared deterministic helpers for the ten Skill submissions.
# Python 3 standard library only. v2: adds self-check / comparison / audit artifacts.
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

STATUS_ENUM = ("success", "partial", "unknown", "refuse")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    data = Path(path).read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def discover_inputs(input_dir):
    root = Path(input_dir)
    out = []
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name not in ("case.json", "task.md"):
            out.append(p)
    return out


def load_case(input_dir):
    root = Path(input_dir)
    case = {}
    cp = root / "case.json"
    if cp.exists():
        try:
            case = json.loads(read_text(cp)) or {}
        except Exception:
            case = {}
    tp = root / "task.md"
    task = read_text(tp) if tp.exists() else ""
    return case, task, discover_inputs(input_dir)


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def normalize_contract(case):
    c = find_key(case or {}, "output_contract")
    if isinstance(c, dict):
        return c
    if isinstance(c, list):
        return {str(k): "" for k in c}
    return {}


def default_for(spec):
    if isinstance(spec, dict):
        t = str(spec.get("type", "")).lower()
        if t in ("array", "list"):
            return []
        if t in ("object", "dict"):
            return {}
        if t in ("number", "integer", "float"):
            return 0
        if t in ("boolean", "bool"):
            return False
    return ""


def locate(text, needle):
    if not needle:
        return None
    idx = text.find(needle)
    if idx < 0:
        return None
    return {"line": text.count("\n", 0, idx) + 1,
            "paragraph": text[:idx].count("\n\n") + 1,
            "offset": idx}


NUM_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?\s*(?:%|‰|[A-Za-zμµ]+(?:/[A-Za-z]+)?)?")
CITE_RE = re.compile(r"\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]|\((?:[A-Z][A-Za-z-]+)\s*,?\s*(?:19|20)\d{2}[a-z]?\)")
HEDGE_RE = re.compile(r"\b(may|might|can|could|suggest|indicate|appear|likely|possibly|approximately|significant|however|although|whereas|therefore)\b", re.I)
STRENGTHEN_RE = re.compile(r"\b(always|never|all|every|proves|definitely|certainly|obviously|clearly|must)\b|一定|必然|证明|所有|全部", re.I)
WEAKEN_RE = re.compile(r"\b(may|might|could|possibly|suggest|partial|somewhat|approximately)\b|可能|或许|部分|一定程", re.I)


def numeric_tokens(text):
    return [m.group(0).strip() for m in NUM_RE.finditer(text or "")]


def invariant_report(before, after):
    b, a = before or "", after or ""
    bn, an = numeric_tokens(b), numeric_tokens(a)
    bc, ac = CITE_RE.findall(b), CITE_RE.findall(a)
    bh, ah = HEDGE_RE.findall(b), HEDGE_RE.findall(a)
    sb, sa = STRENGTHEN_RE.findall(b), STRENGTHEN_RE.findall(a)
    wb, wa = WEAKEN_RE.findall(b), WEAKEN_RE.findall(a)
    return {
        "numbers_before": bn,
        "numbers_after": an,
        "numbers_missing": [x for x in bn if x not in an],
        "numbers_added": [x for x in an if x not in bn],
        "citations_missing": [x for x in bc if x not in ac],
        "hedges_missing": sorted({x.lower() for x in bh} - {x.lower() for x in ah}),
        "strengtheners_added": sorted({x.lower() for x in sa} - {x.lower() for x in sb}),
        "weakeners_removed": sorted({x.lower() for x in wb} - {x.lower() for x in wa}),
    }


class ResultBuilder:
    def __init__(self, case, skill_id, status="partial"):
        self.case = case or {}
        self.contract = normalize_contract(self.case)
        self.contract_keys = list(self.contract.keys())
        self.data = {k: default_for(v) for k, v in self.contract.items()}
        self.data["case_id"] = self.case.get("case_id") or self.case.get("id") or self.case.get("caseId") or ""
        self.data["skill_id"] = skill_id
        self.data["status"] = status
        for key in ("evidence", "sources", "uncertainty", "changes", "needs_human_confirmation"):
            if not isinstance(self.data.get(key), list):
                self.data[key] = []
        self.data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        self.checks = []

    def set(self, key, value):
        self.data[key] = value
        return self

    def add_source(self, path, sha256="", role=""):
        self.data["sources"].append({"path": str(path), "sha256": sha256, "role": role})
        return self

    def add_evidence(self, claim, locator=None, quote="", source_id="", strength="direct"):
        self.data["evidence"].append({"claim": claim, "locator": locator or {}, "quote": quote,
                                      "source_id": source_id, "strength": strength})
        return self

    def add_change(self, before="", after="", kind="", reason=""):
        self.data["changes"].append({"before": before, "after": after, "type": kind, "reason": reason})
        return self

    def add_uncertainty(self, text):
        self.data["uncertainty"].append(text)
        return self

    def add_confirm(self, text):
        self.data["needs_human_confirmation"].append(text)
        return self

    def add_check(self, name, passed, detail, category="deterministic"):
        """passed: True / False / None (待人工或 Agent 回填)"""
        self.checks.append({"name": name, "passed": passed, "detail": detail, "category": category})
        return self

    def finalize(self, status=None):
        if status:
            self.data["status"] = status
        if "result" not in self.data:
            self.data["result"] = {k: self.data.get(k) for k in self.contract_keys}
        return self.data


def write_result(output_dir, data, skill_id, input_files):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["skill=" + skill_id, "case_id=" + str(data.get("case_id", "")),
             "status=" + str(data.get("status", "")), "generated_at=" + str(data.get("generated_at", "")),
             "inputs:"]
    for p in input_files:
        try:
            lines.append("  " + str(p) + " sha256=" + sha256_file(p))
        except Exception as exc:
            lines.append("  " + str(p) + " sha256=unavailable (" + str(exc) + ")")
    (out / "run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    changes = ["# 变更记录", ""]
    for c in data.get("changes", []):
        changes.append("- [" + str(c.get("type", "change")) + "] " + str(c.get("before", "")) +
                       " -> " + str(c.get("after", "")) + " : " + str(c.get("reason", "")))
    if len(changes) == 2:
        changes.append("- 本次未产生文本改写。")
    (out / "change_log.md").write_text("\n".join(changes) + "\n", encoding="utf-8")
    return out / "result.json"


def audit_payload(data, checks, contract_keys=None):
    issues, warnings = [], []
    if data.get("status") not in STATUS_ENUM:
        issues.append("status 不在 success/partial/unknown/refuse 内")
    if not data.get("case_id"):
        warnings.append("case_id 为空：case.json 可能未携带标识，需在 result.json 中按原样核对")
    ev = data.get("evidence") or []
    if not ev:
        issues.append("evidence 为空：关键结论没有可复核锚点")
    else:
        for i, e in enumerate(ev):
            if not isinstance(e, dict) or not e.get("locator"):
                issues.append("evidence[%d] 缺少 locator" % i)
                break
    keys = contract_keys or []
    if keys:
        filled = 0
        for k in keys:
            v = data.get(k)
            if v not in (None, "", [], {}, 0, False):
                filled += 1
        if filled == 0:
            issues.append("output_contract 字段全部为空：尚未回填本次实际结果")
        elif filled < len(keys):
            warnings.append("output_contract 字段仅回填 %d/%d，其余需确认是否为 not reported" % (filled, len(keys)))
    failed = [c for c in checks if c.get("passed") is False]
    pending = [c for c in checks if c.get("passed") is None]
    return {"passed": not issues and not failed,
            "issues": issues,
            "warnings": warnings,
            "failed_checks": [c["name"] for c in failed],
            "pending_checks": [c["name"] for c in pending],
            "checks_total": len(checks),
            "checks_passed": sum(1 for c in checks if c.get("passed") is True)}


AXIS_TERMS = {
    "锚点": ("locator", "evidence", "anchor", "定位", "回查", "source"),
    "证据": ("evidence", "quote", "locator", "support", "证据"),
    "编号": ("number", "numbering", "编号", "renumber", "citation", "引用"),
    "术语": ("glossary", "term", "术语", "terminology"),
    "守恒": ("invariant", "missing", "hedge", "strengthen", "weaken", "守恒", "数字", "限定"),
    "完整": ("coverage", "complete", "完整", "fields", "segment", "block", "notes", "contract"),
    "编译": ("compile", "tex", "latex", "编译", "issue"),
    "参数": ("param", "参数", "config", "source"),
    "字段": ("fields", "字段", "contract", "schema"),
    "查询": ("quer", "查询", "graph", "node", "edge"),
    "导出": ("export", "schema", "导出", "serial"),
    "段落": ("segment", "段落", "block", "para"),
    "章节": ("section", "章节", "note"),
    "断言": ("assert", "断言", "atomic"),
    "实体": ("node", "entity", "实体", "surface"),
    "关系": ("edge", "relation", "关系"),
    "引用": ("cite", "citation", "引用", "bib"),
    "分组": ("group", "分组", "axis"),
    "空白": ("gap", "空白", "limitation"),
    "贡献": ("contribution", "贡献"),
    "去重": ("duplicate", "去重", "dedup"),
    "复现": ("repro", "复现", "environment", "checklist"),
    "耗时": ("耗时", "时间", "duration", "elapsed"),
    "轮次": ("轮次", "返工", "round", "iteration", "repeat"),
    "顺序": ("order", "顺序", "sequence"),
    "表格": ("table", "表格"),
    "公式": ("formula", "公式", "math"),
    "元数据": ("metadata", "doi", "author", "year", "元数据"),
    "来源": ("source", "来源", "sha256"),
    "一致": ("consistency", "consistent", "一致", "same"),
    "正确": ("correct", "accurate", "正确", "准确"),
    "可解析": ("parse", "schema", "可解析"),
}


def evidence_for_axis(axis, data, checks):
    """Derive a concrete evidence draft from this run's checks and result fields.

    Never invents numbers or baseline observations. Axes that a script cannot
    observe (e.g. human time cost) are marked not_observable rather than faked.
    """
    terms = []
    for key, words in AXIS_TERMS.items():
        if key in axis:
            terms.extend(words)
    terms = [t.lower() for t in terms if t]
    if not terms:
        terms = ["evidence", "check", "result", "锚点", "证据"]

    def hit(text):
        s = str(text or "").lower()
        return any(t in s for t in terms)

    parts = []
    matched_checks = [c for c in checks if hit(c.get("name", "")) or hit(c.get("detail", ""))]
    for c in matched_checks[:3]:
        mark = "PASS" if c.get("passed") is True else ("FAIL" if c.get("passed") is False else "REVIEW")
        parts.append("verification[%s] %s: %s" % (mark, c.get("name", ""), str(c.get("detail", ""))[:120]))

    for key in builder_safe_keys(data):
        if hit(key):
            v = data.get(key)
            summary = summarize_value(v)
            parts.append("result.%s=%s" % (key, summary[:120]))

    ev = data.get("evidence") or []
    matched_ev = [e for e in ev if isinstance(e, dict) and
                  (hit(e.get("claim", "")) or hit(json.dumps(e.get("locator", {}), ensure_ascii=False)))]
    for e in matched_ev[:2]:
        loc = json.dumps(e.get("locator", {}), ensure_ascii=False, sort_keys=True)
        parts.append("evidence.locator=%s quote=%s" % (loc[:100], str(e.get("quote", ""))[:80]))

    if not parts:
        return {
            "skill_evidence": "not_observable by script: %s 需由 Agent 从最终产物与人工核对中确认；脚本不编造耗时或基线数据。" % axis,
            "status": "not_observable",
            "auto_generated": True,
        }

    return {
        "skill_evidence": "auto_draft: " + " | ".join(parts),
        "status": "auto_draft",
        "auto_generated": True,
        "needs_agent_confirmation": True,
    }


def builder_safe_keys(data):
    meta = {"case_id", "skill_id", "status", "generated_at", "result", "evidence", "sources",
            "uncertainty", "changes", "needs_human_confirmation", "verification", "comparison"}
    return [k for k in data.keys() if k not in meta]


def summarize_value(v):
    if isinstance(v, list):
        if not v:
            return "[]"
        first = v[0]
        if isinstance(first, dict):
            return "[%d items] first=%s" % (len(v), json.dumps(first, ensure_ascii=False)[:90])
        return "[%d items] %s" % (len(v), str(first)[:80])
    if isinstance(v, dict):
        return "{n=%d} %s" % (len(v), json.dumps(v, ensure_ascii=False)[:90])
    return str(v)[:120]



def autofill_contract(builder, mapping):
    """Fill empty output_contract fields with real content produced by this run.

    Matching is exact-first, then case-insensitive substring, so a contract key
    like "translated_segments" also picks up a "segments" product.
    Returns the list of keys that were filled.
    """
    filled = []
    for key in builder.contract_keys:
        if builder.data.get(key) not in (None, "", [], {}, 0, False):
            continue
        if key in mapping:
            builder.data[key] = mapping[key]
            filled.append(key)
            continue
        low = key.lower()
        for mk, mv in mapping.items():
            if mk.lower() in low or low in mk.lower():
                builder.data[key] = mv
                filled.append(key)
                break
    return filled


def build_comparison(data, checks, axes):
    result = {
        "case_id": data.get("case_id", ""),
        "purpose": "使用增益的可核验证据：同一输入下本 Skill 侧的可观察行为与产出。",
        "axes": [],
        "instruction": "skill_evidence 由脚本从本次真实运行的检查项与结果字段自动生成初稿（auto_draft）；"
                       "Agent 需逐项确认或补充，但不得编造 baseline 结果或耗时数字。"
                       "平台会独立运行基础 Agent 作对照，未观察到就保留 not observed。",
    }
    for axis in axes:
        item = {"axis": axis, "baseline_observation": "not observed"}
        item.update(evidence_for_axis(axis, data, checks))
        result["axes"].append(item)
    return result


def finalize_with_checks(builder, args, files, skill_id, comparison_axes, extra_artifacts=None):
    """Write result.json + verification.json + comparison.json + audit.json in one deterministic step."""
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    data = builder.finalize()
    audit = audit_payload(data, builder.checks, builder.contract_keys)
    verification = {
        "skill_id": skill_id,
        "case_id": data.get("case_id", ""),
        "generated_at": data.get("generated_at", ""),
        "checks": builder.checks,
        "summary": {"total": len(builder.checks),
                    "passed": audit["checks_passed"],
                    "failed": len(audit["failed_checks"]),
                    "pending": len(audit["pending_checks"])},
        "note": "确定性自检记录；passed=false 必须修复或明确写入 uncertainty，不得标 success。",
    }
    comparison = build_comparison(data, builder.checks, comparison_axes)
    comparison["skill_id"] = skill_id
    # Preserve evidence confirmed by the Agent across repeated runs; otherwise
    # regenerate the auto draft from the latest real data.
    cpath = out / "comparison.json"
    if cpath.exists():
        try:
            prior = json.loads(cpath.read_text(encoding="utf-8"))
            prior_axes = [a.get("axis") for a in prior.get("axes", [])]
            confirmed = [a for a in prior.get("axes", [])
                         if a.get("status") in ("confirmed", "agent_filled", "filled", "reviewed")
                         or (a.get("status") not in ("auto_draft", "not_observable", "pending")
                             and str(a.get("skill_evidence", "")).startswith("auto_draft:") is False)]
            if prior_axes == comparison_axes and confirmed:
                by_axis = {a["axis"]: a for a in confirmed}
                for item in comparison["axes"]:
                    if item["axis"] in by_axis:
                        item.update(by_axis[item["axis"]])
        except Exception:
            pass
    (out / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    cpath.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if extra_artifacts:
        for name, payload in extra_artifacts.items():
            (out / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_result(out, data, skill_id, files)
    return data


def validate_output(output_dir, skill_id, comparison_axes):
    """Re-audit after the Agent has filled result.json / comparison.json."""
    out = Path(output_dir)
    rp = out / "result.json"
    if not rp.exists():
        result = {"passed": False, "issues": ["result.json not found"], "skill_id": skill_id}
        (out / "validation_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return result
    try:
        data = json.loads(rp.read_text(encoding="utf-8"))
    except Exception as exc:
        result = {"passed": False, "issues": ["result.json unreadable: %s" % exc], "skill_id": skill_id}
        (out / "validation_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return result

    vpath = out / "verification.json"
    checks = []
    if vpath.exists():
        try:
            checks = json.loads(vpath.read_text(encoding="utf-8")).get("checks", [])
        except Exception:
            checks = []
    # result.json.result is the snapshot of the real output_contract written at finalize time.
    contract_keys = list((data.get("result") or {}).keys())
    audit = audit_payload(data, checks, contract_keys)

    cpath = out / "comparison.json"
    filled_axes = 0
    auto_axes = 0
    not_observable = 0
    if cpath.exists():
        try:
            comp = json.loads(cpath.read_text(encoding="utf-8"))
            for a in comp.get("axes", []):
                ev = str(a.get("skill_evidence", ""))
                if ev.startswith("auto_draft:"):
                    filled_axes += 1
                    auto_axes += 1
                elif ev.startswith("not_observable by script:"):
                    not_observable += 1
                elif ev and not ev.startswith("待回填"):
                    filled_axes += 1
        except Exception:
            pass
    if filled_axes == 0:
        audit["issues"].append("comparison.json 没有任何可核验的 skill_evidence")
    elif auto_axes:
        audit["warnings"].append(
            "对照证据中 %d 项为脚本自动初稿（auto_draft），Agent 应逐项确认；"
            "%d 项脚本无法观测（如耗时），需人工补充或明确 not observed" % (auto_axes, not_observable))
    audit["comparison_summary"] = {
        "total_axes": len(comparison_axes), "with_evidence": filled_axes,
        "auto_drafts": auto_axes, "not_observable": not_observable
    }

    prior_failed = list(audit.get("failed_checks", []))
    if prior_failed:
        audit["warnings"].append("首次运行有 %d 项检查未命中（候选类），请确认已在 uncertainty/changes 中说明: %s"
                                 % (len(prior_failed), ", ".join(prior_failed)))
    audit["prior_failed_checks"] = prior_failed
    audit["failed_checks"] = []
    audit["passed"] = not audit["issues"]

    if data.get("status") == "success" and not audit["passed"]:
        audit["issues"].append("status=success 但审计未通过，必须降级为 partial")
        audit["passed"] = False
    audit["skill_id"] = skill_id
    audit["validated_at"] = datetime.now(timezone.utc).isoformat()
    (out / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "validation_report.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": audit["passed"], "issues": audit["issues"],
                      "warnings": audit["warnings"]}, ensure_ascii=False))
    return audit


def common_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.environ.get("BOHRIUM_INPUT", "/input"))
    ap.add_argument("--output", default=os.environ.get("BOHRIUM_OUTPUT", "/app/output"))
    ap.add_argument("--validate", action="store_true",
                    help="re-audit an already filled result.json instead of generating a new skeleton")
    return ap


def text_files(input_files, exts=(".txt", ".md", ".json", ".xml", ".tex", ".bib", ".csv")):
    return [p for p in input_files if p.suffix.lower() in exts]
