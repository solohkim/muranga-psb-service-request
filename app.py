import os
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

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
app.secret_key = os.environ.get("SECRET_KEY", "muranga-psb-2026-secret")
BASE_UPLOAD = '/tmp/uploads' if os.environ.get('RENDER') else 'static/uploads'
app.config['UPLOAD_FOLDER'] = BASE_UPLOAD
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
ALLOWED_EXT = {'png','jpg','jpeg'}
DATABASE = 'database.db'
DEVELOPER_NAME = "soloh_kim"
COPYRIGHT_YEAR = "2026"

def get_db():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
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
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id SERIAL PRIMARY KEY, user_id INTEGER,
            category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL,
            image_path TEXT, status TEXT DEFAULT 'Pending', admin_remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        db.commit()
        cur.execute("SELECT * FROM users WHERE email=%s", ('admin@muranga.go.ke',))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (full_name, email, password, role) VALUES (%s,%s,%s,%s)",
                       ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
            db.commit()
        cur.close()
        db.close()
    else:
        with sqlite3.connect(DATABASE) as sdb:
            sdb.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                id_number TEXT, email TEXT UNIQUE NOT NULL,
                phone TEXT, password TEXT NOT NULL,
                role TEXT DEFAULT 'citizen', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL,
                image_path TEXT, status TEXT DEFAULT 'Pending', admin_remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """)
            cur2 = sdb.execute("SELECT * FROM users WHERE email='admin@muranga.go.ke'")
            if not cur2.fetchone():
                sdb.execute("INSERT INTO users (full_name, email, password, role) VALUES (?,?,?,?)",
                           ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
            sdb.commit()

init_db()

@app.context_processor
def inject_copyright():
    return dict(developer_name=DEVELOPER_NAME, copyright_year=COPYRIGHT_YEAR)

@app.teardown_appcontext
def close_connection(exception):
    if not IS_POSTGRES:
        db = getattr(g, '_database', None)
        if db is not None: db.close()

def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXT

@app.before_request
def check_session_timeout():
    if request.endpoint in ('login', 'register', 'static', 'home', 'forgot_password', None):
        return
    if 'user_id' in session:
        session.permanent = True
        last_active = session.get('last_active')
        now = datetime.now()
        if last_active:
            try:
                last_time = datetime.fromisoformat(last_active)
                if now - last_time > timedelta(minutes=15):
                    session.clear()
                    flash("Session expired due to inactivity (15 min). Please login again.", "warning")
                    return redirect(url_for('login'))
            except: pass
        session['last_active'] = now.isoformat()

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        db = get_db(); cur = get_cursor(db)
        email = request.form['email'].strip().lower()
        full_name = request.form['full_name'].strip()
        id_number = request.form['id_number'].strip()
        phone = request.form['phone'].strip()
        password = request.form['password']
        if not full_name.replace(' ','').isalpha():
            flash("Full Name must contain letters only", "danger")
            return render_template('register.html')
        if not id_number.isdigit() or len(id_number) not in (7,8):
            flash("ID Number must be 7 or 8 digits", "danger")
            return render_template('register.html')
        if not (phone.isdigit() and len(phone)==10 and phone.startswith('07')):
            flash("Phone must be 10 digits starting with 07", "danger")
            return render_template('register.html')
        cur.execute(q("SELECT id FROM users WHERE LOWER(email)=?"), (email,))
        if cur.fetchone():
            flash("Email already exists!", "danger")
            if IS_POSTGRES: cur.close(); db.close()
            return render_template('register.html')
        try:
            cur.execute(q("INSERT INTO users (full_name, id_number, email, phone, password) VALUES (?,?,?,?,?)"),
                       (full_name, id_number, email, phone, generate_password_hash(password)))
            db.commit()
            flash("Registration successful! Please login.", "success")
            if IS_POSTGRES: cur.close(); db.close()
            return redirect(url_for('login'))
        except Exception as e:
            if IS_POSTGRES: db.rollback()
            flash(f"Error: {str(e)}", "danger")
            if IS_POSTGRES: cur.close(); db.close()
            return render_template('register.html')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        db = get_db(); cur = get_cursor(db)
        cur.execute(q("SELECT * FROM users WHERE email=?"), (request.form['email'].strip().lower(),))
        user = cur.fetchone()
        if IS_POSTGRES: cur.close(); db.close()
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id']=user['id']; session['role']=user['role']; session['full_name']=user['full_name']
            session.permanent=True; session['last_active']=datetime.now().isoformat()
            return redirect(url_for('admin_dashboard' if user['role']=='admin' else 'citizen_dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template('forgot_password.html')
        if len(new_password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return render_template('forgot_password.html')
        db = get_db(); cur = get_cursor(db)
        cur.execute(q("SELECT * FROM users WHERE email=?"), (email,))
        user = cur.fetchone()
        if not user:
            flash("No account found with that email", "danger")
            if IS_POSTGRES: cur.close(); db.close()
            return render_template('forgot_password.html')
        cur.execute(q("UPDATE users SET password=? WHERE email=?"), (generate_password_hash(new_password), email))
        db.commit()
        if IS_POSTGRES: cur.close(); db.close()
        flash("Password reset successful!", "success")
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
def citizen_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    db=get_db(); cur=get_cursor(db)
    try:
        cur.execute(q("SELECT * FROM requests WHERE user_id=? ORDER BY created_at DESC"), (session['user_id'],))
        reqs=cur.fetchall()
    except Exception as e:
        print(f"DASHBOARD ERROR: {e}")
        reqs=[]
    if IS_POSTGRES: cur.close(); db.close()
    stats={'total':len(reqs),'pending':len([r for r in reqs if r['status']=='Pending']),'inprogress':len([r for r in reqs if r['status']=='In Progress']),'resolved':len([r for r in reqs if r['status']=='Resolved'])}
    return render_template('dashboard.html', requests=reqs, stats=stats)

# --- FIXED SUBMIT ROUTES - WILL NOT COLLAPSE ---
@app.route('/submit', methods=['GET','POST'])
def submit_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            image_path=None
            try:
                file=request.files.get('image')
                if file and file.filename!='' and allowed_file(file.filename):
                    filename=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(save_path)
                    image_path=save_path
            except Exception as img_e:
                print(f"IMAGE SAVE IGNORED: {img_e}")
            
            db=get_db(); cur=get_cursor(db)
            category = request.form.get('category') or request.form.get('service') or 'General'
            location = request.form.get('location') or request.form.get('ward') or 'Kiharu'
            description = request.form.get('description') or request.form.get('details') or 'No description'
            
            cur.execute(q("INSERT INTO requests (user_id, category, location, description, image_path) VALUES (?,?,?,?,?)"),
                             (session['user_id'], category, location, description, image_path))
            db.commit()
            if IS_POSTGRES: cur.close(); db.close()
            flash("Request submitted successfully!", "success")
            return redirect(url_for('citizen_dashboard'))
        except Exception as e:
            traceback.print_exc()
            flash(f"Submission failed: {e}", "danger")
            return redirect(url_for('citizen_dashboard'))
    return render_template('submit_request.html')

@app.route('/new_request', methods=['GET','POST'])
def new_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            image_path=None
            try:
                file=request.files.get('image')
                if file and file.filename!='' and allowed_file(file.filename):
                    filename=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path=os.path.join(app.config['UPLOAD_FOLDER'], filename)
            except Exception as img_e:
                print(f"IMAGE SAVE IGNORED: {img_e}")

            category = request.form.get('category','General')
            location = request.form.get('location') or request.form.get('ward') or 'Kiharu'
            description = request.form.get('description','')
            
            db = get_db(); cur=get_cursor(db)
            cur.execute(q("INSERT INTO requests (user_id, category, location, description, image_path) VALUES (?,?,?,?,?)"),
                       (session['user_id'], category, location, description, image_path))
            db.commit()
            if IS_POSTGRES: cur.close(); db.close()
            flash("Request submitted successfully!", "success")
            return redirect(url_for('citizen_dashboard'))
        except Exception as e:
            traceback.print_exc()
            flash(f"Error submitting: {e}", "danger")
            return redirect(url_for('citizen_dashboard'))
    try: return render_template('new_request.html')
    except: return render_template('submit_request.html')

@app.route('/citizen/request/<int:req_id>/edit', methods=['GET','POST'])
def edit_citizen_request(req_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cur=get_cursor(db)
    cur.execute(q("SELECT * FROM requests WHERE id=? AND user_id=?"), (req_id, session['user_id']))
    req = cur.fetchone()
    if not req:
        flash("Request not found", "danger")
        if IS_POSTGRES: cur.close(); db.close()
        return redirect(url_for('citizen_dashboard'))
    if req['status'] != 'Pending' and request.method == 'GET':
        flash("Only Pending requests can be edited", "warning")
        if IS_POSTGRES: cur.close(); db.close()
        return redirect(url_for('citizen_dashboard'))
    if request.method == 'POST':
        cur.execute(q("UPDATE requests SET category=?, location=?, description=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"),
                   (request.form.get('category', req['category']), request.form.get('location', req['location']), request.form.get('description', req['description']), req_id, session['user_id']))
        db.commit()
        if IS_POSTGRES: cur.close(); db.close()
        flash("Request updated!", "success")
        return redirect(url_for('citizen_dashboard'))
    if IS_POSTGRES: cur.close(); db.close()
    return render_template('edit_request.html', req=req)

@app.route('/admin')
def admin_dashboard():
    if session.get('role')!='admin': return redirect(url_for('login'))
    db=get_db(); cur=get_cursor(db)
    status_filter = request.args.get('status', 'All')
    if status_filter == 'All' or not status_filter:
        cur.execute("SELECT r.*, u.full_name, u.phone FROM requests r LEFT JOIN users u ON r.user_id=u.id ORDER BY r.created_at DESC")
    else:
        cur.execute(q("SELECT r.*, u.full_name, u.phone FROM requests r LEFT JOIN users u ON r.user_id=u.id WHERE r.status=? ORDER BY r.created_at DESC"), (status_filter,))
    all_reqs = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS count FROM requests")
    total_row=cur.fetchone()
    total=total_row['count'] if IS_POSTGRES else total_row[0]
    cur.execute("SELECT COUNT(*) AS count FROM requests WHERE status='Pending'")
    row=cur.fetchone()
    pending=row['count'] if IS_POSTGRES else row[0]
    cur.execute("SELECT COUNT(*) AS count FROM requests WHERE status='In Progress'")
    row=cur.fetchone()
    inprog=row['count'] if IS_POSTGRES else row[0]
    cur.execute("SELECT COUNT(*) AS count FROM requests WHERE status='Resolved'")
    row=cur.fetchone()
    resolved=row['count'] if IS_POSTGRES else row[0]
    cur.execute("SELECT category, COUNT(*) as c FROM requests GROUP BY category")
    by_category=cur.fetchall()
    if IS_POSTGRES: cur.close(); db.close()
    return render_template('admin_dashboard.html', requests=all_reqs, total=total, pending=pending, inprog=inprog, resolved=resolved, by_category=by_category, current_filter=status_filter)

@app.route('/admin/update/<int:req_id>', methods=['POST'])
def update_request(req_id):
    if session.get('role')!='admin': return redirect(url_for('login'))
    db=get_db(); cur=get_cursor(db)
    cur.execute(q("UPDATE requests SET status=?, admin_remarks=?, updated_at=CURRENT_TIMESTAMP WHERE id=?"),
               (request.form['status'], request.form['admin_remarks'], req_id))
    db.commit()
    if IS_POSTGRES: cur.close(); db.close()
    flash("Updated!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:req_id>/delete', methods=['POST'])
def delete_request(req_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = get_db(); cur=get_cursor(db)
    cur.execute(q("DELETE FROM requests WHERE id=?"), (req_id,))
    db.commit()
    if IS_POSTGRES: cur.close(); db.close()
    flash(f"Request #{req_id} deleted", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = get_db(); cur=get_cursor(db)
    cur.execute("""
        SELECT u.*, 
        (SELECT COUNT(*) FROM requests WHERE user_id=u.id) as total_requests,
        (SELECT COUNT(*) FROM requests WHERE user_id=u.id AND status='Pending') as pending,
        (SELECT COUNT(*) FROM requests WHERE user_id=u.id AND status='Resolved') as resolved
        FROM users u ORDER BY u.created_at DESC
    """)
    users=cur.fetchall()
    cur.execute("SELECT COUNT(*) AS count FROM users WHERE role='citizen'")
    total_users_row = cur.fetchone()
    total_users = total_users_row['count'] if IS_POSTGRES else total_users_row[0]
    if IS_POSTGRES: cur.close(); db.close()
    return render_template('admin_users.html', users=users, total_users=total_users)

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = get_db(); cur=get_cursor(db)
    cur.execute(q("DELETE FROM requests WHERE user_id=?"), (user_id,))
    cur.execute(q("DELETE FROM users WHERE id=? AND role='citizen'"), (user_id,))
    db.commit()
    if IS_POSTGRES: cur.close(); db.close()
    flash(f"User #{user_id} deleted", "success")
    return redirect(url_for('admin_users'))

if __name__=='__main__':
    app.run(debug=True)