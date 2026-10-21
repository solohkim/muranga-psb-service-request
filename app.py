import os
import re
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "muranga-psb-2026-secret-FIX-THIS-IN-RENDER")
BASE_UPLOAD = '/tmp/uploads' if os.environ.get('RENDER') else 'static/uploads'
app.config['UPLOAD_FOLDER'] = BASE_UPLOAD
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
ALLOWED_EXT = {'png','jpg','jpeg'}
DATABASE = 'database.db'
DEVELOPER_NAME = "soloh_kim"
COPYRIGHT_YEAR = "2026"

# --- FIX 1: FAVICON - stop crash ---
@app.route('/favicon.ico')
def favicon():
    return '', 204

def get_db():
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row
        return db

def get_cursor(db):
    if IS_POSTGRES:
        return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return db.cursor()

def q(sql):
    return sql.replace("?", "%s") if IS_POSTGRES else sql

def init_db():
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs('static/uploads', exist_ok=True)
        db = get_db()
        cur = get_cursor(db)
        if IS_POSTGRES:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                id_number TEXT, email TEXT UNIQUE NOT NULL,
                phone TEXT, password TEXT NOT NULL,
                role TEXT DEFAULT 'citizen', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id SERIAL PRIMARY KEY, user_id INTEGER,
                category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL,
                image_path TEXT, status TEXT DEFAULT 'Pending', admin_remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );""")
            db.commit()
            cur.execute("SELECT * FROM users WHERE email=%s", ('admin@muranga.go.ke',))
            if not cur.fetchone():
                cur.execute("INSERT INTO users (full_name, email, password, role) VALUES (%s,%s,%s,%s)",
                           ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
                db.commit()
            cur.close(); db.close()
        else:
            with sqlite3.connect(DATABASE) as sdb:
                sdb.executescript("""
                CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, id_number TEXT, email TEXT UNIQUE NOT NULL, phone TEXT, password TEXT NOT NULL, role TEXT DEFAULT 'citizen', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL, image_path TEXT, status TEXT DEFAULT 'Pending', admin_remarks TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id));
                """)
                cur2 = sdb.execute("SELECT * FROM users WHERE email='admin@muranga.go.ke'")
                if not cur2.fetchone():
                    sdb.execute("INSERT INTO users (full_name, email, password, role) VALUES (?,?,?,?)",
                               ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
                sdb.commit()
    except Exception as e:
        print(f"INIT DB ERROR (will retry on request): {e}")
        traceback.print_exc()

# --- FIX 2: Don't init DB at import crash ---
# Only init once, safely
try:
    init_db()
except:
    pass

# ... [ KEEP ALL YOUR OTHER ROUTES EXACTLY AS YOU HAVE THEM - login, register, dashboard, etc ] ...

# PASTE YOUR EXISTING ROUTES HERE FROM @app.context_processor to admin_users

# --- FIX 3: THIS IS THE MAIN FIX ---
@app.errorhandler(Exception)
def handle_exception(e):
    # Let normal 404s stay 404, don't turn them into 500
    if isinstance(e, HTTPException):
        return e
    tb = traceback.format_exc()
    print("=== UNHANDLED EXCEPTION ===")
    print(tb)
    return f"<html><body style='padding:20px;font-family:monospace'><h2 style='color:red'>REAL ERROR:</h2><p>{e}</p><pre style='background:#000;color:#0f0;padding:15px;white-space:pre-wrap'>{tb}</pre><a href='/dashboard'>Back</a></body></html>", 500

if __name__=='__main__':
    app.run(debug=True)