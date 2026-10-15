import os
import secrets
import sqlite3
from pathlib import Path
import click
from flask import Flask,render_template,jsonify,request,g
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect,CSRFError
from database import init_db,close_db,get_db
csrf=CSRFProtect()

def create_app(test_config=None):
    app=Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),DATABASE=os.environ.get('DATABASE_PATH',str(Path(app.instance_path)/'lume.sqlite3')),APP_VERSION=os.environ.get('APP_VERSION','1.0.0'),MAX_CONTENT_LENGTH=65536,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax')
    if test_config: app.config.update(test_config)
    app.config['PERMANENT_SESSION_LIFETIME']=timedelta(hours=12)
    csrf.init_app(app)
    app.teardown_appcontext(close_db)
    from app.routes import bp
    from app.services.finance_service import money,EXPENSE,INCOME
    app.register_blueprint(bp)
    from app.auth import bp as auth_bp,load_user,preferences
    app.register_blueprint(auth_bp)
    app.before_request(load_user)
    app.jinja_env.filters['money']=money
    with app.app_context(): init_db()
    @app.context_processor
    def shared():
        return dict(preferences=preferences(),current_user=getattr(g,'user',None),expense_categories=EXPENSE,income_categories=INCOME)
    @app.after_request
    def headers(response):
        if getattr(g,'user',None) is not None or request.endpoint in ('auth.login','auth.register'):
            response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        return response
    def error_response(code,message):
        if request.path.startswith('/api/') or request.path=='/health': return jsonify(error=message),code
        return render_template('error.html',code=code,message=message),code
    @app.errorhandler(404)
    def missing(error): return error_response(404,'We could not find that page or record.')
    @app.errorhandler(400)
    def bad_request(error): return error_response(400,'Invalid request. Check the supplied dates and form values.')
    @app.errorhandler(CSRFError)
    def csrf_error(error): return error_response(400,'Your form expired. Refresh the page and try again.')
    @app.errorhandler(413)
    def too_large(error): return error_response(413,'The submitted form is too large.')
    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        db=g.get('db')
        if db is not None:
            try: db.rollback()
            except sqlite3.Error: pass
        app.logger.error('Database operation failed (%s)',type(error).__name__)
        # Avoid querying settings again when storage is unavailable.
        return jsonify(error='Storage temporarily unavailable. Please try again.'),503
    @app.errorhandler(500)
    def internal(error): return error_response(500,'Something went wrong. Please try again.')
    @app.cli.command('init-db')
    def init_command():
        init_db()
        click.echo('Database initialised; existing data preserved.')
    @app.cli.command('seed-demo')
    @click.option('--email',required=True,help='Registered account to receive fictional records.')
    def seed_command(email):
        from app.services.finance_service import seed_demo
        user=get_db().execute('SELECT id FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        if user is None: raise click.ClickException('Register this account in the browser first.')
        seed_demo(user['id'])
        click.echo('Fictional demo records loaded. Safe to run again.')
    @app.cli.command('assign-legacy-data')
    @click.option('--email',required=True,help='Registered owner of the original single-user data.')
    def assign_legacy(email):
        db=get_db()
        user=db.execute('SELECT id FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        if user is None: raise click.ClickException('Register this account in the browser first.')
        uid=user['id']
        try:
            transactions=db.execute('UPDATE transactions SET user_id=? WHERE user_id IS NULL',(uid,)).rowcount
            budgets=db.execute('UPDATE budgets SET user_id=? WHERE user_id IS NULL',(uid,)).rowcount
            if transactions or budgets:
                db.execute('UPDATE user_settings SET currency=(SELECT currency FROM settings WHERE id=1),compact=(SELECT compact FROM settings WHERE id=1) WHERE user_id=?',(uid,))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise click.ClickException('A category budget conflicts with an existing budget. Remove the conflicting budget before importing; no data was changed.')
        click.echo(f'Assigned {transactions} transactions and {budgets} budgets to {email}.')
    return app
