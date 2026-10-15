from io import BytesIO
from decimal import Decimal
from unittest.mock import patch
from pypdf import PdfReader
from app.briefing import overview_pdf, severity_chart
from app.routes import planning
from app.routes.emergency_reports import public_report
from app.main import app
from app.security import current_user
from conftest import PUBLIC, ADMIN


def fixtures(count=8):
    items = [
        dict(
            kind="disaster",
            id=i + 1,
            title=f"Fixture incident {i + 1}",
            state="Assam",
            severity="HIGH",
            response_status="ACTIVE",
            latitude=26.14,
            longitude=91.73,
            plottable=True,
        )
        for i in range(count)
    ]
    shelters = [dict(name="Fixture shelter", state="Assam", capacity=100, current_occupancy=80)]
    shortages = [
        dict(
            resource_name="Fixture water", unit="litres", outstanding=120, available=50, shortage=70
        )
    ]
    return items, shelters, shortages


def test_briefing_typical_empty_and_larger_scopes_preserve_all_records():
    for count in [0, 4, 8, 80]:
        items, shelters, shortages = fixtures(count)
        pdf = overview_pdf(items, {}, shelters, shortages, "ISOLATED FIXTURE; not live records")
        reader = PdfReader(BytesIO(pdf))
        assert len(reader.pages) >= 2
        text = " ".join(page.extract_text() for page in reader.pages)
        assert "Generated UTC:" in text and "Map legend" in text
        assert "ISOLATED FIXTURE" in text
        assert all(
            "Page " + str(i + 1) in page.extract_text() for i, page in enumerate(reader.pages)
        )
        # V4 intentionally exports every matching record, including larger scopes.
        for item in items:
            assert item["title"] in text
        assert any(page.images for page in reader.pages)


def test_real_chart_counts_not_example_values():
    items, _, _ = fixtures(4)
    drawing = severity_chart(items)
    texts = [getattr(shape, "text", None) for shape in drawing.contents]
    assert "4" in texts and "High" in texts


def test_public_tracking_allowlist_keeps_published_reason_hides_internal_fields():
    result = public_report(
        dict(
            report_id=2,
            review_status="REJECTED",
            status="REJECTED",
            review_reason="Published decision reason",
            reviewed_by=123,
            reported_by_name="Private actor",
            internal_note="SECRET",
            password_hash="SECRET",
        )
    )
    assert result["report_id"] == 2 and result["review_reason"] == "Published decision reason"
    assert not {"internal_note", "password_hash", "reported_by_name", "reviewed_by"} & result.keys()


def test_public_cannot_access_other_reports_or_privileged_tools(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert client.get("/api/emergency-reports/999").status_code == 404
    assert db.execute.call_args.args[1]["owner"] == PUBLIC["user_id"]
    for path in [
        "/api/resource-intelligence",
        "/api/simulations/catalog",
        "/api/audit-history/",
        "/api/resource-movements/",
    ]:
        assert client.get(path).status_code == 403


def test_priority_filters_and_recommendation_respect_shared_stock(db):
    rows = []
    for id, severity, status, allocated in [
        (1, "HIGH", "OPEN", 2),
        (2, "CRITICAL", "CANCELLED", 0),
        (3, "LOW", "OPEN", 0),
    ]:
        rows.append(
            dict(
                request_id=id,
                disaster_id=id,
                resource_id=1,
                status=status,
                disaster_status="ACTIVE",
                severity=severity,
                quantity=Decimal(10),
                allocated_quantity=Decimal(allocated),
                delivered_quantity=Decimal(0),
                outstanding_quantity=Decimal(10 - allocated),
                available_quantity=Decimal(3),
                resource_name="Water",
                unit="litres",
            )
        )
    db.execute.return_value.mappings.return_value.all.return_value = rows
    result = planning.intelligence(db, ADMIN, "", "", "", "", None, None, 25, 0, "URGENT", "OPEN")
    assert [r["request_id"] for r in result["items"]] == [1]
    assert result["metrics"]["high_priority_unresolved"] == 1
    assert result["items"][0]["recommended_quantity"] == 3
    assert result["resource_totals"][0]["shortage"] == 15
    db.commit.assert_not_called()
