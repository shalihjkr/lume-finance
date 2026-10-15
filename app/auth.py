"""Account lifecycle, request authentication, and owner-scoped preferences."""
import re
import sqlite3
import time
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

bp = Blueprint('auth', __name__)
# Check a real hash even for unknown addresses, reducing timing differences.
DUMMY_HASH = generate_password_hash('not-an-account-password')


def owner_id():
    if getattr(g, 'user', None) is None:
        raise RuntimeError('An authenticated user is required.')
    return g.user['id']


def preferences():
    if getattr(g, 'user', None) is None:
        return dict(currency='GBP', compact=0)
    return dict(get_db().execute('SELECT * FROM user_settings WHERE user_id=?', (owner_id(),)).fetchone())


def load_user():
    g.user = None
    user_id = session.get('user_id')
    if user_id:
        g.user = get_db().execute('SELECT id,name,email FROM users WHERE id=?', (user_id,)).fetchone()
        if g.user is None:
            session.clear()
    if request.blueprint == 'main' and request.endpoint != 'main.health' and g.user is None:
        if request.path.startswith('/api/'):
            return jsonify(error='Please log in to continue.'), 401
        return redirect(url_for('auth.login'))


@bp.get('/')
def landing():
    return render_template('landing.html', articles=ARTICLES)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('main.dashboard'))
    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not 1 <= len(name) <= 80:
            error = 'Enter your name (up to 80 characters).'
        elif len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            error = 'Enter a valid email address.'
        elif not 12 <= len(password) <= 128:
            error = 'Use a password between 12 and 128 characters.'
        elif password != request.form.get('confirm_password'):
            error = 'Your passwords do not match.'
        else:
            db = get_db()
            try:
                cursor = db.execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)', (name,email,generate_password_hash(password)))
                db.execute('INSERT INTO user_settings(user_id) VALUES(?)', (cursor.lastrowid,))
                db.commit()
                session.clear()
                flash('Your account is ready. Log in to your new workspace.', 'success')
                return redirect(url_for('auth.login'))
            except sqlite3.IntegrityError:
                db.rollback()
                error = 'An account with this email already exists. Please log in.'
    return render_template('auth.html', registering=True, error=error), 400 if error else 200


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('main.dashboard'))
    error = None
    status = 200
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()[:254]
        password = request.form.get('password', '')
        db = get_db()
        now = int(time.time())
        # Persisted, shared across workers. Expired entries are removed on login.
        db.execute('DELETE FROM login_attempts WHERE window_start<=?', (now-900,))
        identity = email
        attempt = db.execute('SELECT * FROM login_attempts WHERE identity=?', (identity,)).fetchone()
        if attempt and attempt['attempts'] >= 8:
            db.commit()
            error, status = 'Too many attempts. Please try again in 15 minutes.', 429
        else:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
            valid = check_password_hash(user['password_hash'] if user else DUMMY_HASH, password[:128])
            if user and valid and len(password) <= 128:
                db.execute('DELETE FROM login_attempts WHERE identity=?', (identity,))
                db.commit()
                session.clear()
                session['user_id'] = user['id']
                session.permanent = True
                flash('Welcome back, '+user['name']+'.', 'success')
                return redirect(url_for('main.dashboard'))
            db.execute('INSERT INTO login_attempts(identity,attempts,window_start) VALUES(?,1,?) ON CONFLICT(identity) DO UPDATE SET attempts=attempts+1', (identity,now))
            db.commit()
            error, status = 'Email or password is incorrect.', 400
    return render_template('auth.html', registering=False, error=error), status


@bp.post('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.landing'))


ARTICLES = [
    dict(slug='a-budget-you-can-live-with', category='BUDGETING', title='A budget you can actually live with', intro='Build a spending plan around your real life, one category at a time.', sections=[('Start with what is real', 'Record a month of income and expenses before setting strict targets. Separate essential costs, flexible spending and occasional purchases so your plan reflects how you live.'), ('Give your categories some room', 'Choose limits for the categories you want to watch. In Lume, a category budget tracks actual spending and highlights when you approach or exceed its limit. Start with two or three categories and adjust as you learn.'), ('Review rather than restart', 'Check your plan weekly. An unexpected expense is useful information: adjust next month or reduce another category. A practical budget should support decisions, rather than make every purchase feel like a mistake.')]),
    dict(slug='small-expenses-clearer-picture', category='MONEY HABITS', title='Small expenses. A clearer picture.', intro='Find the everyday patterns that quietly shape your monthly spending.', sections=[('Capture the little things', 'A coffee, a subscription and a quick delivery may be easy to forget. Record them with clear descriptions and consistent categories to see their combined impact.'), ('Look for patterns', 'Use the spending mix and top category breakdown to see where your money goes. Compare months and consider one-off purchases before deciding that a category needs a lower limit.'), ('Change one habit', 'Pick one recurring cost to review, such as a subscription you rarely use. Small changes are easier to sustain when they serve a goal you care about.')]),
    dict(slug='your-monthly-money-reset', category='GETTING STARTED', title='Your 15-minute monthly money reset', intro='A simple routine to close one month and approach the next with clarity.', sections=[('Check the record', 'Review your transactions for missing entries, duplicate purchases and incorrect categories. Edit descriptions or add notes while the details are still fresh.'), ('Read the bigger picture', 'Compare monthly income and expenses, then review category budgets. Remember that changing the display currency only changes formatting: Lume does not convert exchange rates.'), ('Plan one next step', 'Choose one achievable adjustment for the coming month. Set the relevant category budget, keep recording your transactions and return to the same review next month.')])
]


@bp.get('/journal/<slug>')
def article(slug):
    from flask import abort
    post = next((item for item in ARTICLES if item['slug'] == slug), None)
    if post is None:
        abort(404)
    return render_template('article.html', article=post)
