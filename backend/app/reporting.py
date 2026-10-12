"""Actual-data PDFs and map images. No browser printing or external tile download."""

import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image as PillowImage, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    LongTable,
    TableStyle,
    Image,
    PageBreak,
)
from app.geo import india_extent

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets" / "fonts"
if (FONTS / "NotoSans-Regular.ttf").exists():
    pdfmetrics.registerFont(TTFont("DMS", str(FONTS / "NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("DMSDeva", str(FONTS / "NotoSansDevanagari-Regular.ttf")))
else:
    import reportlab

    pdfmetrics.registerFont(
        TTFont("DMS", str(Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"))
    )
STYLES = getSampleStyleSheet()
STYLES.add(
    ParagraphStyle(
        name="DMSBody",
        fontName="DMS",
        fontSize=8,
        leading=12,
        spaceAfter=5,
        splitLongWords=True,
        shaping=True,
    )
)
STYLES.add(
    ParagraphStyle(
        name="DMSTitle",
        fontName="DMS",
        fontSize=22,
        leading=28,
        textColor=colors.HexColor("#172d42"),
        spaceAfter=12,
    )
)
STYLES.add(
    ParagraphStyle(
        name="DMSHeading",
        fontName="DMS",
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#172d42"),
        spaceBefore=16,
        spaceAfter=8,
    )
)


def paragraph(value, style="DMSBody"):
    value = "-" if value is None else str(value)
    value = escape(value).replace("\n", "<br/>")
    if "DMSDeva" in pdfmetrics.getRegisteredFontNames():
        value = re.sub(
            r"[\u0900-\u097f]+", lambda m: '<font name="DMSDeva">' + m.group(0) + "</font>", value
        )
    return Paragraph(value, STYLES[style])


def india_map(rows):
    width, height = 1000, 850
    image = PillowImage.new("RGB", (width, height), "#f1f4f6")
    draw = ImageDraw.Draw(image)

    def point(lon, lat):
        return (60 + (float(lon) - 68) / 30 * 760, 35 + (38 - float(lat)) / 32 * 775)

    boundaries = json.loads(
        (ROOT.parent / "frontend/public/data/india-states.geojson").read_text(encoding="utf-8")
    )
    for feature in boundaries["features"]:
        geometry = feature["geometry"]
        polygons = (
            geometry["coordinates"]
            if geometry["type"] == "MultiPolygon"
            else [geometry["coordinates"]]
        )
        for rings in polygons:
            draw.polygon([point(*p[:2]) for p in rings[0]], fill="#dde6ec", outline="#8398a8")
            for ring in rings[1:]:
                draw.polygon([point(*p[:2]) for p in ring], fill="#f1f4f6")
    plotted, unlocated = 0, 0
    for row in rows:
        if not india_extent(row.get("latitude"), row.get("longitude")):
            unlocated += 1
            continue
        x, y = point(row["longitude"], row["latitude"])
        pending = row.get("kind") == "report"
        color = "#d87922" if pending else "#1e637f"
        if pending:
            draw.rectangle((x - 6, y - 6, x + 6, y + 6), fill=color, outline="white", width=2)
        else:
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="white", width=2)
        plotted += 1
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    return buffer, plotted, unlocated


def table(rows, columns):
    if not rows:
        return [paragraph("No matching records in this scope.")]
    # Wide schemas are split into column groups with the identifier repeated.
    blocks = []
    for offset in range(1, len(columns), 6):
        group = [columns[0]] + columns[offset : offset + 6]
        data = [[paragraph(c.replace("_", " ").title()) for c in group]]
        data += [[paragraph(row.get(c)) for c in group] for row in rows]
        column_width = (A4[0] - 80) / len(group)
        # Keep ordinary records together; split only cells taller than a whole page.
        oversized = any(
            cell.wrap(column_width - 12, 100000)[1] > 650 for row in data[1:] for cell in row
        )
        result = LongTable(
            data,
            colWidths=[column_width] * len(group),
            repeatRows=1,
            splitInRow=36 if oversized else 0,
        )
        result.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#d5dfe5")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        blocks += [result, Spacer(1, 10)]
    if len(columns) == 1:
        blocks += [paragraph("; ".join(str(r.get(columns[0], "")) for r in rows))]
    return blocks


def build_pdf(title, sections, scope="All matching records", map_rows=None, warnings=None):
    buffer = io.BytesIO()
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=45,
        title=title,
        author="Disaster Management System",
    )
    story = [
        paragraph("DISASTER MANAGEMENT SYSTEM / V3", "DMSBody"),
        paragraph(title, "DMSTitle"),
        paragraph("Generated UTC: " + generated),
        paragraph("Scope: " + scope),
    ]
    for warning in warnings or []:
        story.append(paragraph(warning))
    if map_rows is not None:
        picture, plotted, unlocated = india_map(map_rows)
        story += [
            paragraph("India incident map", "DMSHeading"),
            Image(picture, width=480, height=408),
            paragraph(
                f"Legend: blue circle = official disaster; orange square = unverified/rejected emergency report. Plotted {plotted}; missing/invalid/outside map coordinates {unlocated}."
            ),
            paragraph(
                "Boundaries: geoBoundaries IND ADM1 / DataMeet / ECI, CC BY 2.5 India. Source metadata and attribution are included in frontend/public/data/india-boundaries-source.json. Geographic boundaries are contextual, not navigational guidance."
            ),
        ]
    for heading, rows, columns in sections:
        story.append(paragraph(heading, "DMSHeading"))
        story.extend(table(rows, columns))

    def footer(canvas, document):
        canvas.setFont("DMS", 8)
        canvas.setFillColor(colors.HexColor("#5c6e7c"))
        canvas.drawString(
            40,
            25,
            "DMS / "
            + generated[:10]
            + " / "
            + ("Hypothetical planning" if "Simulation" in title else "Operational report"),
        )
        canvas.drawRightString(A4[0] - 40, 25, f"Page {document.page}")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
