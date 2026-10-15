import pytest
from app import create_app
from database import get_db
from werkzeug.security import generate_password_hash
TEST_HASH=generate_password_hash("test-password-123")

@pytest.fixture
def app(tmp_path):
    application = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret', 'DATABASE': str(tmp_path / 'test.sqlite3'), 'WTF_CSRF_ENABLED': False})
    with application.app_context():
        get_db().execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)',('Test User','test@example.com',TEST_HASH))
        get_db().execute('INSERT INTO user_settings(user_id) VALUES(1)')
        get_db().commit()
    return application

@pytest.fixture
def client(app):
    client=app.test_client()
    with client.session_transaction() as session:
        session['user_id']=1
    return client

@pytest.fixture
def transaction():
    return dict(description='Test groceries', amount='12.34', type='expense', category='Food', date='2026-10-10', notes='A note')
