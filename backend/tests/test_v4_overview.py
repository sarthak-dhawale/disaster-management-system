from datetime import datetime
from io import BytesIO
from unittest.mock import patch, MagicMock
from pypdf import PdfReader
from app.main import app
from app.security import current_user
from app.routes import operations, intelligence
from app.briefing import overview_pdf
from conftest import ADMIN, PUBLIC


def test_v4_map_layers_restricted_to_response_roles(client):
    for role in ['PUBLIC_USER', 'VOLUNTEER']:
        app.dependency_overrides[current_user] = lambda: {**PUBLIC, 'role': role}
        for path in ['/api/operations/metrics', '/api/operations/map-layers']:
            assert client.get(path).status_code == 403


def test_v4_map_includes_resolved_when_requested_and_preserves_missing_coordinates(db):
    db.execute.return_value.scalar_one.return_value = 2
    db.execute.return_value.mappings.return_value.all.return_value = [
        dict(kind='disaster', id=1, title='Resolved', severity='LOW', response_status='RESOLVED', latitude=26.14, longitude=91.73),
        dict(kind='disaster', id=2, title='Unlocated', severity='HIGH', response_status='ACTIVE', latitude=None, longitude=None),
    ]
    result = intelligence.incidents(db, ADMIN, '', '', '', '', '', None, None, True, False, 500, 0)
    assert [r['plottable'] for r in result['items']] == [True, False]
    assert "response_status!='RESOLVED'" not in str(db.execute.call_args.args[0])
    assert result['total'] == 2


def test_v4_metrics_have_real_scope_and_no_mixed_quantity_sum(db):
    db.execute.return_value.scalar_one.side_effect = [3, 70]
    with patch.object(operations, 'get_dashboard', return_value={'disasters': {'active': 2, 'critical': 1}, 'emergency_reports': {'pending': 4}}):
        result = operations.metrics(db)
    assert result['shortage_types'] == 3 and result['shelter_places'] == 70
    assert result['pending'] == 4


def test_v4_pdf_contains_all_scope_records_and_map():
    items = [dict(kind='disaster', id=i+1, title=f'Incident {i+1}', disaster_type='FLOOD', state='Assam', city='Guwahati', severity='HIGH', response_status='RESOLVED', latitude=26.14, longitude=91.73, plottable=True) for i in range(24)]
    pdf = PdfReader(BytesIO(overview_pdf(items, {}, [], [], 'severity=HIGH')))
    content = '\n'.join(page.extract_text() for page in pdf.pages)
    assert all(f'Incident {i+1}' in content for i in range(24))
    assert 'severity=HIGH' in content and 'Map legend' in content
    assert any(page.images for page in pdf.pages)
    with patch('app.briefing.india_map', side_effect=OSError('Missing fixture boundaries')):
        fallback=PdfReader(BytesIO(overview_pdf(items, {}, [], [], 'severity=HIGH')))
    text='\n'.join(page.extract_text() for page in fallback.pages)
    assert 'Map image unavailable' in text and 'Incident 24' in text
