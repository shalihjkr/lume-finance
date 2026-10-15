import re
import sqlite3
import pytest
from database import get_db, init_db
from app.services.finance_service import seed_demo

@pytest.mark.parametrize('path', ['/', '/dashboard', '/transactions', '/transactions/new', '/budgets', '/analytics', '/settings'])
def test_pages(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b'Lume' in response.data

def test_health(client, app):
    app.config['APP_VERSION'] = '2.3.4'
    assert client.get('/health').json == dict(status='healthy', application='Lume Finance', version='2.3.4')

@pytest.mark.parametrize('kind,category', [('income','Salary'), ('expense','Food')])
def test_add(client, app, transaction, kind, category):
    transaction.update(type=kind, category=category)
    assert client.post('/transactions', data=transaction).status_code == 302
    with app.app_context():
        row = get_db().execute('SELECT * FROM transactions').fetchone()
        assert row['amount'] == 1234 and row['type'] == kind

@pytest.mark.parametrize('field,value', [('description',' '),('description','a'*161),('amount','0'),('amount','-2'),('amount','nan'),('amount','inf'),('amount','1.001'),('amount','1000000000'),('amount','no'),('date','2026-02-30'),('date','20261010'),('type','transfer'),('category','Salary'),('notes','a'*2001)])
def test_invalid(client, app, transaction, field, value):
    transaction[field] = value
    assert client.post('/transactions', data=transaction).status_code == 400
    with app.app_context():
        assert get_db().execute('SELECT count(*) FROM transactions').fetchone()[0] == 0

def test_edit_delete_missing(client, transaction):
    client.post('/transactions', data=transaction)
    assert client.get('/transactions/1/edit').status_code == 200
    transaction.update(amount='42.00', description='Changed')
    assert client.post('/transactions/1/edit', data=transaction).status_code == 302
    assert b'Changed' in client.get('/transactions').data
    assert client.get('/api/summary?month=2026-10').json['expenses'] == 4200
    assert client.post('/transactions/1/delete').status_code == 302
    assert client.get('/transactions/1/edit').status_code == 404
    assert client.post('/transactions/1/edit', data=transaction).status_code == 404
    assert client.post('/transactions/1/delete').status_code == 404

def test_calculations_budgets_and_charts(client, transaction):
    client.post('/transactions', data=transaction)
    client.post('/transactions', data={**transaction, 'type':'income', 'category':'Salary','amount':'100.00'})
    client.post('/transactions', data={**transaction, 'date':'2026-09-01','amount':'5.00'})
    assert client.post('/budgets', data=dict(month='2026-10',category='Food',amount='10')).status_code == 302
    s = client.get('/api/summary?month=2026-10').json
    assert (s['income'],s['expenses'],s['balance'],s['monthly_expenses'],s['remaining']) == (10000,1734,8266,1234,-234)
    page = client.get('/budgets?month=2026-10').data
    assert b'Over budget' in page and b'123.4%' in page
    charts = client.get('/api/charts?month=2026-10').json
    assert charts['unit'] == 'minor'
    assert charts['categories'] == dict(labels=['Food'],values=[1234])
    assert len(charts['monthly']['labels']) == 6
    assert charts['monthly']['expense'][-2:] == [500,1234]
    assert charts['daily'] == dict(labels=['2026-10-10'],income=[10000],expense=[1234])
    client.post('/budgets',data=dict(month='2026-10',category='Food',amount='20'))
    assert client.get('/api/summary?month=2026-10').json['remaining'] == 766
    assert client.post('/budgets/1/delete').status_code == 302
    assert client.post('/budgets/1/delete').status_code == 404

@pytest.mark.parametrize('data', [dict(month='bad',category='Food',amount='10'),dict(month='2026-10',category='Salary',amount='10'),dict(month='2026-10',category='Food',amount='0')])
def test_invalid_budgets(client,data):
    assert client.post('/budgets',data=data).status_code == 400

def test_empty_and_invalid_apis(client):
    assert client.get('/api/summary').json['balance'] == 0
    assert client.get('/api/charts').json['categories']['values'] == []
    assert client.get('/api/charts?month=bad').status_code == 400
    assert client.get('/api/charts?month=0001-01').status_code == 200
    assert client.get('/transactions?start=bad').status_code == 400

def test_filters_sort_pagination_escape(client,transaction):
    for i in range(17):
        client.post('/transactions',data={**transaction,'description':f'Entry {i:02d}','amount':str(i+1)})
    assert b'Page 1 of 2' in client.get('/transactions').data
    assert b'Page 2 of 2' in client.get('/transactions?page=2').data
    assert b'Entry 16' in client.get('/transactions?q=16&type=expense&category=Food&start=2026-10-01&end=2026-10-31').data
    assert b'Entry 16' not in client.get('/transactions?type=income').data
    page=client.get('/transactions?sort=amount_asc').data
    assert page.index(b'Entry 00') < page.index(b'Entry 01')
    client.post('/transactions',data={**transaction,'description':'<script>alert(1)</script>'})
    assert b'&lt;script&gt;' in client.get('/transactions?q=script').data
    assert client.get('/transactions?q=%27%20OR%201=1--').status_code == 200

def test_preferences(client, transaction):
    client.post('/transactions',data=transaction)
    for currency,symbol in [('GBP','\u00a3'),('USD','$'),('INR','\u20b9')]:
        assert client.post('/settings',data=dict(currency=currency,compact='on')).status_code == 302
        assert (symbol+'12.34').encode() in client.get('/transactions').data
        assert client.get('/api/summary').json['expenses'] == 1234
    assert client.post('/settings',data=dict(currency='EUR')).status_code == 400

def test_csrf(client,app,transaction):
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/transactions',data=transaction).status_code == 400
    token=re.search(rb'name="csrf_token" value="([^"]+)"',client.get('/transactions/new').data).group(1).decode()
    assert client.post('/transactions',data={**transaction,'csrf_token':token}).status_code == 302

def test_seed_idempotent_and_migration(app):
    with app.app_context():
        seed_demo(1)
        before = get_db().execute('SELECT count(*),sum(amount) FROM transactions').fetchone()
        seed_demo(1)
        init_db()
        after = get_db().execute('SELECT count(*),sum(amount) FROM transactions').fetchone()
        assert tuple(before) == tuple(after) and before[0] == 60
        assert get_db().execute('PRAGMA user_version').fetchone()[0] == 2

def test_storage_error(client, monkeypatch):
    def broken(*args):
        raise sqlite3.OperationalError('private diagnostic')
    monkeypatch.setattr('app.routes.summary',broken)
    response=client.get('/api/summary')
    assert response.status_code == 503
    assert b'private diagnostic' not in response.data


def test_exact_large_money_and_indian_grouping(app):
    from app.services.finance_service import money, amount_cents
    with app.app_context():
        from flask import g
        g.user=dict(id=1)
        assert amount_cents('999999999.99') == 99999999999
        assert money(99999999999) == '\u00a3999,999,999.99'
        get_db().execute("UPDATE user_settings SET currency='INR'")
        assert money(123456789) == '\u20b912,34,567.89'
        assert money(-234) == '-\u20b92.34'


def test_screenshot_scenario(client,transaction):
    client.post('/transactions',data={**transaction,'description':'Salary','type':'income','category':'Salary','amount':'10000','date':'2026-10-15'})
    client.post('/transactions',data={**transaction,'description':'Dinner','amount':'25','date':'2026-10-15'})
    client.post('/transactions',data={**transaction,'description':'Travel','category':'Transport','amount':'60','date':'2026-10-15'})
    summary=client.get('/api/summary?month=2026-10').json
    assert (summary['income'],summary['expenses'],summary['balance'])==(1000000,8500,991500)
    charts=client.get('/api/charts?month=2026-10').json
    assert charts['categories']==dict(labels=['Transport','Food'],values=[6000,2500])
    assert charts['daily']==dict(labels=['2026-10-15'],income=[1000000],expense=[8500])
    page=client.get('/dashboard?month=2026-10').data
    assert b'Not set' in page
    assert b'-\xc2\xa385.00' not in page
    client.post('/budgets',data=dict(month='2026-10',category='Food',amount='100'))
    assert client.get('/api/summary?month=2026-10').json['remaining']==1500
