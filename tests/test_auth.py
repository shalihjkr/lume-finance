import re
import sqlite3
import pytest
from werkzeug.security import check_password_hash
from database import get_db
from app import create_app


def register(client, email='new@example.com', **overrides):
    data=dict(name='New User',email=email,password='a-long-passphrase-123',confirm_password='a-long-passphrase-123')
    data.update(overrides)
    return client.post('/register',data=data)


def login(client,email='new@example.com',password='a-long-passphrase-123'):
    return client.post('/login',data=dict(email=email,password=password))


def test_full_account_flow(app):
    client=app.test_client()
    assert client.get('/').status_code==200
    assert b'More clarity.' in client.get('/').data
    assert client.get('/dashboard').location.endswith('/login')
    assert register(client).location.endswith('/login')
    assert client.get('/dashboard').status_code==302
    with app.app_context():
        row=get_db().execute('SELECT * FROM users WHERE email=?',('new@example.com',)).fetchone()
        assert row['password_hash']!='a-long-passphrase-123'
        assert check_password_hash(row['password_hash'],'a-long-passphrase-123')
    assert login(client,email='NEW@example.com').location.endswith('/dashboard')
    assert b'Financial overview' in client.get('/dashboard').data
    assert client.get('/dashboard').headers['Cache-Control']=='no-store'
    assert client.post('/logout').location.endswith('/')
    assert client.get('/dashboard').location.endswith('/login')
    assert client.get('/logout').status_code==405


@pytest.mark.parametrize('path', ['/dashboard','/transactions','/transactions/new','/transactions/1/edit','/budgets','/analytics','/settings'])
def test_private_pages_require_login(app,path):
    assert app.test_client().get(path).location.endswith('/login')


@pytest.mark.parametrize('path', ['/api/summary','/api/charts'])
def test_private_apis_require_login(app,path):
    assert app.test_client().get(path).status_code==401


@pytest.mark.parametrize('field,value', [('name',''),('name','a'*81),('email','bad'),('password','short'),('password','x'*129),('confirm_password','different')])
def test_registration_validation(app,field,value):
    assert register(app.test_client(),**{field:value}).status_code==400


def test_duplicate_and_invalid_login(app):
    client=app.test_client()
    assert register(client).status_code==302
    assert register(client,email='NEW@example.com').status_code==400
    for email in ['new@example.com','missing@example.com']:
        response=login(client,email=email,password='incorrect')
        assert response.status_code==400
        assert b'Email or password is incorrect.' in response.data
    assert login(client).status_code==302
    assert client.get('/register').location.endswith('/dashboard')
    assert client.get('/login').location.endswith('/dashboard')


def test_login_throttle(app):
    client=app.test_client()
    for _ in range(8):
        assert login(client,password='wrong').status_code==400
    assert login(client,password='wrong').status_code==429


def test_account_isolation(app,client,transaction):
    client.post('/transactions',data=transaction)
    client.post('/budgets',data=dict(month='2026-10',category='Food',amount='10'))
    client.post('/settings',data=dict(currency='INR',compact='on'))
    other=app.test_client()
    register(other)
    login(other)
    assert other.get('/api/summary?month=2026-10').json['expenses']==0
    assert other.get('/api/summary?month=2026-10').json['budget']==0
    assert other.get('/api/charts?month=2026-10').json['categories']['values']==[]
    assert b'Test groceries' not in other.get('/transactions').data
    assert b'Test groceries' not in other.get('/dashboard').data
    assert b'GBP' in other.get('/settings').data
    assert other.get('/transactions/1/edit').status_code==404
    assert other.post('/transactions/1/edit',data={**transaction,'amount':'50'}).status_code==404
    assert other.post('/transactions/1/delete').status_code==404
    assert other.post('/budgets/1/delete').status_code==404
    other.post('/transactions',data={**transaction,'amount':'3.00'})
    other.post('/budgets',data=dict(month='2026-10',category='Food',amount='20'))
    other.post('/settings',data=dict(currency='USD'))
    assert client.get('/api/summary?month=2026-10').json['expenses']==1234
    assert client.get('/api/summary?month=2026-10').json['budget']==1000
    assert other.get('/api/summary?month=2026-10').json['expenses']==300
    with app.app_context():
        assert get_db().execute('SELECT currency FROM user_settings WHERE user_id=1').fetchone()[0]=='INR'


