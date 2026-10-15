"""Executive briefing from actual selected records; detailed exports stay separate."""

from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from decimal import Decimal
from reportlab.platypus import SimpleDocTemplate, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Rect, String
from app.reporting import paragraph, table, india_map, report_footer

RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def urgency(row):
    return (
        -RANK.get(row.get("severity"), 0),
        row.get("response_status") == "RESOLVED",
        str(row.get("id", "")),
    )


def severity_chart(items):
    counts = Counter(row.get("severity") or "UNKNOWN" for row in items)
    keys = [k for k in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"] if counts[k]]
    if not keys:
        return paragraph("No matching incidents: no severity chart available.")
    chart = Drawing(510, 25 * len(keys) + 15)
    maximum = max(counts.values())
    for index, key in enumerate(keys):
        y = 25 * (len(keys) - index - 1) + 10
        chart.add(
            String(
                0,
                y + 3,
                key.title(),
                fontName="DMS",
                fontSize=9,
                fillColor=colors.HexColor("#172d42"),
            )
        )
        chart.add(
            Rect(
                82,
                y,
                360 * counts[key] / maximum,
                14,
                fillColor=colors.HexColor("#cc773b")
                if key in {"HIGH", "CRITICAL"}
                else colors.HexColor("#41667f"),
                strokeColor=None,
            )
        )
        chart.add(String(450, y + 3, str(counts[key]), fontName="DMS", fontSize=9))
    return chart


def overview_pdf(items, stats, shelters, shortages, scope):
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40,
        topMargin=40, bottomMargin=42, title="Overview briefing", author="Disaster Management System")
    official = [r for r in items if r.get("kind") == "disaster"]
    available = sum(max(0, int(s["capacity"])-int(s["current_occupancy"])) for s in shelters if s.get("status")=="AVAILABLE")
    metrics = [
        {"metric":"Active disasters in scope", "value":sum(r.get("response_status")=="ACTIVE" for r in official)},
        {"metric":"Critical disasters in scope", "value":sum(r.get("severity")=="CRITICAL" for r in official)},
        {"metric":"Pending reports in scope", "value":sum(r.get("review_status")=="PENDING_REVIEW" for r in items)},
        {"metric":"Available shelter places (global)", "value":available},
        {"metric":"Resource shortage types (global)", "value":sum(Decimal(str(r.get("shortage",0)))>0 for r in shortages)},
    ]
    story=[paragraph("DISASTER MANAGEMENT SYSTEM / V4", "DMSBody"), paragraph("Operational overview", "DMSTitle"),
        paragraph("Generated UTC: "+generated), paragraph("Selected incident scope: "+scope)]
    story.extend(table(metrics,["metric","value"]))
    try:
        picture,plotted,unlocated=india_map(items)
        story += [paragraph("India incident map", "DMSHeading"),Image(picture,width=455,height=386.75),
            paragraph(f"Map legend: blue circles = official disasters; orange squares = unverified reports. Plotted {plotted}; location unavailable/outside map extent {unlocated}. All matching records remain in the following table."),
            paragraph("Boundaries: geoBoundaries / DataMeet / ECI, CC BY 2.5 India. Contextual boundaries, not navigation guidance. The map uses stored coordinates; no missing coordinates are inferred.")]
    except (OSError,ValueError):
        story.append(paragraph("Map image unavailable: bundled boundary data could not be read. All matching incident records and the selected filter scope are included below; no coordinates or map image have been fabricated."))
    story += [PageBreak(), paragraph("Incidents in selected scope", "DMSTitle")]
    rows=[{**r,"location":", ".join(str(r.get(k) or "") for k in ["city","state"]).strip(", ") or "Location unavailable"} for r in sorted(items,key=urgency)]
    story.extend(table(rows,["kind","id","title","disaster_type","location","severity","response_status"]))
    story.append(paragraph("Incident KPIs, map and table follow the same filters and include resolved records by default. Inventory and shelter metrics are countrywide. Shortage quantities are compared only within the same resource/unit; allocations do not prove delivery."))
    footer=report_footer(generated,"Overview briefing")
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
