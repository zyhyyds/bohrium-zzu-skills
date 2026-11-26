#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (ResultBuilder, common_args, load_case, read_text,
                           sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "writing13-latex-compile"
CITE_RE = re.compile(r"\\cite(?:\[[^\]]*\])*\{([^}]*)\}")
REF_RE = re.compile(r"\\ref\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]*)\}")
BEGIN_RE = re.compile(r"\\begin\{([^}]*)\}")
END_RE = re.compile(r"\\end\{([^}]*)\}")
BIB_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.I)
IMAGE_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])*\{([^}]*)\}")

AXES = ["编译成功率", "错误根因定位准确率", "修复正确率", "公式/表格/引用对齐率", "可复现构建记录完整率", "定位报错耗时"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texfiles = [p for p in files if p.suffix.lower() == ".tex"]
    bibfiles = [p for p in files if p.suffix.lower() == ".bib"]
    bibkeys = set()
    for p in bibfiles:
        bibkeys.update(BIB_RE.findall(read_text(p)))
        b.add_source(p, sha256_file(p), "bib")
    issues, cites, refs, labels, images = [], set(), set(), set(), []
    for p in texfiles:
        text = read_text(p)
        b.add_source(p, sha256_file(p), "tex")
        b.add_evidence(claim="LaTeX 源码来源", locator={"file": p.name}, quote=text[:250], source_id=p.name)
        for m in CITE_RE.finditer(text):
            cites.update(x.strip() for x in m.group(1).split(",") if x.strip())
        refs.update(x.strip() for x in REF_RE.findall(text))
        labels.update(x.strip() for x in LABEL_RE.findall(text))
        images.extend([(p.name, x) for x in IMAGE_RE.findall(text)])
        opens = [x for x in BEGIN_RE.findall(text)]
        closes = END_RE.findall(text)
        for name in sorted(set(opens)):
            if opens.count(name) != closes.count(name):
                issues.append({"file": p.name, "line": 0, "severity": "error", "type": "environment_mismatch",
                               "detail": name + " begin=" + str(opens.count(name)) + " end=" + str(closes.count(name))})
        for ln, line in enumerate(text.splitlines(), 1):
            if line.count("{") != line.count("}"):
                issues.append({"file": p.name, "line": ln, "severity": "warning", "type": "brace_balance",
                               "detail": line.strip()[:200]})
        if not re.search(r"\\documentclass", text):
            issues.append({"file": p.name, "line": 0, "severity": "warning", "type": "missing_documentclass", "detail": ""})
        for key in ("title", "author"):
            m = re.search(r"\\%s\{([^}]*)\}" % key, text, re.I)
            if not m or not m.group(1).strip() or "TODO" in m.group(1).upper():
                issues.append({"file": p.name, "line": 0, "severity": "warning", "type": "template_required_field",
                               "detail": key})
    missing_cites = sorted(cites - bibkeys) if bibkeys else sorted(cites)
    missing_refs = sorted(refs - labels)
    for key in missing_cites:
        issues.append({"file": ",".join(p.name for p in bibfiles) or "(no bib)", "line": 0,
                       "severity": "error", "type": "missing_bib_key", "detail": key})
    for key in missing_refs:
        issues.append({"file": "cross-reference", "line": 0, "severity": "error", "type": "undefined_ref", "detail": key})
    for fname, img in images:
        if not any(Path(p).name == Path(img).name for p in files):
            issues.append({"file": fname, "line": 0, "severity": "warning", "type": "missing_figure", "detail": img})
    b.set("issues", issues)
    b.set("compile_plan", ["pdflatex -interaction=nonstopmode main.tex", "bibtex main",
                           "pdflatex -interaction=nonstopmode main.tex", "pdflatex -interaction=nonstopmode main.tex"])
    b.set("environment_record", ["TeX 发行版", "模板版本", "宏包版本", "字体版本", "编译命令与轮次"])
    if not texfiles:
        b.add_uncertainty("输入中未发现 .tex 文件，无法静态检查；需核对实际工程结构。")
    b.add_confirm("用平台 latex-compiler 真实编译，把日志与根因回填 result.json。")
    b.add_check("tex_found", bool(texfiles), "发现 %d 个 .tex 文件" % len(texfiles))
    b.add_check("issues_classified", True,
                "静态检查问题 %d 条；0 条也必须用 latex-compiler 真实编译确认" % len(issues))
    b.add_check("compile_executed", None,
                "须真实编译并把完整日志、轮次、TeX 发行版与宏包/字体版本回填 result.json")
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
