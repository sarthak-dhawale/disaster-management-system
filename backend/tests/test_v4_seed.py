import importlib.util
from pathlib import Path
import sys, ast
from unittest.mock import MagicMock

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'database'))
from demo_v4_data import validate, PLACES, RESOURCE_SPECS
from seed_v4 import seed, PREFIX


def test_demo_plan_geography_and_units_are_valid():
    plan=validate()
    assert plan['disasters']==12 and plan['shelters']==16 and plan['resources']==20
    assert len({p[0] for p in PLACES})>=10
    assert sum(stock==0 for _,_,_,stock,_ in RESOURCE_SPECS)==2
    assert sum(minimum>stock for _,_,_,stock,minimum in RESOURCE_SPECS)>=3


def test_complete_seed_rerun_does_not_insert_or_change_accounts():
    conn=MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value={'user_id':101,'full_name':PREFIX+' Administrator','role':'ADMIN'}
    conn.execute.return_value.scalar_one.side_effect=[12,16,20]
    result=seed(conn,'never-used-password')
    assert 'already exists' in result['result']
    assert all(str(c.args[0]).startswith('SELECT') for c in conn.execute.call_args_list)


def test_conflicting_namespace_refuses_without_writes():
    conn=MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value={'user_id':101,'full_name':'Existing person','role':'ADMIN'}
    conn.execute.return_value.scalar_one.return_value=12
    try:seed(conn,'never-used-password')
    except RuntimeError as e:assert 'no overwrite' in str(e)
    else:assert False
    assert all(str(c.args[0]).startswith('SELECT') for c in conn.execute.call_args_list)


def test_seed_is_python310_compatible_and_verification_sql_read_only():
    ast.parse((ROOT/'database/seed_v4.py').read_text(encoding='utf-8'),feature_version=(3,10))
    sql=(ROOT/'database/verify_v4.sql').read_text()
    for statement in sql.split(';'):
        lines=[line for line in statement.splitlines() if line.strip() and not line.strip().startswith('--')]
        if lines:assert '\n'.join(lines).lstrip().startswith('SELECT')


def test_demo_accounts_pass_actual_login_validation():
    from app.models import Login
    from seed_v4 import ADMIN_EMAIL, MANAGER_EMAIL
    emails = [ADMIN_EMAIL, MANAGER_EMAIL]
    emails += [f'demo.v4.public{i:02}@dms.example.com' for i in range(1, 11)]
    emails += [f'demo.v4.volunteer{i:02}@dms.example.com' for i in range(1, 13)]
    for email in emails:
        assert str(Login(email=email, password='validation-only').email) == email
