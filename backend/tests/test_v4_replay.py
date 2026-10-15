from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from app.replay import replay, category
from app.history_schema import audit_trigger, TABLES, REPLAY_FIELDS, install_v4_history
from app.main import app
from app.security import current_user
from conftest import ADMIN, PUBLIC


def result(rows=None, first=None):
    r=MagicMock();r.mappings.return_value.all.return_value=rows or []
    r.mappings.return_value.first.return_value=first
    r.mappings.return_value.__iter__.return_value=iter(rows or [])
    return r


def test_replay_order_partial_history_and_no_writes(db):
    t=datetime(2026,1,1,10)
    incident=dict(disaster_id=12,title='Recorded flood',disaster_type='FLOOD',status='ACTIVE',severity='HIGH',location_id=1,created_at=t,latitude=26.1,longitude=91.7,city='Guwahati',state='Assam')
    audits=[dict(audit_id=2,entity='emergency_reports',record_id=8,action='UPDATE',actor_id=1,actor_name='Manager',created_at=t+timedelta(minutes=5),before_data={'review_status':'PENDING_REVIEW'},after_data={'review_status':'CONFIRMED','disaster_id':12})]
    report=dict(report_id=8,reported_at=t-timedelta(minutes=10),reviewed_at=t+timedelta(minutes=5),review_status='CONFIRMED',disaster_id=12)
    db.execute.side_effect=[result(first=incident),result(audits),result([report]),result(),result(),result()]
    data=replay(db,12)
    assert data['coverage']=='PARTIAL' and data['event_count']==3
    assert data['items'][0]['title']=='Emergency report submitted'
    assert data['items'][-1]['title']=='Emergency report confirmed'
    assert len({e['event_id'] for e in data['items']})==3
    assert all(str(c.args[0]).lstrip().startswith('SELECT') for c in db.execute.call_args_list)
    db.commit.assert_not_called()
    assert all(e['location']['plottable'] for e in data['items'])


def test_replay_missing_record(db):
    db.execute.return_value.mappings.return_value.first.return_value=None
    with pytest.raises(HTTPException) as e: replay(db,999)
    assert e.value.status_code==404


def test_replay_empty_timestamp_history_is_honest(db):
    incident=dict(disaster_id=1,title='Legacy record',disaster_type='FLOOD',status='REPORTED',severity='LOW',location_id=1,latitude=None,longitude=None)
    db.execute.side_effect=[result(first=incident),result(),result(),result(),result(),result()]
    data=replay(db,1)
    assert data['items']==[] and data['read_only'] and 'Partial' in data['history_note']


def test_replay_permissions_and_read_only_http_methods(client):
    for role in ['PUBLIC_USER','VOLUNTEER']:
        app.dependency_overrides[current_user]=lambda: {**PUBLIC,'role':role}
        assert client.get('/api/replay/disasters/1').status_code==403
        assert client.get('/api/replay/disasters/1/pdf').status_code==403
    app.dependency_overrides[current_user]=lambda: ADMIN
    assert client.post('/api/replay/disasters/1',headers={'X-DMS-Request':'1'}).status_code==405
    with patch('app.routes.replay.replay',return_value={'items':[],'coverage':'PARTIAL'}):
        app.dependency_overrides[current_user]=lambda: {**ADMIN,'role':'DISASTER_MANAGER'}
        assert client.get('/api/replay/disasters/1').json()['coverage']=='PARTIAL'


def test_future_event_triggers_include_response_timestamps_without_account_secrets():
    for entity,fields in REPLAY_FIELDS.items():
        sql=audit_trigger(entity,'UPDATE')
        assert all("'"+field+"'" in sql for field in fields)
        assert 'password' not in sql and 'token' not in sql
    assert 'check_in' in TABLES['shelter_registrations'][1]
    assert category('disasters','UPDATE',{'status':'ACTIVE'},{'status':'RESOLVED'})=='ACTION_TAKEN'


def test_up_to_date_history_migration_does_not_recreate_triggers(db):
    rows=[{'TRIGGER_NAME':f'dms_v12_audit_{table}_{action.lower()}', 'ACTION_STATEMENT':audit_trigger(table,action)} for table in REPLAY_FIELDS for action in ['INSERT','UPDATE','DELETE']]
    db.execute.return_value.mappings.return_value.__iter__.return_value=iter(rows)
    install_v4_history(db)
    db.exec_driver_sql.assert_not_called()


def test_replay_pdf_is_a_real_download_with_events(client):
    from io import BytesIO
    from pypdf import PdfReader
    app.dependency_overrides[current_user] = lambda: ADMIN
    fixture = dict(disaster=dict(title='Flood exercise', disaster_type='FLOOD', city='Patna', state='Bihar', status='ACTIVE'),
                   items=[dict(timestamp='2026-01-01T12:00:00', title='Resource demand recorded', category='WARNING',
                               status='OPEN', actor_id=1, actor_name='Manager', entity='resource_requests', record_id=42)],
                   history_note='Partial recorded history.', demonstration=True)
    with patch('app.routes.replay.replay', return_value=fixture):
        response = client.get('/api/replay/disasters/12/pdf')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/pdf'
    assert 'attachment;' in response.headers['content-disposition']
    reader = PdfReader(BytesIO(response.content))
    text = '\n'.join(page.extract_text() for page in reader.pages)
    assert 'Flood exercise' in text and 'Resource demand recorded' in text
    assert 'resource_requests#42' in ''.join(text.split())
    assert 'Partial recorded history.' in text
