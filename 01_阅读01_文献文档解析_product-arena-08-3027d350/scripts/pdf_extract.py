#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure-stdlib PDF text extraction with page numbers and rough coordinates.

Strategy:
1. If pypdf is importable, use it (best quality).
2. Otherwise parse the PDF directly: locate page objects, resolve their
   content streams, inflate FlateDecode, and read text-showing operators.

Returns per-page items with x/y so the caller can restore reading order.
No third-party dependency is required for the fallback path.
"""
from __future__ import annotations

import re
import zlib
from pathlib import Path

OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")
PAGE_RE = re.compile(rb"/Type\s*/Page\b")
PAGES_RE = re.compile(rb"/Type\s*/Pages\b")
CONTENTS_RE = re.compile(rb"/Contents\s*(\[(.*?)\]|(\d+)\s+\d+\s+R)", re.S)
STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
FLATE_RE = re.compile(rb"/FlateDecode")
OBJSTM_RE = re.compile(rb"/Type\s*/ObjStm")
N_RE = re.compile(rb"/N\s+(\d+)")
FIRST_RE = re.compile(rb"/First\s+(\d+)")

# text-showing operators
TJ_RE = re.compile(rb"\[(.*?)\]\s*TJ", re.S)
TJ_STR_RE = re.compile(rb"\((?:\\.|[^\\()])*\)")
TJ_NUM_RE = re.compile(rb"(-?\d+(?:\.\d+)?)")
TJ_STR_SINGLE = re.compile(rb"\((?:\\.|[^\\()])*\)\s*Tj", re.S)
POS_TM_RE = re.compile(rb"([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+Tm")
POS_TD_RE = re.compile(rb"([-\d.]+)\s+([-\d.]+)\s+(?:Td|TD)")


def _decode_pdf_string(raw: bytes) -> str:
    """Decode a PDF literal string body (without the surrounding parentheses)."""
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == 0x5C and i + 1 < n:  # backslash
            nxt = raw[i + 1]
            simple = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12,
                      0x28: 0x28, 0x29: 0x29, 0x5C: 0x5C}
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            if 0x30 <= nxt <= 0x37:  # octal
                oct_digits = raw[i + 1:i + 4]
                m = re.match(rb"[0-7]{1,3}", oct_digits)
                if m:
                    out.append(int(m.group(0), 8) & 0xFF)
                    i += 1 + len(m.group(0))
                    continue
            i += 2
            continue
        out.append(c)
        i += 1
    # PDF strings are often Latin-1/PDFDocEncoding; try UTF-8 then latin-1.
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return out.decode("latin-1", "replace")


def _unpack_stream(dict_bytes: bytes, stream: bytes) -> bytes:
    if FLATE_RE.search(dict_bytes) or stream[:2] == b"x\x9c":
        try:
            return zlib.decompress(stream)
        except zlib.error:
            try:
                return zlib.decompressobj().decompress(stream)
            except zlib.error:
                return b""
    return stream


def _extract_items_from_content(content: bytes):
    """Walk operators in order; emit one (x, y, text) per text-showing op."""
    items = []
    cur_x = cur_y = 0.0
    lead = 0.0

    # One regex that matches every operator we care about, in document order.
    op_re = re.compile(
        rb"([-\d.]+)\s+([-\d.]+)\s+(?:Td|TD)"
        rb"|([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+Tm"
        rb"|(?:\[(.*?)\]\s*TJ)"
        rb"|(\((?:\\.|[^\\()])*\)\s*Tj)"
        rb"|(T\*)",
        re.S)

    for m in op_re.finditer(content):
        if m.group(1) is not None:           # Td / TD
            try:
                cur_x += float(m.group(1))
                cur_y += float(m.group(2))
            except ValueError:
                pass
        elif m.group(3) is not None:         # Tm
            try:
                cur_x = float(m.group(7))
                cur_y = float(m.group(8))
            except ValueError:
                pass
        elif m.group(9) is not None:         # TJ array
            arr = m.group(9)
            parts, gaps = [], []
            for tok in TJ_STR_RE.finditer(arr):
                parts.append(_decode_pdf_string(tok.group(0)[1:-1]))
            nums = [float(x) for x in TJ_NUM_RE.findall(arr)]
            if parts:
                text = "".join(parts)
                if nums and any(v < -60 for v in nums):
                    text = " " + text
                items.append((cur_x, cur_y, text))
                # Advance x roughly by text length; exact metrics are unavailable.
                cur_x += len(text) * 4.5
        elif m.group(10) is not None:        # Tj
            body = m.group(10)
            sm = re.match(rb"\((.*)\)\s*Tj", body, re.S)
            if sm:
                text = _decode_pdf_string(sm.group(1))
                if text.strip():
                    items.append((cur_x, cur_y, text))
                    cur_x += len(text) * 4.5
        elif m.group(11) is not None:        # T*
            cur_x = 0.0
            cur_y -= 12.0

    return items


def _collect_objects(data: bytes):
    """Collect direct objects, then unpack ObjStm containers into the same map."""
    objs = {}
    for m in OBJ_RE.finditer(data):
        num = int(m.group(1))
        start = m.end()
        end = data.find(b"endobj", start)
        if end < 0:
            continue
        objs[num] = data[start:end]

    # Expand object streams: /Type /ObjStm holds N compressed objects.
    for num, body in list(objs.items()):
        if not OBJSTM_RE.search(body[:600]):
            continue
        sm = STREAM_RE.search(body)
        if not sm:
            continue
        raw = _unpack_stream(body[:sm.start()], sm.group(1))
        n_m = N_RE.search(body[:sm.start()])
        f_m = FIRST_RE.search(body[:sm.start()])
        if not (n_m and f_m):
            continue
        try:
            count = int(n_m.group(1))
            first = int(f_m.group(1))
        except ValueError:
            continue
        header = raw[:first]
        pairs = re.findall(rb"(\d+)\s+(\d+)", header)
        for i, (onum, off) in enumerate(pairs[:count]):
            try:
                obj_num = int(onum)
                start = first + int(off)
                end = first + int(pairs[i + 1][1]) if i + 1 < len(pairs) else len(raw)
            except (ValueError, IndexError):
                continue
            if obj_num not in objs:
                objs[obj_num] = raw[start:end]
    return objs


def _surface_pages(objs):
    """Order page objects by walking /Type /Pages kids when possible."""
    pages = []
    kids_refs = []
    for body in objs.values():
        if PAGES_RE.search(body[:400]):
            km = re.search(rb"/Kids\s*\[(.*?)\]", body, re.S)
            if km:
                kids_refs.extend(int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", km.group(1)))
    if kids_refs:
        for ref in kids_refs:
            body = objs.get(ref, b"")
            if PAGE_RE.search(body[:400]):
                pages.append(body)
    if not pages:
        for num in sorted(objs):
            body = objs[num]
            if PAGE_RE.search(body[:400]):
                pages.append(body)
    return pages


def _pages_via_objects(data: bytes):
    """Resolve page objects (including those inside ObjStm) and read their content streams."""
    objs = _collect_objects(data)
    pages = []
    for body in _surface_pages(objs):
        m = CONTENTS_RE.search(body)
        if not m:
            continue
        refs = []
        if m.group(3):
            refs.append(int(m.group(3)))
        else:
            refs.extend(int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", m.group(2) or b""))
        page_items = []
        for ref in refs:
            cbody = objs.get(ref, b"")
            sm = STREAM_RE.search(cbody)
            if not sm:
                continue
            raw = _unpack_stream(cbody[:sm.start()], sm.group(1))
            page_items.extend(_extract_items_from_content(raw))
        if page_items:
            pages.append(page_items)
    return pages


def _pages_via_pypdf(path: Path):
    try:
        import pypdf  # type: ignore
    except Exception:
        return None
    try:
        reader = pypdf.PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            # Space y by a full line height so downstream line grouping keeps
            # distinct lines apart (a 1.0 step is inside any sane tolerance).
            items = [(0.0, -float(i) * 20.0, line)
                     for i, line in enumerate(text.splitlines()) if line.strip()]
            if items:
                pages.append(items)
        return pages
    except Exception:
        return None


def _pages_via_pdftotext(path: Path):
    """Use poppler's pdftotext when present (usually the highest fidelity)."""
    import shutil
    import subprocess
    import tempfile

    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            out = tmp.name
        subprocess.run([exe, "-layout", "-enc", "UTF-8", str(path), out],
                       capture_output=True, timeout=120)
        text = Path(out).read_text(encoding="utf-8", errors="replace")
        Path(out).unlink(missing_ok=True)
        pages = []
        for i, page in enumerate(text.split("\f")):
            items = [(0.0, -float(j) * 20.0, line)
                     for j, line in enumerate(page.splitlines()) if line.strip()]
            if items:
                pages.append(items)
        return pages or None
    except Exception:
        return None


def extract_pdf(path):
    """Return (pages, meta). pages is [ [(x, y, text), ...], ... ] per page."""
    p = Path(path)
    data = p.read_bytes()
    meta = {"backend": "", "encrypted": b"/Encrypt" in data[:20000], "page_count": 0}
    if meta["encrypted"]:
        meta["backend"] = "none"
        return [], meta

    pages = _pages_via_pypdf(p)
    meta["backend"] = "pypdf"
    if not pages:
        pages = _pages_via_pdftotext(p)
        meta["backend"] = "pdftotext"
    if not pages:
        pages = _pages_via_objects(data)
        meta["backend"] = "stdlib"
    meta["page_count"] = len(pages)
    return pages, meta

def extract_layout_lines(path):
    """Per-page lines from pypdf layout mode, preserving column spacing for tables."""
    try:
        import pypdf  # type: ignore
    except Exception:
        return []
    try:
        reader = pypdf.PdfReader(str(path))
        pages = []
        for page in reader.pages:
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                text = page.extract_text() or ""
            pages.append([ln.rstrip() for ln in text.splitlines()])
        return pages
    except Exception:
        return []
