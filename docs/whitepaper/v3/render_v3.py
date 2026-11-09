"""Render the v3 Chinese whitepaper (adapted from docs/whitepaper/render_whitepaper.py, 2.0).

Requires reportlab; CODEX_PDF_PACKAGES may point to bundled Python site-packages.
This is a document renderer, not a project build or a benchmark runner.
"""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
import sys

if os.environ.get("CODEX_PDF_PACKAGES"):
    sys.path.insert(0, os.environ["CODEX_PDF_PACKAGES"])

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
COMMIT = "0c53fae1811b1731e43a0386bd4f42106fe422e7"
INK = colors.HexColor("#172a3a")
TEAL = colors.HexColor("#007c89")


def register_fonts(font_dir: Path) -> None:
    pdfmetrics.registerFont(TTFont("CN", str(font_dir / "simsun.ttc"), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("CNBold", str(font_dir / "simhei.ttf")))
    pdfmetrics.registerFontFamily("CN", normal="CN", bold="CNBold", italic="CN", boldItalic="CNBold")
    for name, filename in [("CoverCN", "msyh.ttc"), ("CoverCNBold", "msyhbd.ttc"),
                           ("CoverSans", "segoeui.ttf"), ("CoverSansBold", "segoeuib.ttf"),
                           ("CoverMono", "consola.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / filename), subfontIndex=0))


def inline(raw: str) -> str:
    raw = raw.replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
    raw = html.escape(raw)
    # Links are resolved before emphasis; escaped underscores in URLs stay literal.
    def link(m):
        label, url = m.group(1), html.unescape(m.group(2))
        if url.startswith("#"):
            return label
        if not re.match(r"https?://", url):
            target = (BASE / url.split("#")[0]).resolve()
            if target.is_relative_to(BASE):
                # Newly authored research is delivered alongside this PDF; it is
                # not present at the historical code commit used for source links.
                return label
            fragment = "#" + url.split("#", 1)[1] if "#" in url else ""
            url = f"https://github.com/AAswordman/Operit2/blob/{COMMIT}/{target.relative_to(ROOT).as_posix()}{fragment}"
        return f'<link href="{html.escape(url, quote=True)}" color="#007c89">{label}</link>'
    raw = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, raw)
    raw = re.sub(r"`([^`]+)`", r'<font color="#22546a">\1</font>', raw)
    raw = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", raw)
    return raw


class SvgFigure(Flowable):
    """The authored SVG subset drawn as vectors in PDF, without rasterization."""
    def __init__(self, path: Path, width: float):
        super().__init__()
        import xml.etree.ElementTree as ET
        self.root = ET.parse(path).getroot()
        _, _, self.vw, self.vh = map(float, self.root.attrib["viewBox"].split())
        self.width = width
        self.height = width * self.vh / self.vw

    def draw(self):
        c = self.canv
        c.saveState()
        c.scale(self.width / self.vw, self.width / self.vw)
        for el in self.root.iter():
            tag = el.tag.rsplit("}", 1)[-1]
            a = el.attrib
            if tag not in {"rect", "line", "polyline", "polygon", "circle", "text"}:
                continue
            fill, stroke = a.get("fill", "none"), a.get("stroke", "none")
            if fill != "none":
                c.setFillColor(colors.HexColor(fill))
            if stroke != "none":
                c.setStrokeColor(colors.HexColor(stroke))
            c.setLineWidth(float(a.get("stroke-width", 1)))
            dash = a.get("stroke-dasharray")
            c.setDash(list(map(float, dash.split(","))) if dash else [])
            if tag == "rect":
                x, y, w, h = (float(a.get(k, 0)) for k in ("x", "y", "width", "height"))
                c.roundRect(x, self.vh - y - h, w, h, float(a.get("rx", 0)), stroke=int(stroke != "none"), fill=int(fill != "none"))
            elif tag == "circle":
                c.circle(float(a["cx"]), self.vh-float(a["cy"]), float(a["r"]), stroke=int(stroke != "none"), fill=int(fill != "none"))
            elif tag in {"polyline", "polygon"}:
                pts = [tuple(map(float, p.split(","))) for p in a["points"].split()]
                p = c.beginPath()
                p.moveTo(pts[0][0], self.vh-pts[0][1])
                for x, y in pts[1:]:
                    p.lineTo(x, self.vh-y)
                if tag == "polygon":
                    p.close()
                c.drawPath(p, stroke=int(stroke != "none"), fill=int(fill != "none"))
            elif tag == "line":
                c.line(float(a["x1"]), self.vh-float(a["y1"]), float(a["x2"]), self.vh-float(a["y2"]))
            elif tag == "text":
                name = a.get("data-pdf-font", "CN")
                if a.get("font-weight") == "700":
                    name += "Bold"
                c.setFont(name, float(a.get("font-size", 18)))
                x, y = float(a["x"]), self.vh-float(a["y"])
                draw = {"middle": c.drawCentredString, "end": c.drawRightString}.get(a.get("text-anchor"), c.drawString)
                draw(x, y, "".join(el.itertext()))
        c.restoreState()


class WhitepaperDoc(BaseDocTemplate):
    def __init__(self, output: Path):
        super().__init__(str(output), pagesize=(210*mm, 297*mm), leftMargin=20*mm,
                         rightMargin=20*mm, topMargin=21*mm, bottomMargin=20*mm,
                         title="Operit2 技术白皮书 3.0：个人设备空间中 Agent 的回合边界续跑与执行所有权",
                         author="Operit 项目", subject=f"代码基线 {COMMIT}；2026-11-10")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self.decorate))

    def beforeDocument(self):
        self.heading_count = 0

    def decorate(self, c, doc):
        if doc.page == 1:
            SvgFigure(BASE / "cover.svg", 210*mm).drawOn(c, 0, 0)
            return
        c.saveState()
        c.setStrokeColor(colors.HexColor("#d7e4e7"))
        c.line(20*mm, 283*mm, 190*mm, 283*mm)
        c.setFont("CN", 8)
        c.setFillColor(colors.HexColor("#607781"))
        c.drawString(20*mm, 286*mm, "OPERIT2  /  技术白皮书  /  中文版 3.0")
        c.drawRightString(190*mm, 12*mm, f"{doc.page:02d}")
        c.drawString(20*mm, 12*mm, "2026-11-10  ·  源码基线 0c53fae  ·  预览阶段")
        c.restoreState()

    def afterFlowable(self, flow):
        if isinstance(flow, Paragraph) and flow.style.name in {"H1", "H2"}:
            level = 0 if flow.style.name == "H1" else 1
            text = flow.getPlainText()
            self.heading_count += 1
            key = f"section-{self.heading_count}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
            if text not in {"摘要", "Abstract", "文档范围与阅读方式", "目录"}:
                self.notify("TOCEntry", (level, text, self.page, key))


