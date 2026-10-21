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
app.secret_key = os.environ.get("SECRET_KEY", "muranga-psb-2026-secret-fixed-key-please-set-env")
BASE_UPLOAD = '/tmp/uploads' if os.environ.get('RENDER') else 'static/uploads'
app.config['UPLOAD_FOLDER'] = BASE_UPLOAD
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
ALLOWED_EXT = {'png','jpg','jpeg'}
DATABASE = 'database.db'
DEVELOPER_NAME = "soloh_kim"
COPYRIGHT_YEAR = "2026"

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
            cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, full_name TEXT NOT NULL, id_number TEXT, email TEXT UNIQUE NOT NULL, phone TEXT, password TEXT NOT NULL, role TEXT DEFAULT 'citizen', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
            cur.execute("CREATE TABLE IF NOT EXISTS requests (id SERIAL PRIMARY KEY, user_id INTEGER, category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL, image_path TEXT, status TEXT DEFAULT 'Pending', admin_remarks TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id));")
            db.commit()
            cur.execute("SELECT * FROM users WHERE email=%s", ('admin@muranga.go.ke',))
            if not cur.fetchone():
                cur.execute("INSERT INTO users (full_name, email, password, role) VALUES (%s,%s,%s,%s)", ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
                db.commit()
            cur.close(); db.close()
        else:
            with sqlite3.connect(DATABASE) as sdb:
                sdb.executescript("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, id_number TEXT, email TEXT UNIQUE NOT NULL, phone TEXT, password TEXT NOT NULL, role TEXT DEFAULT 'citizen', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL, image_path TEXT, status TEXT DEFAULT 'Pending', admin_remarks TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id));")
                cur2 = sdb.execute("SELECT * FROM users WHERE email='admin@muranga.go.ke'")
                if not cur2.fetchone():
                    sdb.execute("INSERT INTO users (full_name, email, password, role) VALUES (?,?,?,?)", ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
                sdb.commit()
    except Exception as e:
        print(f"INIT DB SKIPPED: {e}"); traceback.print_exc()
try:
    init_db()
except:
    pass

@app.context_processor
def inject_copyright():
    return dict(developer_name=DEVELOPER_NAME, copyright_year=COPYRIGHT_YEAR)
@app.teardown_appcontext
def close_connection(exception):
    if not IS_POSTGRES:
        db = getattr(g, '_database', None)
        if db is not None: db.close()
def allowed_file(f): 
    return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXT
def save_uploaded_image(file):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    try:
        os.makedirs('static/uploads', exist_ok=True)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        save_path = os.path.join('static/uploads', filename)
        file.save(save_path)
        if app.config['UPLOAD_FOLDER'] != 'static/uploads':
            try:
                import shutil
                shutil.copy(save_path, os.path.join(app.config['UPLOAD_FOLDER'], filename))
            except: pass
        return f"static/uploads/{filename}"
    except Exception as e:
        print(f"IMAGE SAVE ERROR: {e}"); traceback.print_exc(); return None

@app.before_request
def check_session_timeout():
    if request.endpoint in ('login', 'register', 'static', 'home', 'forgot_password', 'favicon', None): return
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
            flash("Full Name must contain letters only", "danger"); return render_template('register.html')
        if not id_number.isdigit() or len(id_number) not in (7,8):
            flash("ID Number must be 7 or 8 digits", "danger"); return render_template('register.html')
        if not (phone.isdigit() and len(phone)==10 and phone.startswith('07')):
            flash("Phone must be 10 digits starting with 07", "danger"); return render_template('register.html')
        cur.execute(q("SELECT id FROM users WHERE LOWER(email)=?"), (email,))
        if cur.fetchone():
            flash("Email already exists!", "danger")
            if IS_POSTGRES: cur.close(); db.close()
            return render_template('register.html')
        try:
            cur.execute(q("INSERT INTO users (full_name, id_number, email, phone, password) VALUES (?,?,?,?,?)"), (full_name, id_number, email, phone, generate_password_hash(password)))
            db.commit(); flash("Registration successful! Please login.", "success")
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
        new_password = request.form['new_password']; confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash("Passwords do not match!", "danger"); return render_template('forgot_password.html')
        if len(new_password) < 6:
            flash("Password must be at least 6 characters", "danger"); return render_template('forgot_password.html')
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
        print(f"DASHBOARD ERROR: {e}"); traceback.print_exc(); reqs=[]
    if IS_POSTGRES: 
        try: cur.close(); db.close()
        except: pass
    seen = {}; duplicate_count = 0; duplicate_ids = []
    for r in reqs:
        try: c = r['category']; l = r['location']; d = r['description']
        except: c = l = d = str(r)
        key = (str(c).strip().lower(), str(l).strip().lower(), str(d).strip().lower())
        if key in seen:
            duplicate_count += 1
            try: duplicate_ids.append(r['id'])
            except: pass
        else: seen[key] = True
    has_duplicates = duplicate_count > 0
    try:
        stats={'total':len(reqs),'pending':len([r for r in reqs if r['status']=='Pending']),'inprogress':len([r for r in reqs if r['status']=='In Progress']),'resolved':len([r for r in reqs if r['status']=='Resolved'])}
    except:
        stats={'total':len(reqs),'pending':0,'inprogress':0,'resolved':0}
    return render_template('dashboard.html', requests=reqs, stats=stats, has_duplicates=has_duplicates, duplicate_count=duplicate_count, duplicate_ids=duplicate_ids)
@app.route('/profile', methods=['GET','POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    db=get_db(); cur=get_cursor(db)
    if request.method=='POST':
        full_name = request.form.get('full_name','').strip()
        phone = request.form.get('phone','').strip()
        email = request.form.get('email','').strip().lower()
        if not re.match(r"^[A-Za-z ]+$", full_name) or len(full_name)<3:
            flash("Full name letters only, min 3 chars","danger")
        elif not re.match(r"^07\d{8}$", phone):
            flash("Phone must be 07XXXXXXXX (10 digits)","danger")
        else:
            try:
                cur.execute(q("UPDATE users SET full_name=?, phone=?, email=? WHERE id=?"), (full_name, phone, email, session['user_id']))
                db.commit(); session['full_name']=full_name; flash("Profile updated successfully!","success")
            except Exception as e:
                if IS_POSTGRES: db.rollback()
                err=str(e).lower()
                if 'phone' in err: flash("Phone already used","danger")
                elif 'email' in err: flash("Email already used","danger")
                else: flash(f"Update failed: {e}","danger")
    cur.execute(q("SELECT * FROM users WHERE id=?"), (session['user_id'],))
    user=cur.fetchone()
    if IS_POSTGRES:
        try: cur.close(); db.close()
        except: pass
    return render_template('profile.html', user=user)
@app.route('/submit', methods=['GET','POST'])
def submit_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            category = (request.form.get('category') or request.form.get('service') or 'General').strip()
            location = (request.form.get('location') or request.form.get('ward') or 'Kiharu').strip()
            description = (request.form.get('description') or request.form.get('details') or 'No description').strip()
            image_path = save_uploaded_image(request.files.get('image') or request.files.get('evidence') or request.files.get('photo'))
            db=get_db(); cur=get_cursor(db)
            if IS_POSTGRES:
                cur.execute(q("SELECT id FROM requests WHERE user_id=? AND category=? AND location=? AND description=? AND created_at > NOW() - INTERVAL '60 seconds'"), (session['user_id'], category, location, description))
            else:
                cur.execute(q("SELECT id FROM requests WHERE user_id=? AND category=? AND location=? AND description=? AND created_at > datetime('now','-60 seconds')"), (session['user_id'], category, location, description))
            if cur.fetchone():
                flash("Duplicate ignored - you just submitted this", "warning")
                if IS_POSTGRES: cur.close(); db.close()
                return redirect(url_for('citizen_dashboard'))
            cur.execute(q("INSERT INTO requests (user_id, category, location, description, image_path) VALUES (?,?,?,?,?)"), (session['user_id'], category, location, description, image_path))
            db.commit()
            if IS_POSTGRES: cur.close(); db.close()
            flash("Request submitted with image!" if image_path else "Request submitted!", "success")
            return redirect(url_for('citizen_dashboard'))
        except Exception as e:
            traceback.print_exc(); flash(f"Submission error: {e}", "danger"); return redirect(url_for('citizen_dashboard'))
    return render_template('submit_request.html')
@app.route('/new_request', methods=['GET','POST'])
def new_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            category = (request.form.get('category') or 'General').strip()
            location = (request.form.get('location') or request.form.get('ward') or 'Kiharu').strip()
            description = (request.form.get('description') or '').strip() or 'No drugs at the hospital'
            image_path = save_uploaded_image(request.files.get('image') or request.files.get('evidence') or request.files.get('photo'))
            db = get_db(); cur=get_cursor(db)
            if IS_POSTGRES:
                cur.execute(q("SELECT id FROM requests WHERE user_id=? AND category=? AND location=? AND description=? AND created_at > NOW() - INTERVAL '60 seconds'"), (session['user_id'], category, location, description))
            else:
                cur.execute(q("SELECT id FROM requests WHERE user_id=? AND category=? AND location=? AND description=? AND created_at > datetime('now','-60 seconds')"), (session['user_id'], category, location, description))
            if cur.fetchone():
                flash("Duplicate ignored - you just submitted this", "warning")
                if IS_POSTGRES: cur.close(); db.close()
                return redirect(url_for('citizen_dashboard'))
            cur.execute(q("INSERT INTO requests (user_id, category, location, description, image_path) VALUES (?,?,?,?,?)"), (session['user_id'], category, location, description, image_path))
            db.commit()
            if IS_POSTGRES: cur.close(); db.close()
            flash("Request submitted with image!" if image_path else "Request submitted!", "success")
            return redirect(url_for('citizen_dashboard'))
        except Exception as e:
            traceback.print_exc(); flash(f"Error submitting: {e}", "danger"); return redirect(url_for('citizen_dashboard'))
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
        new_image_path = req['image_path']
        uploaded = request.files.get('image')
        if uploaded and uploaded.filename:
            saved = save_uploaded_image(uploaded)
            if saved: new_image_path = saved
        cur.execute(q("UPDATE requests SET category=?, location=?, description=?, image_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"), (request.form.get('category', req['category']), request.form.get('location', req['location']), request.form.get('description', req['description']), new_image_path, req_id, session['user_id']))
        db.commit()
        if IS_POSTGRES: cur.close(); db.close()
        flash("Request updated!", "success")
        return redirect(url_for('citizen_dashboard'))
    if IS_POSTGRES: cur.close(); db.close()
    return render_template('edit_request.html', req=req)
@app.route('/citizen/request/<int:req_id>/delete', methods=['POST'])
def delete_citizen_request(req_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cur=get_cursor(db)
    cur.execute(q("SELECT id FROM requests WHERE id=? AND user_id=?"), (req_id, session['user_id']))
    if not cur.fetchone():
        flash("Request not found or not yours", "danger")
    else:
        cur.execute(q("DELETE FROM requests WHERE id=? AND user_id=?"), (req_id, session['user_id']))
        db.commit(); flash(f"Request #{req_id} deleted", "success")
    if IS_POSTGRES:
        try: cur.close(); db.close()
        except: pass
    return redirect(url_for('citizen_dashboard'))
@app.route('/citizen/cleanup-duplicates', methods=['POST'])
def cleanup_my_duplicates():
    if 'user_id' not in session: return redirect(url_for('login'))
    db=get_db(); cur=get_cursor(db)
    cur.execute(q("SELECT id, category, location, description, created_at FROM requests WHERE user_id=? ORDER BY created_at DESC"), (session['user_id'],))
    all_reqs = cur.fetchall()
    seen = set(); to_delete = []
    for r in all_reqs:
        key = (r['category'].strip().lower(), r['location'].strip().lower(), r['description'].strip().lower())
        if key in seen: to_delete.append(r['id'])
        else: seen.add(key)
    if to_delete:
        for del_id in to_delete:
            cur.execute(q("DELETE FROM requests WHERE id=? AND user_id=?"), (del_id, session['user_id']))
        db.commit(); flash(f"Cleaned {len(to_delete)} duplicate(s)", "success")
    else:
        flash("No exact duplicates found", "info")
    if IS_POSTGRES:
        try: cur.close(); db.close()
        except: pass
    return redirect(url_for('citizen_dashboard'))
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
    cur.execute("SELECT COUNT(*) AS count FROM requests"); total=cur.fetchone()['count'] if IS_POSTGRES else cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) AS count FROM requests WHERE status='Pending'"); pending=cur.fetchone()['count'] if IS_POSTGRES else cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) AS count FROM requests WHERE status='In Progress'"); inprog=cur.fetchone()['count'] if IS_POSTGRES else cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) AS count FROM requests WHERE status='Resolved'"); resolved=cur.fetchone()['count'] if IS_POSTGRES else cur.fetchone()[0]
    cur.execute("SELECT category, COUNT(*) as c FROM requests GROUP BY category"); by_category=cur.fetchall()
    if IS_POSTGRES: cur.close(); db.close()
    return render_template('admin_dashboard.html', requests=all_reqs, total=total, pending=pending, inprog=inprog, resolved=resolved, by_category=by_category, current_filter=status_filter)
@app.route('/admin/request/<int:request_id>')
def admin_request_detail(request_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    db = get_db(); cur = get_cursor(db)
    cur.execute(q("SELECT r.*, u.full_name, u.phone, u.email FROM requests r LEFT JOIN users u ON r.user_id = u.id WHERE r.id = ?"), (request_id,))
    req = cur.fetchone()
    if IS_POSTGRES: cur.close(); db.close()
    if not req:
        flash('Request not found', 'danger'); return redirect('/admin')
    return render_template('admin_request_detail.html', r=req, developer_name='soloh_kim', copyright_year=2026)
@app.route('/admin/update/<int:req_id>', methods=['POST'])
def update_request(req_id):
    if session.get('role')!='admin': return redirect(url_for('login'))
    db=get_db(); cur=get_cursor(db)
    cur.execute(q("UPDATE requests SET status=?, admin_remarks=?, updated_at=CURRENT_TIMESTAMP WHERE id=?"), (request.form['status'], request.form['admin_remarks'], req_id))
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
    cur.execute("SELECT u.*, (SELECT COUNT(*) FROM requests WHERE user_id=u.id) as total_requests, (SELECT COUNT(*) FROM requests WHERE user_id=u.id AND status='Pending') as pending, (SELECT COUNT(*) FROM requests WHERE user_id=u.id AND status='Resolved') as resolved FROM users u ORDER BY u.created_at DESC")
    users=cur.fetchall()
    cur.execute("SELECT COUNT(*) AS count FROM users WHERE role='citizen'")
    total_users_row = cur.fetchone(); total_users = total_users_row['count'] if IS_POSTGRES else total_users_row[0]
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
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return e
@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    print("=== UNHANDLED EXCEPTION ==="); print(tb)
    return f"<html><body style='padding:20px;font-family:monospace'><h2 style='color:red'>REAL ERROR:</h2><p>{e}</p><pre style='background:#000;color:#0f0;padding:15px;white-space:pre-wrap'>{tb}</pre><a href='/dashboard'>Back</a></body></html>", 500
if __name__=='__main__':
    app.run(debug=True)
