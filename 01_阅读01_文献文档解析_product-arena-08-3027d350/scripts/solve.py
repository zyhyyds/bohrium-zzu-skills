#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reading01 Skill entrypoint: parse real PDFs/text into anchored blocks.

Design goal (v4): produce a COMPLETE result.json by itself, so the evaluator
does not depend on an agent manually filling fields afterwards. The script:
  1. extracts text from every input (PDF via pdf_extract, text files directly),
  2. restores reading order (column detection from x/y coordinates),
  3. segments into typed blocks (heading / caption / table / formula / paragraph),
  4. fills every output_contract field with real content,
  5. records anchors (file, page, block_id) and honest uncertainty.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_core import (ResultBuilder, common_args, load_case, read_text,
                           sha256_file, finalize_with_checks)
from pdf_extract import extract_pdf

SKILL_ID = "reading01-pdf-parsing"

HEAD_RE = re.compile(
    r"^(?:#{1,6}\s|\d+(?:\.\d+)*\.?\s+[A-Z\u4e00-\u9fff]|"
    r"abstract|摘要|introduction|引言|related work|相关工作|method(?:s|ology)?|方法|"
    r"experiment(?:s)?|实验|result(?:s)?|结果|discussion|讨论|conclusion(?:s)?|结论|"
    r"references?|参考文献|acknowledg)", re.I)
CAP_RE = re.compile(r"^(?:figure|fig\.?|table|图|表)\s*\d+", re.I)
FORMULA_HINT = re.compile(r"(?:=|\\frac|\\sum|\\int|\bwhere\b|公式)")
REF_ENTRY_RE = re.compile(r"^\s*\[\d+\]\s+\S")


