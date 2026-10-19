import os, sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "muranga-psb-2026-secret"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
ALLOWED_EXT = {'png','jpg','jpeg'}
DATABASE = 'database.db'
DEVELOPER_NAME = "YOUR FULL NAME HERE - Replace this" # <-- CHANGE THIS!
COPYRIGHT_YEAR = "2026"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with sqlite3.connect(DATABASE) as db:
        db.executescript("""
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
        cur = db.execute("SELECT * FROM users WHERE email='admin@muranga.go.ke'")
        if not cur.fetchone():
            db.execute("INSERT INTO users (full_name, email, password, role) VALUES (?,?,?,?)",
                       ("Admin Muranga", "admin@muranga.go.ke", generate_password_hash("admin123"), "admin"))
        db.commit()

init_db()

@app.context_processor
def inject_copyright():
    return dict(developer_name=DEVELOPER_NAME, copyright_year=COPYRIGHT_YEAR)

@app.teardown_appcontext
def close_connection(exception):
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
                    return render_template('register.html')
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
        db = get_db()
        email = request.form['email'].strip().lower()  # ALWAYS lower
        full_name = request.form['full_name'].strip()
        id_number = request.form['id_number'].strip()
        phone = request.form['phone'].strip()
        password = request.form['password']

        # 1. CHECK FIRST - case-insensitive
        existing = db.execute("SELECT id FROM users WHERE LOWER(email)=?", (email,)).fetchone()
        if existing:
            flash("Email already exists! This email is already registered. Please login or use Forgot Password.", "danger")
            return render_template('register.html')

        # 2. Try insert
        try:
            db.execute("INSERT INTO users (full_name, id_number, email, phone, password) VALUES (?,?,?,?,?)",
                       (full_name, id_number, email, phone, generate_password_hash(password)))
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # This will still catch if UNIQUE fails
            flash("Email already exists! Please use a different email or login.", "danger")
            return render_template('register.html')
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return render_template('register.html')
            
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = get_db().execute("SELECT * FROM users WHERE email=?", (request.form['email'].strip().lower(),)).fetchone()
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
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            flash("No account found with that email", "danger")
            return render_template('forgot_password.html')
        db.execute("UPDATE users SET password=? WHERE email=?", (generate_password_hash(new_password), email))
        db.commit()
        flash("Password reset successful! Please login with new password.", "success")
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
def citizen_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    db=get_db(); reqs=db.execute("SELECT * FROM requests WHERE user_id=? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    stats={'total':len(reqs),'pending':len([r for r in reqs if r['status']=='Pending']),'inprogress':len([r for r in reqs if r['status']=='In Progress']),'resolved':len([r for r in reqs if r['status']=='Resolved'])}
    return render_template('dashboard.html', requests=reqs, stats=stats)

@app.route('/submit', methods=['GET','POST'])
def submit_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        image_path=None
        file=request.files.get('image')
        if file and file.filename!='' and allowed_file(file.filename):
            filename=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path=f"static/uploads/{filename}"
        get_db().execute("INSERT INTO requests (user_id, category, location, description, image_path) VALUES (?,?,?,?,?)",
                         (session['user_id'], request.form['category'], request.form['location'], request.form['description'], image_path))
        get_db().commit(); flash("Request submitted!", "success")
        return redirect(url_for('citizen_dashboard'))
    return render_template('submit_request.html')

@app.route('/new_request', methods=['GET','POST'])
def new_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        image_path=None
        file=request.files.get('image')
        if file and file.filename!='' and allowed_file(file.filename):
            filename=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path=f"static/uploads/{filename}"
        category = request.form.get('category','General')
        location = request.form.get('location', request.form.get('ward','Kiharu'))
        description = request.form.get('description','')
        db = get_db()
        db.execute("INSERT INTO requests (user_id, category, location, description, image_path) VALUES (?,?,?,?,?)",
                   (session['user_id'], category, location, description, image_path))
        db.commit()
        flash("Request submitted successfully!", "success")
        return redirect(url_for('citizen_dashboard'))
    try: return render_template('new_request.html')
    except: return render_template('submit_request.html')

@app.route('/admin')
def admin_dashboard():
    if session.get('role')!='admin': return redirect(url_for('login'))
    db=get_db()
    all_reqs=db.execute("SELECT r.*, u.full_name, u.phone FROM requests r JOIN users u ON r.user_id=u.id ORDER BY r.created_at DESC").fetchall()
    total=db.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    pending=db.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'").fetchone()[0]
    inprog=db.execute("SELECT COUNT(*) FROM requests WHERE status='In Progress'").fetchone()[0]
    resolved=db.execute("SELECT COUNT(*) FROM requests WHERE status='Resolved'").fetchone()[0]
    by_category=db.execute("SELECT category, COUNT(*) as c FROM requests GROUP BY category").fetchall()
    return render_template('admin_dashboard.html', requests=all_reqs, total=total, pending=pending, inprog=inprog, resolved=resolved, by_category=by_category)

@app.route('/admin/update/<int:req_id>', methods=['POST'])
def update_request(req_id):
    if session.get('role')!='admin': return redirect(url_for('login'))
    db=get_db()
    db.execute("UPDATE requests SET status=?, admin_remarks=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
               (request.form['status'], request.form['admin_remarks'], req_id))
    db.commit()
    flash("Updated!", "success")
    return redirect(url_for('admin_dashboard'))

if __name__=='__main__':
    app.run(debug=True)