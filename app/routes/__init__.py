from datetime import date
from flask import Blueprint,render_template,request,redirect,url_for,flash,jsonify,abort,current_app
from database import get_db
from app.auth import owner_id
from app.services.finance_service import summary,chart_data,budgets_for,month_now,valid_month,validate_transaction,amount_cents,EXPENSE
bp=Blueprint('main',__name__)

def selected_month():
    try: return valid_month(request.args.get('month',month_now()))
    except ValueError: abort(400)

@bp.get('/health')
def health():
    get_db().execute('SELECT 1').fetchone()
    return jsonify(status='healthy',application='Lume Finance',version=current_app.config['APP_VERSION'])

@bp.get('/dashboard')
def dashboard():
    month=selected_month()
    recent=get_db().execute('SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC,id DESC LIMIT 6',(owner_id(),)).fetchall()
    return render_template('dashboard.html',summary=summary(month),recent=recent,month=month)

@bp.get('/api/summary')
def api_summary(): return jsonify(summary(selected_month()))

@bp.get('/api/charts')
def api_charts(): return jsonify(chart_data(selected_month()))

@bp.route('/transactions',methods=['GET','POST'])
def transactions():
    db=get_db()
    if request.method=='POST':
        try:
            data=validate_transaction(request.form); data['user_id']=owner_id()
            db.execute('INSERT INTO transactions(description,amount,type,category,date,notes,user_id) VALUES(:description,:amount,:type,:category,:date,:notes,:user_id)',data)
            db.commit()
            flash('Transaction added.','success')
            return redirect(url_for('main.transactions'))
        except ValueError as error:
            return render_template('transaction_form.html',transaction=request.form,error=str(error),editing=False,today=date.today().isoformat()),400
    clauses,params=['user_id=?'],[owner_id()]
    for key,column in [('q','description'),('category','category'),('type','type'),('start','date'),('end','date')]:
        value=request.args.get(key,'').strip()
        if value:
            if key in ('start','end'):
                try: date.fromisoformat(value)
                except ValueError: abort(400)
            if key=='q':
                clauses.append('instr(lower(description),lower(?))>0')
            else: clauses.append(column+('>=?' if key=='start' else '<=?' if key=='end' else '=?'))
            params.append(value)
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    sort={'date_desc':'date DESC,id DESC','date_asc':'date ASC,id ASC','amount_desc':'amount DESC,id DESC','amount_asc':'amount ASC,id ASC'}.get(request.args.get('sort'),'date DESC,id DESC')
    try: page=max(1,int(request.args.get('page',1)))
    except ValueError: page=1
    count=db.execute('SELECT COUNT(*) FROM transactions'+where,params).fetchone()[0]
    pages=max(1,(count+14)//15)
    page=min(page,pages)
    rows=db.execute('SELECT * FROM transactions'+where+' ORDER BY '+sort+' LIMIT 15 OFFSET ?',params+[(page-1)*15]).fetchall()
    def page_url(number):
        args=request.args.to_dict(); args['page']=number
        return url_for('main.transactions',**args)
    return render_template('transactions.html',transactions=rows,count=count,page=page,pages=pages,page_url=page_url)

@bp.get('/transactions/new')
def new_transaction(): return render_template('transaction_form.html',transaction={},editing=False,today=date.today().isoformat())

@bp.route('/transactions/<int:transaction_id>/edit',methods=['GET','POST'])
def edit_transaction(transaction_id):
    db=get_db()
    row=db.execute('SELECT * FROM transactions WHERE id=? AND user_id=?',(transaction_id,owner_id())).fetchone()
    if row is None: abort(404)
    if request.method=='POST':
        try:
            data=validate_transaction(request.form); data['user_id']=owner_id(); data['id']=transaction_id
            db.execute('UPDATE transactions SET description=:description,amount=:amount,type=:type,category=:category,date=:date,notes=:notes WHERE id=:id AND user_id=:user_id',data)
            db.commit(); flash('Transaction updated.','success')
            return redirect(url_for('main.transactions'))
        except ValueError as error:
            return render_template('transaction_form.html',transaction=request.form,editing=True,error=str(error)),400
    data=dict(row); data['amount']=f"{row['amount']/100:.2f}"
    return render_template('transaction_form.html',transaction=data,editing=True)

@bp.post('/transactions/<int:transaction_id>/delete')
def delete_transaction(transaction_id):
    cursor=get_db().execute('DELETE FROM transactions WHERE id=? AND user_id=?',(transaction_id,owner_id()))
    if cursor.rowcount==0: abort(404)
    get_db().commit(); flash('Transaction deleted.','success')
    return redirect(url_for('main.transactions'))

@bp.route('/budgets',methods=['GET','POST'])
def budgets():
    month=selected_month(); error=None
    if request.method=='POST':
        try:
            month=valid_month(request.form.get('month',''))
            category=request.form.get('category')
            if category not in EXPENSE: raise ValueError('Choose an expense category.')
            amount=amount_cents(request.form.get('amount'))
            get_db().execute('INSERT INTO budgets(month,category,amount,user_id) VALUES(?,?,?,?) ON CONFLICT(user_id,month,category) DO UPDATE SET amount=excluded.amount',(month,category,amount,owner_id()))
            get_db().commit(); flash('Budget saved.','success')
            return redirect(url_for('main.budgets',month=month))
        except ValueError as exc: error=str(exc); month=selected_month()
    return render_template('budgets.html',budgets=budgets_for(month),month=month,summary=summary(month),error=error),400 if error else 200

@bp.post('/budgets/<int:budget_id>/delete')
def delete_budget(budget_id):
    row=get_db().execute('SELECT * FROM budgets WHERE id=? AND user_id=?',(budget_id,owner_id())).fetchone()
    if row is None: abort(404)
    get_db().execute('DELETE FROM budgets WHERE id=? AND user_id=?',(budget_id,owner_id())); get_db().commit()
    flash('Budget removed.','success')
    return redirect(url_for('main.budgets',month=row['month']))

@bp.get('/analytics')
def analytics():
    month=selected_month()
    return render_template('analytics.html',month=month,summary=summary(month))

@bp.route('/settings',methods=['GET','POST'])
def settings():
    error=None
    if request.method=='POST':
        currency=request.form.get('currency')
        if currency not in ('GBP','USD','INR'): error='Choose a supported currency.'
        else:
            get_db().execute('UPDATE user_settings SET currency=?,compact=? WHERE user_id=?',(currency,int(request.form.get('compact')=='on'),owner_id()))
            get_db().commit(); flash('Preferences saved.','success')
            return redirect(url_for('main.settings'))
    return render_template('settings.html',error=error),400 if error else 200
