from fastapi import APIRouter, Depends, Path
from fastapi.responses import Response
from app.database import get_db
from app.security import require_admin
from app.replay import replay
from app.reporting import build_pdf
from app.routes.reports_v3 import download_headers

router=APIRouter(prefix='/api/replay',tags=['Disaster Replay Studio'],dependencies=[Depends(require_admin)])


@router.get('/disasters/{id}')
def timeline(id: int=Path(gt=0),db=Depends(get_db)):
    return replay(db,id)


@router.get('/disasters/{id}/pdf')
def timeline_pdf(id: int=Path(gt=0),db=Depends(get_db)):
    result=replay(db,id);d=result['disaster']
    details=[{'disaster_id':id,'title':d['title'],'type':d['disaster_type'],'location':', '.join(filter(None,[d.get('city'),d.get('state')])),'status':d['status']}]
    events=[{**e,'actor':e.get('actor_name') or ('User #'+str(e['actor_id']) if e.get('actor_id') else 'Not recorded'),
             'record':e['entity']+' #'+str(e['record_id'])} for e in result['items']]
    pdf=build_pdf('Disaster Replay Studio', [('Selected incident',details,['disaster_id','title','type','location','status']),
        ('Chronological recorded events',events,['timestamp','title','category','status','actor','record'])],
        scope=f'Disaster #{id}; read-only recorded-event timeline',warnings=[result['history_note'],
        'Explicit demonstration record; sample events are illustrative.' if result['demonstration'] else 'Only available recorded history is shown.'])
    return Response(pdf,media_type='application/pdf',headers=download_headers(f'replay-{id}','pdf'))
