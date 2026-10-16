from datetime import date
from decimal import Decimal,InvalidOperation
from database import get_db
from app.auth import owner_id,preferences
EXPENSE=['Food','Transport','Housing','Shopping','Healthcare','Education','Entertainment','Utilities','Other']
INCOME=['Salary','Freelance','Business','Investment','Gift','Other']

def money(value):
    currency=preferences()['currency']
    whole,minor=divmod(abs(value),100)
    grouped=f'{whole:,}'
    if currency=='INR' and whole>=1000:
        digits=str(whole)
        tail=digits[-3:]
        head=digits[:-3]
        groups=[]
        while head:
            groups.insert(0,head[-2:])
            head=head[:-2]
        grouped=','.join(groups+[tail])
    symbol={'GBP':'\u00a3','USD':'$','INR':'\u20b9'}[currency]
    return f"{'-' if value<0 else ''}{symbol}{grouped}.{minor:02d}"


def month_now(): return date.today().strftime('%Y-%m')

def valid_month(value):
    try:
        if len(value)!=7 or date.fromisoformat(value+'-01').isoformat()[:7]!=value: raise ValueError()
    except (ValueError,TypeError): raise ValueError('Choose a valid month.')
    return value

def amount_cents(value):
    try:
        amount=Decimal(str(value))
        if not amount.is_finite() or amount<=0 or amount>Decimal('999999999.99') or amount.as_tuple().exponent < -2: raise ValueError()
        return int(amount*100)
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError('Enter a positive amount with at most two decimal places (maximum 999,999,999.99).')

def validate_transaction(form):
    description=form.get('description','').strip()
    if not description or len(description)>160: raise ValueError('Enter a description of 1-160 characters.')
    kind=form.get('type')
    if kind not in ('income','expense'): raise ValueError('Choose income or expense.')
    category=form.get('category')
    if category not in (INCOME if kind=='income' else EXPENSE): raise ValueError('Choose a category matching the transaction type.')
    day=form.get('date','')
    try:
        if date.fromisoformat(day).isoformat()!=day: raise ValueError()
    except ValueError: raise ValueError('Enter a valid date in YYYY-MM-DD format.')
    notes=form.get('notes','').strip()
    if len(notes)>2000: raise ValueError('Notes must be 2,000 characters or fewer.')
    return dict(description=description,amount=amount_cents(form.get('amount')),type=kind,category=category,date=day,notes=notes)

def budgets_for(month):
    return get_db().execute("""SELECT b.*,COALESCE(SUM(t.amount),0) spent FROM budgets b LEFT JOIN transactions t ON t.type='expense' AND t.user_id=b.user_id AND t.category=b.category AND substr(t.date,1,7)=b.month WHERE b.month=? AND b.user_id=? GROUP BY b.id ORDER BY b.category""",(month,owner_id())).fetchall()

def summary(month):
    db=get_db()
    totals=dict(db.execute('SELECT type,SUM(amount) FROM transactions WHERE user_id=? GROUP BY type',(owner_id(),)).fetchall())
    monthly=dict(db.execute('SELECT type,SUM(amount) FROM transactions WHERE substr(date,1,7)=? AND user_id=? GROUP BY type',(month,owner_id())).fetchall())
    budget=db.execute('SELECT COALESCE(SUM(amount),0) FROM budgets WHERE month=? AND user_id=?',(month,owner_id())).fetchone()[0]
    expense=monthly.get('expense',0)
    return dict(income=totals.get('income',0),expenses=totals.get('expense',0),balance=totals.get('income',0)-totals.get('expense',0),monthly_income=monthly.get('income',0),monthly_expenses=expense,budget=budget,remaining=budget-expense,month=month)

def chart_data(month):
    db=get_db()
    cats=db.execute("SELECT category,SUM(amount) amount FROM transactions WHERE type='expense' AND substr(date,1,7)=? AND user_id=? GROUP BY category ORDER BY amount DESC,category",(month,owner_id())).fetchall()
    year,m=map(int,month.split('-'))
    months=[]
    for offset in range(5,-1,-1):
        index=year*12+m-1-offset
        if index<12: continue
        months.append(f'{index//12:04d}-{index%12+1:02d}')
    rows=db.execute('SELECT substr(date,1,7) month,type,SUM(amount) amount FROM transactions WHERE substr(date,1,7)>=? AND substr(date,1,7)<=? AND user_id=? GROUP BY month,type',(months[0],month,owner_id())).fetchall()
    lookup={(r['month'],r['type']):r['amount'] for r in rows}
    daily=db.execute('SELECT date,type,SUM(amount) amount FROM transactions WHERE substr(date,1,7)=? AND user_id=? GROUP BY date,type ORDER BY date',(month,owner_id())).fetchall()
    days=sorted(set(r['date'] for r in daily))
    daily_lookup={(r['date'],r['type']):r['amount'] for r in daily}
    return dict(unit='minor',categories=dict(labels=[r['category'] for r in cats],values=[r['amount'] for r in cats]),monthly=dict(labels=months,income=[lookup.get((v,'income'),0) for v in months],expense=[lookup.get((v,'expense'),0) for v in months]),daily=dict(labels=days,income=[daily_lookup.get((v,'income'),0) for v in days],expense=[daily_lookup.get((v,'expense'),0) for v in days]))

def seed_demo(user_id):
    db=get_db()
    today=date.today()
    for offset in range(6):
        index=today.year*12+today.month-1-offset
        month=f'{index//12:04d}-{index%12+1:02d}'
        examples=[('Salary',420000,'income','Salary',1),('Studio freelance',48000+offset*2500,'income','Freelance',5),('Apartment rent',125000,'expense','Housing',2),('Weekly groceries',16450+offset*300,'expense','Food',6),('City transport',8200,'expense','Transport',8),('Design books',6900,'expense','Education',10),('Dinner with friends',7800,'expense','Food',12),('Electricity and internet',14500,'expense','Utilities',13),('Weekend cinema',3200,'expense','Entertainment',14),('Wardrobe essentials',18400,'expense','Shopping',15)]
        for i,(desc,amount,kind,category,day) in enumerate(examples):
            if offset==0: day=min(day,today.day)
            db.execute('INSERT OR IGNORE INTO transactions(description,amount,type,category,date,notes,seed_key,user_id) VALUES(?,?,?,?,?,?,?,?)',('[Demo] '+desc,amount,kind,category,f'{month}-{day:02d}','Fictional sample data; remove freely.',f'demo-{user_id}-{month}-{i}',user_id))
    for category,amount in [('Housing',140000),('Food',40000),('Transport',15000),('Shopping',15000),('Utilities',20000),('Entertainment',10000)]:
        db.execute('INSERT OR IGNORE INTO budgets(month,category,amount,user_id) VALUES(?,?,?,?)',(today.strftime('%Y-%m'),category,amount,user_id))
    db.commit()