def render(source: Path, output: Path, font_dir: Path):
    register_fonts(font_dir)
    body = ParagraphStyle("Body", fontName="CN", fontSize=10.2, leading=17,
                          textColor=INK, wordWrap="CJK", spaceAfter=7.5,
                          allowWidows=0, allowOrphans=0, splitLongWords=1)
    styles = {
        "Body": body,
        "H1": ParagraphStyle("H1", parent=body, fontName="CNBold", fontSize=17, leading=25, spaceBefore=18, spaceAfter=13, keepWithNext=True),
        "H2": ParagraphStyle("H2", parent=body, fontName="CNBold", fontSize=12.6, leading=20, spaceBefore=13, spaceAfter=8, keepWithNext=True),
        "H3": ParagraphStyle("H3", parent=body, fontName="CNBold", fontSize=10.6, leading=18, spaceBefore=10, spaceAfter=5, keepWithNext=True),
        "Small": ParagraphStyle("Small", parent=body, fontSize=8.2, leading=12.8, spaceAfter=5),
        "Cell": ParagraphStyle("Cell", parent=body, fontSize=8.1, leading=12.4, spaceAfter=0),
        "Caption": ParagraphStyle("Caption", parent=body, fontSize=8.7, leading=14, textColor=colors.HexColor("#4a626c"), spaceBefore=5, spaceAfter=13),
        "Quote": ParagraphStyle("Quote", parent=body, leftIndent=10, borderColor=TEAL, borderWidth=1, borderPadding=8, backColor=colors.HexColor("#eff6f6"), spaceBefore=6, spaceAfter=12),
    }
    story = [Spacer(1, 1), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc0", parent=body, fontName="CNBold", fontSize=10.5, leading=17, spaceBefore=4), ParagraphStyle("toc1", parent=body, fontSize=9, leading=13, leftIndent=12)]
    lines = source.read_text(encoding="utf-8").splitlines()
    i = 0
    def p(text, style="Body"):
        return Paragraph(inline(text), styles[style])
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("# ") or line.startswith("<!-- metadata"):
            i += 1
            continue
        if line == "<!-- toc -->":
            story += [PageBreak(), Paragraph("目录", styles["H1"]), toc, PageBreak()]
            i += 1
            continue
        if line == "<!-- pagebreak -->":
            story.append(PageBreak()); i += 1; continue
        if line.startswith("!["):
            m = re.match(r"!\[([^\]]+)\]\(([^)]+)\)", line)
            if not m:
                raise ValueError(f"Invalid figure: {line}")
            fig = SvgFigure(BASE / m.group(2), 170*mm)
            story.append(KeepTogether([Spacer(1, 5), fig, p(m.group(1), "Caption")]))
            i += 1; continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in row):
                    rows.append(row)
                i += 1
            n = len(rows[0])
            if any(len(r) != n for r in rows):
                raise ValueError("Unequal table columns")
            weights = {2:[0.30,0.70],3:[0.22,0.39,0.39],4:[0.15,0.27,0.31,0.27],5:[0.16,0.21,0.21,0.21,0.21]}.get(n, [1/n]*n)
            table = Table([[p(c, "Cell") for c in r] for r in rows], colWidths=[170*mm*w for w in weights], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0),colors.HexColor("#e3f0f0")),
                ("ROWBACKGROUNDS", (0,1),(-1,-1),[colors.white,colors.HexColor("#f6f8f9")]),
                ("VALIGN", (0,0),(-1,-1),"TOP"), ("LEFTPADDING", (0,0),(-1,-1),7), ("RIGHTPADDING", (0,0),(-1,-1),7),
                ("TOPPADDING", (0,0),(-1,-1),7), ("BOTTOMPADDING", (0,0),(-1,-1),7),
                ("LINEBELOW", (0,0),(-1,0),0.7,TEAL), ("LINEBELOW", (0,1),(-1,-1),0.25,colors.HexColor("#dfe7e9"))]))
            story += [table, Spacer(1, 10)]; continue
        if line.startswith("```"):
            code=[]; i+=1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i+=1
            story += [p("<br/>".join(code).replace(" ", "&#160;"), "Small")]
            i += 1; continue
        m=re.match(r"(#{2,4}) (.*)", line)
        if m:
            story.append(p(m.group(2), f"H{len(m.group(1))-1}")); i+=1; continue
        if line.startswith("> "):
            story.append(p(line[2:], "Quote")); i+=1; continue
        if line.startswith("- "):
            story.append(p("• " + line[2:])); i+=1; continue
        para=[line]; i+=1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||!\[|<!--|>|- |```)",lines[i].strip()):
            para.append(lines[i].strip()); i+=1
        story.append(p(" ".join(para)))
    output.parent.mkdir(parents=True, exist_ok=True)
    WhitepaperDoc(output).multiBuild(story)
    print(output)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=BASE / "Operit2-Whitepaper-zh-v3.md")
    ap.add_argument("--output", type=Path, default=ROOT / "docs" / "Operit2技术白皮书-3.0.pdf")
    ap.add_argument("--font-dir", type=Path, default=Path("C:/Windows/Fonts"))
    args = ap.parse_args()
    render(args.source, args.output, args.font_dir)