def token(response):
    return re.search(rb'name="csrf_token" value="([^"]+)"',response.data).group(1).decode()


def test_auth_csrf(app):
    app.config['WTF_CSRF_ENABLED']=True
    client=app.test_client()
    assert register(client).status_code==400
    csrf=token(client.get('/register'))
    assert register(client,csrf_token=csrf).status_code==302
    assert login(client).status_code==400
    csrf=token(client.get('/login'))
    assert client.post('/login',data=dict(email='new@example.com',password='a-long-passphrase-123',csrf_token=csrf)).status_code==302
    assert client.post('/logout').status_code==400
    csrf=token(client.get('/dashboard'))
    assert client.post('/logout',data=dict(csrf_token=csrf)).status_code==302


@pytest.mark.parametrize('slug',['a-budget-you-can-live-with','small-expenses-clearer-picture','your-monthly-money-reset'])
def test_public_articles(app,slug):
    assert app.test_client().get('/journal/'+slug).status_code==200
    assert app.test_client().get('/journal/missing').status_code==404


def test_legacy_migration_and_explicit_assignment(tmp_path):
    path=tmp_path/'legacy.sqlite3'
    db=sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE transactions(id INTEGER PRIMARY KEY,description TEXT NOT NULL,amount INTEGER NOT NULL,type TEXT NOT NULL,category TEXT NOT NULL,date TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',seed_key TEXT UNIQUE);
    CREATE TABLE budgets(id INTEGER PRIMARY KEY,month TEXT NOT NULL,category TEXT NOT NULL,amount INTEGER NOT NULL,UNIQUE(month,category));
    CREATE TABLE settings(id INTEGER PRIMARY KEY,currency TEXT NOT NULL,compact INTEGER NOT NULL);
    INSERT INTO settings VALUES(1,'INR',1);
    INSERT INTO transactions(id,description,amount,type,category,date) VALUES(1,'Legacy expense',500,'expense','Food','2026-10-01');
    INSERT INTO budgets VALUES(1,'2026-10','Food',1000);
    PRAGMA user_version=1;
    """)
    db.close()
    app=create_app(dict(TESTING=True,SECRET_KEY='test',DATABASE=str(path),WTF_CSRF_ENABLED=False))
    client=app.test_client()
    register(client)
    login(client)
    assert client.get('/api/summary?month=2026-10').json['expenses']==0
    result=app.test_cli_runner().invoke(args=['assign-legacy-data','--email','new@example.com'])
    assert result.exit_code==0,result.output
    assert client.get('/api/summary?month=2026-10').json['expenses']==500
    assert client.get('/api/summary?month=2026-10').json['budget']==1000
    assert b'Legacy expense' in client.get('/transactions').data
    with app.app_context():
        assert get_db().execute('SELECT currency FROM user_settings').fetchone()[0]=='INR'
    assert app.test_cli_runner().invoke(args=['assign-legacy-data','--email','new@example.com']).exit_code==0


def test_per_user_seed(app,client):
    from app.services.finance_service import seed_demo
    other=app.test_client()
    register(other)
    with app.app_context():
        seed_demo(1)
        seed_demo(2)
        seed_demo(1)
        counts=get_db().execute('SELECT user_id,count(*) count FROM transactions GROUP BY user_id ORDER BY user_id').fetchall()
        assert [(row['user_id'],row['count']) for row in counts]==[(1,60),(2,60)]
    assert app.test_cli_runner().invoke(args=['seed-demo','--email','missing@example.com']).exit_code!=0
    assert app.test_cli_runner().invoke(args=['seed-demo','--email','new@example.com']).exit_code==0


def test_anonymous_writes_and_invalid_session(app,transaction):
    client=app.test_client()
    for path,data in [('/transactions',transaction),('/transactions/1/delete',{}),('/budgets',dict(month='2026-10',category='Food',amount='10')),('/settings',dict(currency='USD'))]:
        assert client.post(path,data=data).location.endswith('/login')
    with client.session_transaction() as session:
        session['user_id']=9999
    assert client.get('/api/summary').status_code==401
    with app.app_context():
        assert get_db().execute('SELECT count(*) FROM transactions').fetchone()[0]==0