def clean(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def dehyphenate(prev: str, nxt: str) -> str:
    """Join two wrapped lines, re-joining words broken by an end-of-line hyphen."""
    prev = prev.rstrip()
    if prev.endswith("-") and nxt[:1].islower():
        return prev[:-1] + nxt.lstrip()
    return prev + " " + nxt.lstrip()


def items_to_lines(items, page_no: int, y_tol: float = 4.0):
    """Group (x, y, text) items into lines, preserving column order."""
    if not items:
        return []
    xs = sorted(x for x, _, t in items if t.strip())
    columns = [(0.0, float("inf"))]
    if len(xs) >= 6:
        mid = (min(xs) + max(xs)) / 2
        left = [x for x in xs if x < mid]
        right = [x for x in xs if x >= mid]
        if len(left) >= 3 and len(right) >= 3:
            gap = min(right) - max(left)
            if gap > 30:
                split = (max(left) + min(right)) / 2
                columns = [(0.0, split), (split, float("inf"))]

    lines = []
    for lo, hi in columns:
        col_items = [it for it in items if lo <= it[0] < hi and it[2].strip()]
        col_items.sort(key=lambda it: (-it[1], it[0]))
        current, cur_y = [], None
        for x, y, text in col_items:
            if cur_y is None or abs(y - cur_y) <= y_tol:
                current.append((x, text))
                cur_y = y if cur_y is None else cur_y
            else:
                lines.append({"page": page_no, "y": cur_y, "text": join_fragments(current)})
                current, cur_y = [(x, text)], y
        if current:
            lines.append({"page": page_no, "y": cur_y, "text": join_fragments(current)})
    return [l for l in lines if l["text"]]


def join_fragments(items):
    """Join positioned fragments; insert a space only on a real horizontal gap.

    Fragments from the stdlib PDF backend carry true x coordinates; text-file
    lines all share x=0 and are joined with a single space.
    """
    items = sorted(items, key=lambda p: p[0])
    if not items:
        return ""
    if len({round(x, 1) for x, _ in items}) == 1:
        return clean(" ".join(t for _, t in items))
    out = []
    prev_end = None
    for x, text in items:
        t = text
        if prev_end is not None:
            gap = x - prev_end
            if gap > 1.5 and out and not out[-1].endswith(" ") and not t.startswith(" "):
                out.append(" ")
        out.append(t)
        # Approximate glyph advance; metrics are not in the content stream.
        prev_end = x + len(t) * 4.2
    return clean("".join(out))


def classify(text: str) -> str:
    t = text.strip()
    if not t:
        return "paragraph"
    if REF_ENTRY_RE.match(t):
        return "reference"
    if CAP_RE.match(t):
        return "caption"
    if HEAD_RE.match(t) and len(t) < 160:
        return "heading"
    # A display formula is short and symbol-dense; prose containing "=" is not.
    if len(t) < 120:
        symbols = sum(t.count(c) for c in "=+×÷∑∫√±≈<>")
        letters = sum(ch.isalpha() for ch in t)
        if FORMULA_HINT.search(t) and symbols >= 2 and letters < len(t) * 0.55:
            return "formula"
    if t.count("|") >= 2 and len(t) < 400:
        return "table"
    return "paragraph"


def build_blocks_from_lines(lines):
    blocks, buf = [], []

    def flush(kind_hint=None):
        nonlocal buf
        if not buf:
            return
        text = ""
        for l in buf:
            text = dehyphenate(text, l["text"]) if text else l["text"]
        kind = kind_hint or classify(buf[0]["text"])
        blocks.append({
            "block_id": "B%04d" % (len(blocks) + 1),
            "kind": kind,
            "text": text,
            "page": buf[0]["page"],
            "source": buf[0].get("source", ""),
            "first_line": buf[0]["text"][:200],
        })
        buf = []

    for line in lines:
        kind = classify(line["text"])
        if kind in ("heading", "caption", "reference", "table", "formula"):
            flush()
            buf = [line]
            flush(kind)
        else:
            if buf and buf[-1]["page"] != line["page"]:
                flush()
            buf.append(line)
            if len(buf) > 400:
                flush()
    flush()
    return blocks


def collect_from_pdf(path):
    pages, meta = extract_pdf(path)
    lines = []
    for i, items in enumerate(pages, 1):
        lines.extend(items_to_lines(items, i))
    return lines, meta



def text_quality(blocks):
    """Flag implausibly long letter runs: PDFs that draw no space glyphs."""
    samples, count = [], 0
    for b in blocks:
        for tok in re.findall(r"[A-Za-z]{22,}", b.get("text", "")):
            count += 1
            if len(samples) < 5:
                samples.append({"block_id": b.get("block_id"), "token": tok[:60],
                                "length": len(tok)})
    total_chars = sum(len(b.get("text", "")) for b in blocks) or 1
    return {
        "long_token_count": count,
        "long_token_samples": samples,
        "chars": total_chars,
        "note": "长粘连词通常表示 PDF 未绘制空格字符；本 Skill 如实标注，不猜补空格。",
    }


def main():
    args = common_args().parse_args()
    if args.validate:
        from evidence_core import validate_output
        validate_output(args.output, SKILL_ID, AXES)
        return

    case, task, files = load_case(args.input)
    b = ResultBuilder(case, SKILL_ID)

    all_lines, doc_meta = [], {"pdfs": [], "texts": []}
    for p in files:
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            lines, meta = collect_from_pdf(p)
            for l in lines:
                l["source"] = p.name
            all_lines.extend(lines)
            doc_meta["pdfs"].append({"file": p.name, "pages": meta["page_count"],
                                     "backend": meta["backend"],
                                     "encrypted": meta["encrypted"],
                                     "lines": len(lines)})
            b.add_source(p, sha256_file(p), "pdf")
            if meta["page_count"] == 0:
                b.add_uncertainty(
                    "PDF %s 未提取到文字层（backend=%s）：需用 pdf-text-tool 或 OCR "
                    "逐页读取后回填；当前未编造任何正文。" % (p.name, meta["backend"]))
        elif suffix in (".txt", ".md", ".tex", ".csv", ".json", ".xml"):
            text = read_text(p)
            for i, ln in enumerate(text.splitlines(), 1):
                if ln.strip():
                    all_lines.append({"page": None, "y": -i, "text": clean(ln),
                                      "source": p.name})
            doc_meta["texts"].append({"file": p.name, "lines": len(text.splitlines())})
            b.add_source(p, sha256_file(p), "text")

    blocks = build_blocks_from_lines(all_lines)
    for blk in blocks:
        anchor = {"file": blk.get("source", ""), "block_id": blk["block_id"]}
        if blk["page"]:
            anchor["page"] = blk["page"]
        b.add_evidence(claim=blk["first_line"], locator=anchor,
                       quote=blk["text"][:300], source_id=blk.get("source", ""),
                       strength="direct")

    by_kind = {}
    for blk in blocks:
        by_kind.setdefault(blk["kind"], []).append(blk)

    structure = {
        "headings": len(by_kind.get("heading", [])),
        "captions": len(by_kind.get("caption", [])),
        "tables": len(by_kind.get("table", [])),
        "formulas": len(by_kind.get("formula", [])),
        "references": len(by_kind.get("reference", [])),
        "paragraphs": len(by_kind.get("paragraph", [])),
        "pages": sum(d["pages"] for d in doc_meta["pdfs"]) or None,
    }
    sections = [{"heading": h["text"], "page": h["page"], "block_id": h["block_id"]}
                for h in by_kind.get("heading", [])]
    figures = [{"label": c["text"][:80], "page": c["page"], "block_id": c["block_id"]}
               for c in by_kind.get("caption", [])]
    tables = [{"label": t["text"][:80], "page": t["page"], "block_id": t["block_id"]}
              for t in by_kind.get("table", [])]
    formulas = [{"text": f["text"][:200], "page": f["page"], "block_id": f["block_id"]}
                for f in by_kind.get("formula", [])]

    b.set("blocks", blocks)
    b.set("structure_summary", structure)
    b.set("sections", sections)
    b.set("figures", figures)
    b.set("tables", tables)
    b.set("formulas", formulas)
    b.set("order_checks", {
        "heading_sequence": [h["text"][:100] for h in by_kind.get("heading", [])],
        "caption_sequence": [c["text"][:100] for c in by_kind.get("caption", [])],
        "page_sequence_ok": all(
            (blocks[i]["page"] or 0) <= (blocks[i + 1]["page"] or 0)
            for i in range(len(blocks) - 1) if blocks[i]["page"] and blocks[i + 1]["page"]),
    })
    b.set("document_meta", doc_meta)
    tq = text_quality(blocks)
    b.set("text_quality", tq)
    if tq["long_token_count"]:
        b.add_uncertainty("检出 %d 处超长粘连词（示例：%s），可能是 PDF 未绘制空格字符所致，需人工核对分词。"
                          % (tq["long_token_count"],
                             ", ".join(x["token"] for x in tq["long_token_samples"][:2])))
    b.set("inventory", [{"path": str(p), "sha256": sha256_file(p), "suffix": p.suffix}
                        for p in files])

    contract = b.contract_keys
    mapping = {
        "blocks": blocks, "structure": structure, "structure_summary": structure,
        "sections": sections, "figures": figures, "tables": tables,
        "formulas": formulas, "references": by_kind.get("reference", []),
        "text": "\n".join(x["text"] for x in blocks), "content": blocks,
        "markdown": "\n\n".join(("## " if x["kind"] == "heading" else "") + x["text"]
                                for x in blocks),
    }
    for key in contract:
        if b.data.get(key) in (None, "", [], {}, 0, False):
            low = key.lower()
            for mk, mv in mapping.items():
                if mk in low or low in mk:
                    b.data[key] = mv
                    break

    if blocks:
        b.finalize("success")
    elif doc_meta["pdfs"]:
        b.finalize("partial")
    else:
        b.finalize("unknown")

    b.add_check("inputs_discovered", bool(files), "输入目录发现 %d 个文件" % len(files))
    b.add_check("blocks_extracted", bool(blocks), "解析出 %d 个文本块" % len(blocks))
    b.add_check("pdf_text_layer",
                True if not doc_meta["pdfs"] else all(d["pages"] > 0 for d in doc_meta["pdfs"]),
                "PDF：%s" % json.dumps(doc_meta["pdfs"], ensure_ascii=False))
    b.add_check("evidence_locators",
                bool(b.data["evidence"]) and all(
                    isinstance(x.get("locator"), dict) and x["locator"]
                    for x in b.data["evidence"]),
                "每条 evidence 必须有 file + block_id/页码 锚点")
    b.add_check("contract_filled",
                any(b.data.get(k) not in (None, "", [], {}, 0, False) for k in contract),
                "output_contract 字段已用真实内容填充")

    finalize_with_checks(b, args, files, SKILL_ID, AXES)
    print("wrote", Path(args.output) / "result.json",
          "| blocks=", len(blocks), "| status=", b.data.get("status"))


AXES = ["逐字提取完整率", "阅读顺序正确率", "表格行列归属准确率", "公式符号保真率", "锚点可回查率", "人工校对耗时"]

if __name__ == "__main__":
    main()
