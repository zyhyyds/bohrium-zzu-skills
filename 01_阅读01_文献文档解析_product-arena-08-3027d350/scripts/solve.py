#!/usr/bin/env python3
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_core import (ResultBuilder, common_args, discover_inputs, load_case,
                           read_text, sha256_file, text_files, write_result)

from evidence_core import finalize_with_checks  # v2 audit gate

SKILL_ID = "reading01-pdf-parsing"
HEAD_RE = re.compile(r"^(?:#{1,6}\s|\d+(?:\.\d+)*\s+|Abstract\b|摘要|References\b|参考文献)", re.I)
CAP_RE = re.compile(r"^(?:Figure|Fig\.|Table|图|表)\s*\d+", re.I)
FORMULA_RE = re.compile(r"(=|\\frac|\\sum|\\int|\d+\s*[A-Za-z]\s*=|公式)")

def blocks_from_text(text):
    blocks = []
    for raw in re.split(r"\n\s*\n", text):
        s = raw.strip()
        if not s:
            continue
        first = s.splitlines()[0].strip()
        kind = "paragraph"
        if HEAD_RE.match(first):
            kind = "heading"
        elif CAP_RE.match(first):
            kind = "caption"
        elif ("|" in s) or re.search(r"\t{2,}", s):
            kind = "table"
        elif FORMULA_RE.search(s):
            kind = "formula"
        blocks.append({"block_id": "B%03d" % (len(blocks) + 1), "kind": kind,
                       "text": s[:4000], "first_line": first[:200]})
    return blocks

AXES = ["逐字提取完整率", "阅读顺序正确率", "表格行列归属准确率", "公式符号保真率", "锚点可回查率", "人工校对耗时"]


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return
    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)
    texts = text_files(files)
    all_blocks = []
    for p in texts:
        t = read_text(p)
        blocks = blocks_from_text(t)
        for blk in blocks:
            blk["source"] = p.name
            b.add_evidence(claim=blk["first_line"], locator={"file": p.name, "block_id": blk["block_id"]},
                           quote=blk["text"][:300], source_id=p.name)
        all_blocks.extend(blocks)
        b.add_source(p, sha256_file(p), "text-or-markup")
    pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
    for p in pdfs:
        b.add_source(p, sha256_file(p), "pdf")
    if pdfs:
        b.add_uncertainty("检测到 PDF 输入。本脚本只生成文本清单，不代替真实 PDF 读取；必须用平台提供的 pdf-text-tool / pdf-render-tool / ocr-tool 读取原文件后回填 blocks。")
    if not all_blocks and not pdfs:
        b.add_uncertainty("输入目录未发现可读取文本或 PDF，无法生成解析块。")
    caps = [x for x in all_blocks if x["kind"] == "caption"]
    heads = [x for x in all_blocks if x["kind"] == "heading"]
    tables = [x for x in all_blocks if x["kind"] == "table"]
    b.set("blocks", all_blocks)
    b.set("inventory", [{"path": str(p), "sha256": sha256_file(p), "suffix": p.suffix} for p in files])
    b.set("structure_summary", {"headings": len(heads), "captions": len(caps), "tables": len(tables), "other_blocks": len(all_blocks) - len(heads) - len(caps) - len(tables)})
    b.set("order_checks", {"caption_sequence": [x["first_line"] for x in caps],
                           "heading_sequence": [x["first_line"] for x in heads]})
    b.add_confirm("逐块核对阅读顺序、表格行列归属与公式符号是否失真。")
    b.add_check("inputs_discovered", bool(files), "输入目录发现 %d 个文件" % len(files))
    b.add_check("blocks_extracted", bool(all_blocks), "解析出 %d 个文本块" % len(all_blocks))
    b.add_check("pdf_text_layer", None if pdfs else True,
                "检测到 %d 个 PDF：必须用 pdf-text-tool 读取文字层并回填 blocks，不得用文本清单冒充" % len(pdfs) if pdfs else "无 PDF 输入")
    b.add_check("evidence_locators", all(isinstance(x.get("locator"), dict) and x["locator"] for x in b.data["evidence"]),
                "每条 evidence 必须有 file + block_id/页码 锚点")
    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json")

if __name__ == "__main__":
    main()
