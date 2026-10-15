"""Read-only timeline assembled from recorded row timestamps and existing audit history.

No historical state is guessed and no events are written by opening or seeking replay.
"""
import json
from fastapi import HTTPException
from sqlalchemy import text
from app.geo import valid_coordinates

NOTE = ("Partial historical coverage: only stored timestamps and installed audit records are available. "
        "Current location coordinates provide context, not a reconstruction of historical geography. "
        "Shelter registrations have no direct disaster reference and are not attributed to an incident by proximity.")
ASSOCIATED = {
    'emergency_reports': ('report_id', 'reported_at', 'Emergency report submitted'),
    'resource_requests': ('request_id', 'created_at', 'Resource demand recorded'),
    'resource_allocations': ('allocation_id', 'allocation_date', 'Resource allocation recorded'),
    'volunteer_assignments': ('assignment_id', 'start_time', 'Volunteer assignment scheduled'),
}


def decoded(value):
    if isinstance(value, str):
        try: return json.loads(value)
        except (ValueError, TypeError): return {}
    return value if isinstance(value, dict) else {}


def category(entity, action, before, after):
    if after.get('review_status') == 'REJECTED': return 'WARNING'
    if after.get('status') == 'RESOLVED': return 'ACTION_TAKEN'
    if entity == 'disasters' and after.get('severity') == 'CRITICAL': return 'CRITICAL'
    if entity in {'resource_requests', 'emergency_reports'} and action == 'INSERT': return 'WARNING'
    return 'INFORMATION' if entity == 'disasters' and action == 'INSERT' else 'ACTION_TAKEN'


def event_title(entity, action, before, after):
    if entity == 'emergency_reports' and before.get('review_status') != after.get('review_status') and after.get('review_status') in {'CONFIRMED','REJECTED'}:
        return 'Emergency report ' + after['review_status'].lower()
    if entity == 'disasters' and before.get('status') != after.get('status') and action == 'UPDATE':
        return 'Incident resolved' if after.get('status') == 'RESOLVED' else 'Disaster status changed'
    if action == 'INSERT':
        return 'Disaster created' if entity == 'disasters' else ASSOCIATED.get(entity, (None,None,entity.replace('_',' ').title()+' recorded'))[2]
    return entity.replace('_',' ').title() + (' removed' if action == 'DELETE' else ' updated')


