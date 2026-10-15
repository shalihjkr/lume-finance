import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db=sqlite3.connect(current_app.config['DATABASE'],timeout=10)
        g.db.row_factory=sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def close_db(error=None):
    db=g.pop('db',None)
    if db is not None: db.close()

def init_db():
    Path(current_app.config['DATABASE']).parent.mkdir(parents=True,exist_ok=True)
    db=get_db()
    # Future migrations should run in ascending user_version order, preserving data.
    if db.execute('PRAGMA user_version').fetchone()[0]<1:
        db.executescript("""BEGIN;
        CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,description TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),type TEXT NOT NULL CHECK(type IN ('income','expense')),category TEXT NOT NULL,date TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',seed_key TEXT UNIQUE);
        CREATE INDEX IF NOT EXISTS tx_date ON transactions(date);
        CREATE TABLE IF NOT EXISTS budgets(id INTEGER PRIMARY KEY,month TEXT NOT NULL,category TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),UNIQUE(month,category));
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),currency TEXT NOT NULL DEFAULT 'GBP',compact INTEGER NOT NULL DEFAULT 0);
        INSERT OR IGNORE INTO settings(id) VALUES(1);
        PRAGMA user_version=1;
        COMMIT;""")

    if db.execute('PRAGMA user_version').fetchone()[0]<2:
        # Existing records remain unassigned until the local owner explicitly imports them.
        db.executescript("""BEGIN;
        CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id);
        CREATE INDEX tx_owner_date ON transactions(user_id,date);
        ALTER TABLE budgets RENAME TO budgets_v1;
        CREATE TABLE budgets(id INTEGER PRIMARY KEY,month TEXT NOT NULL,category TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),user_id INTEGER REFERENCES users(id),UNIQUE(user_id,month,category));
        INSERT INTO budgets(id,month,category,amount) SELECT id,month,category,amount FROM budgets_v1;
        DROP TABLE budgets_v1;
        CREATE TABLE user_settings(user_id INTEGER PRIMARY KEY REFERENCES users(id),currency TEXT NOT NULL DEFAULT 'GBP',compact INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE login_attempts(identity TEXT PRIMARY KEY,attempts INTEGER NOT NULL,window_start INTEGER NOT NULL);
        PRAGMA user_version=2;
        COMMIT;""")
