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
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=42,
        title="Overview briefing",
        author="Disaster Management System",
    )
    ordered = sorted(items, key=urgency)
    shortage_rows = sorted(
        [dict(r) for r in shortages if Decimal(str(r.get("shortage", 0))) > 0],
        key=lambda r: str(r.get("resource_name", "")),
    )
    shelter_rows = sorted(
        [
            {
                **r,
                "spare": max(0, int(r.get("capacity") or 0) - int(r.get("current_occupancy") or 0)),
            }
            for r in shelters
        ],
        key=lambda r: (
            -float(r.get("current_occupancy") or 0) / max(1, float(r.get("capacity") or 0)),
            str(r.get("name", "")),
        ),
    )
    official = sum(r.get("kind") == "disaster" for r in items)
    pending = sum(r.get("review_status") == "PENDING_REVIEW" for r in items)
    story = [
        paragraph("DISASTER MANAGEMENT SYSTEM / V3.1", "DMSBody"),
        paragraph("Operational overview", "DMSTitle"),
        paragraph("Generated UTC: " + generated),
        paragraph("Selected incident scope: " + scope),
    ]
    cards = [
        [
            paragraph("OFFICIAL INCIDENTS\n" + str(official)),
            paragraph("PENDING REPORTS\n" + str(pending)),
            paragraph(
                "HIGH / CRITICAL\n"
                + str(sum(r.get("severity") in {"HIGH", "CRITICAL"} for r in items))
            ),
            paragraph(
                "UNLOCATED\n"
                + str(
                    sum(
                        not r.get(
                            "plottable",
                            r.get("latitude") is not None and r.get("longitude") is not None,
                        )
                        for r in items
                    )
                )
            ),
        ]
    ]
    panel = Table(cards, colWidths=[128] * 4)
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1dce4")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.extend(
        [
            Spacer(1, 12),
            panel,
            paragraph("Incident severity in selected scope", "DMSHeading"),
            severity_chart(items),
            paragraph(
                f"{official} official incident records and {pending} pending reports in this scope. Confirmed reports linked to an official disaster are not counted twice."
            ),
        ]
    )
    s = stats.get("shelters", {})
    r = stats.get("resources", {})
    v = stats.get("volunteers", {})
    story.extend(
        [
            paragraph("Countrywide operational situation", "DMSHeading"),
            paragraph(
                f"Shelters: {s.get('total', 0)} recorded; {s.get('available', 0)} eligible with spare capacity. Occupancy {s.get('total_occupancy', 0)} / {s.get('total_capacity', 0)} recorded places. Resources: {r.get('available_types', 0)} types with stock, {r.get('low_stock_count', 0)} at/below minimum. Volunteers: {v.get('available', 0)} available of {v.get('total', 0)} registered."
            ),
            paragraph(
                f"{len(shortage_rows)} resource IDs have global OPEN demand exceeding available stock. Quantities are compared within each resource and unit; reserved stock and delivered stock remain distinct."
            ),
            paragraph(
                "Scope note: incident KPIs/chart/map follow selected filters. Inventory, shortage and shelter summaries are countrywide. This briefing highlights priority records; filtered page exports and Overview CSV contain the underlying detailed records."
            ),
        ]
    )
    story.extend([PageBreak(), paragraph("Geographic & operational summary", "DMSTitle")])
    picture, plotted, unlocated = india_map(items)
    notes = paragraph(
        f"Map legend\nBlue circle: official disaster\nOrange square: unverified/rejected report\n\nPlotted: {plotted}\nMissing/invalid/outside-map coordinates: {unlocated}\n\ngeoBoundaries / DataMeet / ECI\nCC BY 2.5 India. Boundaries are contextual."
    )
    map_panel = Table([[Image(picture, width=250, height=212.5), notes]], colWidths=[288, 227])
    map_panel.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(map_panel)
    incident_columns = ["id", "title", "state", "severity", "response_status"]
    for heading, rows, columns in [
        ("Priority incidents / reports (up to 4)", ordered[:4], incident_columns),
        (
            "Resource shortage highlights (up to 3; original units)",
            shortage_rows[:3],
            ["resource_name", "unit", "outstanding", "available", "shortage"],
        ),
        (
            "Shelter occupancy highlights (up to 3)",
            shelter_rows[:3],
            ["name", "state", "current_occupancy", "capacity", "spare"],
        ),
    ]:
        story.append(paragraph(heading, "DMSHeading"))
        story.extend(table(rows, columns))
    if len(ordered) > 4 or len(shortage_rows) > 3 or len(shelter_rows) > 3:
        story.extend([PageBreak(), paragraph("Additional highlights & review notes", "DMSTitle")])
        for heading, rows, columns in [
            ("Further priority incidents / reports (next 14)", ordered[4:18], incident_columns),
            (
                "Further resource shortages (next 6)",
                shortage_rows[3:9],
                ["resource_name", "unit", "outstanding", "available", "shortage"],
            ),
        ]:
            story.append(paragraph(heading, "DMSHeading"))
            story.extend(table(rows, columns))
        story.append(
            paragraph(
                f"Summary scope: {len(items)} incidents/reports, {len(shortage_rows)} shortage resources and {len(shelters)} shelters. Tables are explicitly selected highlights, not an exhaustive inventory. Use page-specific PDFs or CSV for all matching records. Shelter priority is recorded occupancy ratio; resource quantities are never ranked across incompatible units."
            )
        )
    story.append(
        paragraph(
            "Method: severity-based review order; counts represent records, not affected population. Missing coordinates remain counted. Availability reflects existing allocation rules; a recommendation requires a fresh authorized stock review."
        )
    )
    footer = report_footer(generated, "Overview briefing")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