def replay(db, disaster_id):
    disaster = db.execute(text("""SELECT d.*,l.state,l.city,l.address,l.latitude,l.longitude
        FROM disasters d JOIN locations l ON l.location_id=d.location_id WHERE d.disaster_id=:id"""), {'id':disaster_id}).mappings().first()
    if not disaster: raise HTTPException(404, 'Disaster not found')
    incident = dict(disaster)
    # Report IDs retain submission/review events from before they were linked to this disaster.
    audits = db.execute(text("""SELECT audit_id,entity,record_id,action,actor_id,actor_name,
        before_data,after_data,created_at FROM audit_history WHERE
        (entity='disasters' AND record_id=:id) OR
        (entity='emergency_reports' AND record_id IN (SELECT report_id FROM emergency_reports WHERE disaster_id=:id)) OR
        (entity IN ('emergency_reports','resource_requests','resource_allocations','volunteer_assignments') AND
          (JSON_UNQUOTE(JSON_EXTRACT(before_data,'$.disaster_id'))=CAST(:id AS CHAR) OR
           JSON_UNQUOTE(JSON_EXTRACT(after_data,'$.disaster_id'))=CAST(:id AS CHAR)))
        ORDER BY created_at,audit_id"""), {'id':disaster_id}).mappings().all()
    events=[]; inserted=set(); reviewed=set()
    for raw in audits:
        a=dict(raw); before,after=decoded(a['before_data']),decoded(a['after_data'])
        entity=a['entity']; record_id=a['record_id']
        if a['action']=='INSERT': inserted.add((entity,record_id))
        if entity=='emergency_reports' and before.get('review_status')!=after.get('review_status') and after.get('review_status') in {'CONFIRMED','REJECTED'}: reviewed.add(record_id)
        title=event_title(entity,a['action'],before,after)
        status=after.get('review_status') if entity=='emergency_reports' else after.get('status')
        events.append({'event_id':f"audit:{a['audit_id']}",'timestamp':a['created_at'],'title':title,
            'category':category(entity,a['action'],before,after),'description':f"{entity.replace('_',' ')} #{record_id}: {a['action'].lower()}",
            'status':status,'actor_id':a.get('actor_id'),'actor_name':a.get('actor_name'),
            'entity':entity,'record_id':record_id,'source':'Recorded audit event','metadata':{'before':before,'after':after}})
    def baseline(entity,row,key,time,title):
        if row.get(time) is None or (entity,row[key]) in inserted: return
        events.append({'event_id':f'row:{entity}:{row[key]}:{time}','timestamp':row[time],'title':title,
            'description':'Stored record timestamp; earlier changes may not have been captured.',
            'category':category(entity,'INSERT',{},row),'status':row.get('review_status') if entity=='emergency_reports' else row.get('status'),
            'entity':entity,'record_id':row[key],'actor_id':None,'actor_name':None,'source':'Stored row timestamp (partial history)',
            'metadata':{'timestamp_field':time}})
    baseline('disasters',incident,'disaster_id','created_at','Official disaster record created')
    related={}
    for entity,(key,time,title) in ASSOCIATED.items():
        # Entity names come exclusively from this fixed dictionary.
        rows=[dict(r) for r in db.execute(text(f'SELECT * FROM {entity} WHERE disaster_id=:id ORDER BY {key}'), {'id':disaster_id}).mappings().all()]
        related[entity]=rows
        for row in rows:
            baseline(entity,row,key,time,title)
            if entity=='emergency_reports' and row.get('reviewed_at') and row[key] not in reviewed:
                events.append({'event_id':f'row:report:{row[key]}:review','timestamp':row['reviewed_at'],
                    'title':'Emergency report '+row.get('review_status','reviewed').lower(), 'description':row.get('review_reason') or 'Stored review decision',
                    'category':'WARNING' if row.get('review_status')=='REJECTED' else 'ACTION_TAKEN',
                    'status':row.get('review_status'),'actor_id':row.get('reviewed_by'),'actor_name':None,
                    'entity':entity,'record_id':row[key],'source':'Stored review timestamp','metadata':{}})
    if incident.get('end_time') and incident['status']=='RESOLVED' and not any(e['title']=='Incident resolved' for e in events):
        events.append({'event_id':f'row:disaster:{disaster_id}:resolution','timestamp':incident['end_time'],
            'title':'Recorded incident end time','description':'Recorded end_time; not evidence of when a manager changed status.',
            'category':'INFORMATION','status':'RESOLVED','actor_id':None,'actor_name':None,
            'entity':'disasters','record_id':disaster_id,'source':'Stored end timestamp','metadata':{}})
    locations={incident['location_id']:{'latitude':incident.get('latitude'),'longitude':incident.get('longitude'),'city':incident.get('city'),'state':incident.get('state')}}
    ids={snap.get('location_id') for e in events for snap in [e['metadata'].get('before',{}),e['metadata'].get('after',{})] if snap.get('location_id')}
    if ids:
        params={f'l{i}':v for i,v in enumerate(sorted(ids))}
        for r in db.execute(text('SELECT location_id,latitude,longitude,city,state FROM locations WHERE location_id IN ('+','.join(':'+k for k in params)+')'),params).mappings(): locations[r['location_id']]=dict(r)
    for e in events:
        snapshot=e['metadata'].get('after') or e['metadata'].get('before') or {}
        location=locations.get(snapshot.get('location_id'),locations[incident['location_id']])
        e['location']={**location,'context':'Current stored coordinates; incident context when no event location is recorded'}
        e['location']['plottable']=valid_coordinates(location.get('latitude'),location.get('longitude'))
        e['timestamp']=e['timestamp'].isoformat() if hasattr(e['timestamp'],'isoformat') else str(e['timestamp']).replace(' ','T')
    events.sort(key=lambda e:(e['timestamp'],e['event_id']))
    # Never serialize account emails/phones/passwords from joined records or snapshots.
    incident={k:v for k,v in incident.items() if k not in {'reported_by'}}
    return {'disaster':incident,'items':events,'event_count':len(events),'audit_event_count':len(audits),
            'coverage':'PARTIAL','history_note':NOTE,'read_only':True,
            'demonstration':str(incident.get('title','')).startswith('[DEMO V4]')}
