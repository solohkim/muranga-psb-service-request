# Murang'a County - PSB Service Request Management System

> Huduma Bora, Maisha Bora | Developed by [soloh_kim](https://www.linkedin.com/in/soloh-kim/) © 2026

A full-stack web application for Murang'a County Public Service Board (PSB) to manage citizen service requests like Health Facility, Water Issues, Drainage, etc. Built for efficiency, transparency, and SLA compliance (48hrs).

**Live Demo:** https://muranga-psb-service-request.onrender.com/

---

### ✨ Key Features

**For Citizens:**
- Secure Registration & Login (Full Name validation, ID 7/8 digits, 07XXXXXXXX phone)
- Submit requests with image evidence (png/jpg/jpeg, 5MB max)
- Dashboard with stats (Total, Pending, In Progress, Resolved)
- Edit/Delete only Pending requests
- Duplicate detection & cleanup (exact category+location+description)
- Session timeout 15 mins + security headers
- Profile update

**For Admin (PSB Control):**
- Secure Admin Panel `/admin` - admin@muranga.go.ke / admin123
- **New v2.0:** Clean Details column with View button only (no cluttered description)
- View full request detail page `/admin/request/<id>` with citizen info, image, full description
- Filter by status: All / Pending / In Progress / Resolved
- Stats cards: Total, Pending, In Progress, Resolved
- Update status + admin remarks
- Delete requests
- Members management `/admin/users` - view users, total requests, delete user
- Image evidence preview with lightbox

### 🛠️ Tech Stack

- **Backend:** Flask (Python), Werkzeug, Gunicorn
- **Database:** PostgreSQL (Render) + SQLite (local dev) - auto-detected via `DATABASE_URL`
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Custom CSS (Murang'a Green #0a5c26 & Gold #FFD54F)
- **Security:** Password hashing, session timeout, X-Content-Type-Options, X-Frame-Options, Cache-Control: no-store
- **Storage:** `/tmp/uploads` on Render, `static/uploads` locally
- **Deployment:** Render.com

### 📂 Project Structure
pip install -r requirements.txt
python app.py
# Open http://127.0.0.1:5000

AUTHORIZATION

Default LoginsAdmin:
Email: admin@muranga.go.ke
Password: admin123Citizen:
Create a new account via Register page
OR
Email: test@citizen.com / Password: test123

JAVASCRIPT

Muranga_PSB_Service_Request_System/
├── app.py                    # Main Flask app + Session Timeout + Security Headers + RBAC + Members + Filter + Edit + Forgot Password + Delete
├── requirements.txt          # Flask, Werkzeug, gunicorn
├── README.md                 # Project documentation
├── .gitignore                # Ignore DB and uploads
├── static/
│   └── uploads/              # Citizen evidence photos storage
└── templates/
    ├── login.html            # Green/Gold pro login - classy UI
    ├── register.html         # Citizen registration with validation
    ├── forgot_password.html  # Password reset
    ├── dashboard.html        # Citizen dashboard - stats + requests + timeline + edit button
    ├── edit_request.html     # Edit own pending request
    ├── submit_request.html   # Submit new service request form
    ├── new_request.html      # Alternative request form
    ├── admin_dashboard.html  # Admin control - stats clickable + filter pills + update + delete
    └── admin_users.html      # Admin members tracking - all citizens + request counts + delete user

    API Routes
    /→ redirect to login
    /register (GET/POST)
    /login (GET/POST)
    /forgot-password(GET/POST)
    /dashboard - citizen stats + list
    /submit & /new_request - create request
    /citizen/request/<id>/edit - edit own pending
    /admin?status=All|Pending|In Progress|Resolved - admin dashboard with filter
    /admin/update/<id> - update status
    /admin/request/<id>/delete - delete request
    /admin/users - members tracking
    /admin/user/<id>/delete - delete member + requests/logout



```bash
git clone https://github.com/solohkim/muranga-psb-service-request.git
cd muranga-psb-service-request
pip install -r requirements.txt
python app.py
# Open http://127.0.0.1:5000


## Murang'a PSB eService
- Live: https://muranga-psb-service-request.onrender.com
- Admin: admin@muranga.go.ke / admin123
- Features: Citizen submission with image, Admin management, Duplicate handling
- Stack: Flask, Postgres, Bootstrap 5
- Developer: soloh_kim © 2026
Murang'a County Government - Huduma Bora, Maisha Bora