#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (autofill_contract, ResultBuilder, common_args, load_case, read_text,
                           sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "writing09-methods-experiments"
KV_RE = re.compile(r"^\s*(?:[\"']?)([A-Za-z_][\w.\-]*)(?:[\"']?)\s*[:=]\s*([^\n#]+)")
FLAG_RE = re.compile(r"--([A-Za-z][\w\-]*)[=\s]+([^\s,]+)")
JSONKV_RE = re.compile(r"\"([A-Za-z_][\w.\-]*)\"\s*:\s*([^,\n}]+)")

# Natural-language parameter mentions that key:value regexes miss, e.g.
# "batch size of 256", "learning rate 3e-4", "3 epochs", "8 A100 GPUs".
NAT_RULES = [
    ("batch_size", re.compile(r"batch\s*size\s*(?:of|=|:)?\s*(\d+)", re.I), ""),
    ("learning_rate", re.compile(r"learning\s*rate\s*(?:of|=|:)?\s*([0-9]+(?:\.[0-9]+)?(?:e-?\d+)?)", re.I), ""),
    ("weight_decay", re.compile(r"weight\s*decay\s*(?:of|=|:)?\s*([0-9]+(?:\.[0-9]+)?(?:e-?\d+)?)", re.I), ""),
    ("dropout", re.compile(r"dropout\s*(?:of|=|:)?\s*([0-9.]+)", re.I), ""),
    ("epochs", re.compile(r"(\d+)\s*epochs?\b", re.I), "epoch"),
    ("steps", re.compile(r"(\d+)\s*(?:steps|iterations)\b", re.I), "step"),
]
NAT_REVERSE = [
    ("gpu_count", re.compile(r"(\d+)\s*(?:x\s*)?(?:A100|H100|V100|A800|DCU|GPU)s?\b", re.I), "device"),
    ("document_count", re.compile(r"([0-9.]+\s*[KMB]?)\s*(?:documents|samples|examples|queries)\b", re.I), "item"),
]

CATEGORIES = {
    "dataset": ["dataset", "data set", "corpus", "数据集", "train", "test", "val"],
    "seed": ["seed", "random_state", "随机种子"],
    "hardware": ["gpu", "cuda", "dcu", "hip", "device", "硬件"],
    "software": ["version", "python", "pytorch", "cuda version", "版本"],
    "baseline": ["baseline", "compare", "对照", "基线"],
    "repeat": ["repeat", "trial", "runs", "重复"],
    "split": ["split", "划分", "ratio"],
}

AXES = ["六类要素齐全度", "参数来源可追溯率", "条件一致性", "复现清单可执行率", "缺口追问覆盖率", "补写返工轮次"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    params = []
    exts = (".txt", ".md", ".json", ".xml", ".tex", ".bib", ".csv", ".yaml", ".yml", ".py", ".sh")
    for p in text_files(files, exts=exts):
        text = read_text(p)
        b.add_source(p, sha256_file(p), "config-log-code")
        b.add_evidence(claim="实验要素来源", locator={"file": p.name}, quote=text[:250], source_id=p.name)
        for ln, line in enumerate(text.splitlines(), 1):
            for rx in (KV_RE, FLAG_RE, JSONKV_RE):
                for m in rx.finditer(line):
                    params.append({"name": m.group(1), "value": m.group(2).strip()[:200],
                                   "source_file": p.name, "line": ln,
                                   "source_type": "config/log/code", "unit": "", "role": ""})
                    break
            for name, rx, unit in NAT_RULES:
                for m in rx.finditer(line):
                    params.append({"name": name, "value": m.group(1).strip(),
                                   "source_file": p.name, "line": ln,
                                   "source_type": "prose", "unit": unit, "role": ""})
            for name, rx, role in NAT_REVERSE:
                for m in rx.finditer(line):
                    params.append({"name": name, "value": m.group(1).strip(),
                                   "source_file": p.name, "line": ln,
                                   "source_type": "prose", "unit": "", "role": role})
    alltext = "\n".join(read_text(p) for p in files if p.suffix.lower() in (".txt", ".md", ".json", ".yaml", ".yml", ".py", ".sh", ".csv"))
    low = alltext.lower()
    missing = []
    for cat, keys in CATEGORIES.items():
        if not any(k.lower() in low for k in keys):
            missing.append(cat)
            b.add_confirm("材料未见 %s 信息：请作者确认或明确标为 not reported。" % cat)
    followups = ["请确认每个参数的单位与作用对象。", "请确认数据集版本、划分比例与随机方式。",
                 "请确认训练/验证/测试条件是否串台。", "请确认基线的版本与预算是否同条件。"]
    seen, deduped = set(), []
    for it in params:
        key = (it["name"], it["value"], it["source_file"], it["line"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    params = deduped
    b.set("parameter_table", params)
    b.set("missing_categories", missing)
    b.set("followup_questions", followups)
    b.set("reproducibility_checklist", ["代码版本", "环境依赖", "随机种子", "数据获取方式", "运行命令", "重复次数"])
    if not params:
        b.add_uncertainty("未从输入中抽出参数，需由 Agent 直接读取实际配置、日志与代码后回填。")
    b.add_check("params_extracted", bool(params), "抽出 %d 个参数，须逐条补单位与作用对象" % len(params))
    b.add_check("six_elements", not missing,
                "未见要素类别：%s" % (",".join(missing) if missing else "none"))
    b.add_check("no_fabricated_values", None,
                "材料中没有的参数/种子/版本一律 not reported 并追问，不得为段落顺畅补数值")
    autofill_contract(b, {
        "parameters": params,
        "parameter_table": params,
        "missing": missing,
        "missing_categories": missing,
        "followup_questions": followups,
        "reproducibility_checklist": b.data.get("reproducibility_checklist") or [],
    })
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
