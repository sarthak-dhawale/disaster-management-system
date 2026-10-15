"""Explicitly fictional Indian response scenarios. No current emergency claims."""
from datetime import datetime, timedelta

PREFIX='[DEMO V4]'
START=datetime(2026,9,1,8)
# Approximate city coordinates are scenario placements, not surveyed shelter sites.
PLACES=[
    ('Assam','Kamrup Metropolitan','Guwahati',26.1445,91.7362,'FLOOD','CRITICAL'),
    ('Bihar','Patna','Patna',25.5941,85.1376,'FLOOD','HIGH'),
    ('Odisha','Puri','Puri',19.8135,85.8312,'CYCLONE','CRITICAL'),
    ('Andhra Pradesh','Visakhapatnam','Visakhapatnam',17.6868,83.2185,'CYCLONE','HIGH'),
    ('Kerala','Ernakulam','Kochi',9.9312,76.2673,'FLOOD','HIGH'),
    ('Uttarakhand','Dehradun','Dehradun',30.3165,78.0322,'LANDSLIDE','MEDIUM'),
    ('Himachal Pradesh','Mandi','Mandi',31.7087,76.9310,'LANDSLIDE','HIGH'),
    ('Tamil Nadu','Chennai','Chennai',13.0827,80.2707,'CYCLONE','HIGH'),
    ('West Bengal','South 24 Parganas','Diamond Harbour',22.1930,88.1840,'CYCLONE','MEDIUM'),
    ('Rajasthan','Jodhpur','Jodhpur',26.2389,73.0243,'OTHER','HIGH'),
    ('Assam','Dibrugarh','Dibrugarh',27.4728,94.9120,'FLOOD','LOW'),
    ('Bihar','Darbhanga','Darbhanga',26.1542,85.8918,'FLOOD','MEDIUM'),
]
RESOURCE_SPECS=[
    ('Drinking water','WATER','litres',600,150),('Rice packs','FOOD','packs',1000,100),
    ('First aid kits','MEDICINE','kits',60,20),('Oral rehydration salts','MEDICINE','sachets',0,50),
    ('Blankets','CLOTHING','pieces',300,50),('Tarpaulins','SHELTER_SUPPLIES','sheets',30,25),
    ('Rescue ropes','EQUIPMENT','metres',500,100),('Life jackets','EQUIPMENT','pieces',40,20),
    ('Family tents','SHELTER_SUPPLIES','tents',20,15),('Hygiene kits','OTHER','kits',400,80),
    ('Baby food','FOOD','packs',100,30),('Water containers','WATER','containers',200,40),
    ('Flashlights','EQUIPMENT','pieces',250,50),('Battery packs','EQUIPMENT','packs',600,80),
    ('Raincoats','CLOTHING','pieces',150,30),('Medical gloves','MEDICINE','boxes',80,15),
    ('Mosquito nets','SHELTER_SUPPLIES','nets',200,40),('Dry ration boxes','FOOD','boxes',25,30),
    ('Sanitation supplies','OTHER','kits',0,20),('Portable pumps','EQUIPMENT','pumps',12,5),
]
SKILLS=['First aid','Search and rescue','Shelter coordination','Water sanitation','Logistics','Community outreach','Medical assistance','Radio communication','Food distribution','Mapping support','Transport coordination','Psychological first aid']


def plan():
    return {'disasters':12,'locations':18,'shelters':16,'resources':20,'volunteers':12,
            'public_users':10,'role_accounts':2,'emergency_reports':16,'resource_requests':24,
            'resource_allocations':11,'volunteer_assignments':10,'shelter_registrations':14,
            'histories':'Existing audit_history and resource_movements; demo metadata is explicit.'}


def validate():
    assert len(PLACES)==12 and len(RESOURCE_SPECS)==20 and len(SKILLS)==12
    assert all(6<=p[3]<=38 and 68<=p[4]<=98 for p in PLACES)
    assert all(total>=0 and minimum>=0 and unit for _,_,unit,total,minimum in RESOURCE_SPECS)
    assert len({p[2] for p in PLACES})==12
    return plan()
