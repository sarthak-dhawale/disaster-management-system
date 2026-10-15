"""Opt-in, atomic, once-only V4 demo seed. Default --check never connects to MySQL.

Run from backend: python ../database/seed_v4.py --check
After backup/migration: python ../database/seed_v4.py --apply
"""
import argparse, getpass, hashlib, json, sys
from datetime import timedelta
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from demo_v4_data import PREFIX, START, PLACES, RESOURCE_SPECS, SKILLS, validate

ADMIN_EMAIL='demo.v4.admin@dms.example.com'
MANAGER_EMAIL='demo.v4.manager@dms.example.com'


def seed(conn,password):
    from sqlalchemy import text
    from app.security import hash_password
    def execute(sql,params=None): return conn.execute(text(sql),params or {})
    # The batch is one transaction. Its reserved administrator is a completion marker.
    existing=execute('SELECT user_id,full_name,role FROM users WHERE email=:email',{'email':ADMIN_EMAIL}).mappings().first()
    if existing:
        expected={'disasters':12,'shelters':16,'resources':20}
        intact=existing['full_name']==PREFIX+' Administrator' and existing['role']=='ADMIN'
        for table,count in expected.items():
            column='title' if table=='disasters' else 'resource_name' if table=='resources' else 'name'
            intact=intact and execute(f'SELECT COUNT(*) FROM {table} WHERE {column} LIKE :prefix',{'prefix':PREFIX+'%'}).scalar_one()==count
        if intact: return {'result':'Batch already exists. No records or passwords changed.'}
        raise RuntimeError('Reserved demo account exists but the batch differs. Review manually; no overwrite attempted.')
    for table,column in [('users','email'),('disasters','title'),('shelters','name'),('resources','resource_name')]:
        pattern='demo.v4.%@dms.example.%' if table=='users' else PREFIX+'%'
        if execute(f'SELECT COUNT(*) FROM {table} WHERE {column} LIKE :pattern',{'pattern':pattern}).scalar_one():
            raise RuntimeError('A conflicting/partial demo namespace exists. Review it manually before seeding.')
    triggers={r[0] for r in execute('SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()')}
    from app.history_schema import TABLES
    needed={f'dms_v12_audit_{table}_{action}' for table in TABLES for action in ['insert','update','delete']}|{'dms_v12_ledger_insert','dms_v12_ledger_update'}
    if not needed.issubset(triggers): raise RuntimeError('Run the explicit additive migration first; audit/ledger triggers are required.')
    highest=execute('SELECT COALESCE(MAX(audit_id),0) FROM audit_history').scalar_one()
    counts={}
    def actor(id,name): execute('SET @dms_actor_id=:id,@dms_actor_name=:name',{'id':id,'name':name})
    def stamp(table,id,when,action='INSERT'):
        # Touch only new audit entries for new owned records in this transaction.
        execute("""UPDATE audit_history SET created_at=:time,
          after_data=IF(after_data IS NULL,NULL,JSON_SET(after_data,'$.demonstration',true,'$.sample_source','DMS V4 fictional exercise'))
          WHERE audit_id>:highest AND entity=:entity AND record_id=:id AND action=:action""",
          {'time':when,'highest':highest,'entity':table,'id':id,'action':action})
    def insert(table,data,when=None):
        fields=list(data)
        result=execute(f'INSERT INTO {table} ('+','.join(fields)+') VALUES ('+','.join(':'+f for f in fields)+')',data)
        id=result.lastrowid;counts[table]=counts.get(table,0)+1
        if when is not None and table in TABLES: stamp(table,id,when)
        return id
    # Password supplied interactively; independently salted Argon2 hashes per account.
    def account(email,name,role):
        return insert('users',dict(full_name=PREFIX+' '+name,email=email,password_hash=hash_password(password),role=role,status='ACTIVE',created_at=START-timedelta(days=3)))
    admin=account(ADMIN_EMAIL,'Administrator','ADMIN'); manager=account(MANAGER_EMAIL,'Disaster Manager','DISASTER_MANAGER')
    actor(manager,PREFIX+' Disaster Manager')
    public=[account(f'demo.v4.public{i+1:02}@dms.example.com',f'Community Member {i+1:02}','PUBLIC_USER') for i in range(10)]
    volunteer_users=[account(f'demo.v4.volunteer{i+1:02}@dms.example.com',f'Responder {i+1:02}','VOLUNTEER') for i in range(12)]
    locations=[]
    for i in range(18):
        state,district,city,lat,lon,_,_=PLACES[i%12]
        address=f'{PREFIX} exercise zone {i+1:02}, {city}; fictional site'
        key=hashlib.sha256('\x1f'.join([state.lower(),district.lower(),city.lower(),address.lower()]).encode()).hexdigest()
        locations.append(insert('locations',dict(state=state,district=district,city=city,address=address,
            latitude=lat+(0.008 if i>=12 else 0),longitude=lon+(0.008 if i>=12 else 0),coordinate_source='DEMO_SCENARIO',location_key=key)))
    disasters=[]
    for i,place in enumerate(PLACES):
        t=START+timedelta(days=i)
        description=PREFIX+' Fictional response exercise. This record does not describe a verified current emergency.'
        if i==9: description+=' Heatwave scenario uses the existing OTHER disaster type.'
        disasters.append(insert('disasters',dict(location_id=locations[i],reported_by=public[i%10],disaster_type=place[5],
            title=f'{PREFIX} {place[2]} '+('heatwave exercise' if i==9 else place[5].lower()+' exercise'),
            description=description,severity=place[6],status='ACTIVE' if i<10 else 'REPORTED',start_time=t,created_at=t+timedelta(hours=1)),t+timedelta(hours=1)))
    shelters=[]
    for i in range(16):
        capacity=[120,180,100,100][i%4]; occupancy=[0,45,90,100][i%4]
        status='CLOSED' if i==14 else 'FULL' if occupancy==capacity else 'AVAILABLE'
        if status=='CLOSED': occupancy=0
        shelters.append(insert('shelters',dict(location_id=locations[i%18],name=f'{PREFIX} {PLACES[i%12][2]} shelter {i+1:02}',
            capacity=capacity,current_occupancy=occupancy,status=status,created_at=START-timedelta(days=2))))
    resources=[]
    for name,cat,unit,total,minimum in RESOURCE_SPECS:
        resources.append(insert('resources',dict(resource_name=PREFIX+' '+name,category=cat,unit=unit,total_quantity=total,available_quantity=total,minimum_required=minimum)))
    volunteers=[]
    for i,user in enumerate(volunteer_users):
        volunteers.append(insert('volunteers',dict(user_id=user,skills=SKILLS[i],availability_status='AVAILABLE' if i<10 else 'UNAVAILABLE',joined_at=START-timedelta(days=2))))
    for i in range(16):
        t=START+timedelta(days=i%12);place=PLACES[i%12]
        actor(public[i%10],PREFIX+f' Community Member {i%10+1:02}')
        report=insert('emergency_reports',dict(location_id=locations[i%12],reported_by=public[i%10],disaster_type=place[5],report_type='OTHER',
            description=f'{PREFIX} Community observation {i+1:02}; fictional scenario, not a live emergency.',severity=place[6],status='PENDING',
            review_status='PENDING_REVIEW',reported_at=t,occurred_at=t,coordinate_source='SAVED_LOCATION'),t)
        if i<8 or i>=12:
            actor(manager,PREFIX+' Disaster Manager');confirmed=i<8
            execute("""UPDATE emergency_reports SET disaster_id=:disaster,review_status=:review,status=:status,
                reviewed_by=:manager,reviewed_at=:time,review_reason=:reason WHERE report_id=:id""",
                dict(disaster=disasters[i] if confirmed else None,review='CONFIRMED' if confirmed else 'REJECTED',
                status='IN_PROGRESS' if confirmed else 'REJECTED',manager=manager,time=t+timedelta(hours=1),
                reason=PREFIX+(' Verified for exercise and linked to official sample record.' if confirmed else ' Exercise duplicate/unverifiable observation.'),id=report))
            stamp('emergency_reports',report,t+timedelta(hours=1),'UPDATE')
    actor(manager,PREFIX+' Disaster Manager')
    for i in range(24):
        resource=i%20;incident=i%10;t=START+timedelta(days=incident,hours=2)
        quantity=Decimal(60 if resource%3 else 900)
        req=insert('resource_requests',dict(disaster_id=disasters[incident],resource_id=resources[resource],quantity=quantity,
            note=f'{PREFIX} Demand {i+1:02}: fictional planning quantity.',status='CANCELLED' if i==23 else 'OPEN',created_by=manager,created_at=t,updated_at=t),t)
        if i<12 and RESOURCE_SPECS[resource][3]>0:
            current=execute('SELECT available_quantity FROM resources WHERE resource_id=:id FOR UPDATE',{'id':resources[resource]}).scalar_one()
            amount=min(quantity,Decimal(str(current))/4) if i%2==0 else min(quantity,Decimal(str(current)))
            if amount<=0: raise RuntimeError('Demo allocation unexpectedly exceeds available stock')
            allocation=insert('resource_allocations',dict(resource_id=resources[resource],disaster_id=disasters[incident],shelter_id=None,
                allocated_by=manager,quantity=amount,allocation_date=t+timedelta(hours=1),status='DELIVERED' if i%3==0 else 'ALLOCATED',
                request_id=req,approval_key=f'dms-v4-demo-allocation-{i+1:02}'),t+timedelta(hours=1))
            execute('SET @dms_movement_kind=:kind,@dms_movement_note=:note,@dms_allocation_id=:id',{'kind':'DEMO_ALLOCATION','note':PREFIX+' Fictional stock reservation','id':allocation})
            execute('UPDATE resources SET available_quantity=available_quantity-:quantity WHERE resource_id=:id',{'quantity':amount,'id':resources[resource]})
            execute('SET @dms_movement_kind=NULL,@dms_movement_note=NULL,@dms_allocation_id=NULL')
    for i in range(10):
        t=START+timedelta(days=i,hours=4);completed=i>=8
        insert('volunteer_assignments',dict(volunteer_id=volunteers[i],disaster_id=disasters[i],shelter_id=None,assigned_by=manager,
            assignment_role=SKILLS[i],start_time=t,end_time=t+timedelta(hours=8) if completed else None,status='COMPLETED' if completed else 'ACTIVE'),t)
        if not completed:execute("UPDATE volunteers SET availability_status='ASSIGNED' WHERE volunteer_id=:id",{'id':volunteers[i]})
    # Occupancy includes explicit aggregate headcounts; active registrations add one each.
    eligible=[0,1,2,4,5,6,8,9,10,12]
    for i,shelter_index in enumerate(eligible):
        t=START+timedelta(days=i%10,hours=5)
        insert('shelter_registrations',dict(shelter_id=shelters[shelter_index],user_id=public[i],check_in=t,status='ACTIVE'),t)
        execute('UPDATE shelters SET current_occupancy=current_occupancy+1 WHERE shelter_id=:id',{'id':shelters[shelter_index]})
    for i in range(4):
        t=START-timedelta(days=2)+timedelta(hours=i)
        insert('shelter_registrations',dict(shelter_id=shelters[4+i],user_id=public[i],check_in=t,check_out=t+timedelta(hours=2),status='CHECKED_OUT'),t)
    for i in [4,7,8]:
        t=START+timedelta(days=i+2)
        execute("UPDATE disasters SET status='RESOLVED',end_time=:time WHERE disaster_id=:id",{'time':t,'id':disasters[i]})
        stamp('disasters',disasters[i],t,'UPDATE')
        execute("UPDATE volunteer_assignments SET status='COMPLETED',end_time=:time WHERE disaster_id=:id",{'time':t,'id':disasters[i]})
        execute("UPDATE volunteers SET availability_status='AVAILABLE' WHERE volunteer_id=:id",{'id':volunteers[i]})
    # Final SQL invariants protect the whole atomic insert, including stock/capacity.
    bad=execute("SELECT COUNT(*) FROM resources WHERE available_quantity<0 OR available_quantity>total_quantity").scalar_one()
    bad+=execute('SELECT COUNT(*) FROM shelters WHERE current_occupancy<0 OR current_occupancy>capacity').scalar_one()
    if bad: raise RuntimeError('Inventory/capacity validation failed; complete seed transaction rolled back')
    return {'result':'New demonstration batch inserted; all earlier records retained.','inserted':counts,
            'accounts':{'administrator':ADMIN_EMAIL,'manager':MANAGER_EMAIL,'public':'demo.v4.public01@dms.example.com','volunteer':'demo.v4.volunteer01@dms.example.com'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group();group.add_argument('--check',action='store_true');group.add_argument('--apply',action='store_true')
    args=parser.parse_args();print(json.dumps(validate(),indent=2))
    if not args.apply:
        print('Static plan checked. No database connection or writes. Use --apply only after backup and migration.');return
    password=getpass.getpass('New demonstration accounts password (10–128 characters): ')
    if not 10<=len(password)<=128 or password!=getpass.getpass('Confirm demonstration password: '):raise SystemExit('Password invalid or confirmation differs')
    from sqlalchemy import text
    from app.database import engine
    try:
        with engine.connect() as conn:
            locked=conn.execute(text("SELECT GET_LOCK('dms_v4_demo_seed',10)")).scalar_one();conn.commit()
            if locked!=1:raise RuntimeError('Another seed operation is active')
            try:
                with conn.begin():result=seed(conn,password)
                print(json.dumps(result,indent=2))
            finally:
                conn.execute(text("SELECT RELEASE_LOCK('dms_v4_demo_seed')"));conn.commit()
    except Exception as exc:
        # Never print bound SQL parameters, URLs, passwords or hashes on failure.
        message=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__+'; check MySQL readiness/schema and backup instructions'
        raise SystemExit('Seed did not complete: '+message) from None


if __name__=='__main__':main()
