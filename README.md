# Murang'a County PSB - Citizen Service Request System
**Huduma Bora, Maisha Bora | County Government E-Service Portal**

> Built for Murang'a County Public Service Board 2026 - Final Year Project by soloh_kim © 2026
> **Data Protection Act 2019 (ODPC) Compliant**

### Live Links
- **GitHub:** https://github.com/solohkim/muranga-psb-service-request
- **Live Demo:** https://muranga-psb-service-request.onrender.com

### Overview
A secure citizen e-service portal where citizens can register, submit service requests with location (8 wards: Kiharu, Kangema, Mathioya, Kigumo, Maragua, Kandara, Gatanga, Makuyu) and photo evidence, and track status. Admins manage all requests, filter by status, update status with remarks, delete requests, view all registered members, and view evidence thumbnails. Built with Murang'a County green/gold theme - classy, responsive, professional.

### Core Features
**Citizen:**
- Registration with strict validation (Name letters only, ID 7-8 digits, Phone 07xxxxxxxx 10 digits, Unique email)
- Login/Logout with 15min session timeout
- Dashboard with stats (Total/Pending/In Progress/Resolved)
- Submit Request with category, ward, description, photo upload (png/jpg/jpeg)
- **Edit Own Pending Requests** - `/citizen/request/<id>/edit` - No 500 error
- Track status + admin remarks timeline
- Forgot Password with email verification

**Admin:**
- View all requests with citizen info (name, phone), evidence thumbnails
- **Filter/Sort Services:** All / Pending / In Progress / Resolved - Clickable stat cards + filter pills (`/admin?status=Pending`)
- Update status (Pending/In Progress/Resolved), add admin remarks
- **Delete Requests:** Admin can delete any request
- **Members Tracking Page:** `/admin/users` - View all registered citizens with total requests count, pending/resolved breakdown, join date, ID number, phone, email
- **Delete Members:** Full right to erasure (deletes user + all their requests) - ODPC Compliant
- Real-time counts dashboard

**UI/UX:**
- Murang'a green #0a5c26 / gold #FFD54F, Bootstrap 5.3, Bootstrap Icons, responsive
- Avatar initials, status badges (Pending yellow, In Progress blue, Resolved green), clickable logos, filter active states

### Security & ODPC Compliance (Data Protection Act 2019)
- **Password Security:** `werkzeug.security generate_password_hash / check_password_hash` - never plain text
- **Session Management:** 15min inactive timeout via `@app.before_request`, `PERMANENT_SESSION_LIFETIME`, auto logout, `Cache-Control: no-store`
- **Security Headers:** X-Frame-Options DENY, X-Content-Type-Options nosniff
- **Validation:** Server-side + client-side - Full name letters only, ID digits 7-8, Phone 10 digits 07..., Email unique check (case-insensitive), File type whitelist png/jpg/jpeg + secure_filename
- **RBAC:** Role-based access control - citizen cannot access /admin, admin cannot access citizen edit
- **ODPC Rights:** 
    - Consent on registration
    - Right to Access: /admin/users shows all personal data
    - Right to Erasure: /admin/user/<id>/delete + /admin/request/<id>/delete
    - Data Minimization: Only collects full_name, id_number, email, phone
    - Purpose Limitation: Data used only for service delivery

### Bonus Features
- Forgot Password module
- Citizen edit own request
- Members tracking with request stats per user
- Admin filter by status with URL query param
- Evidence image thumbnails with preview
- Flash messages with categories (success/danger/warning)

### Tech Stack
Flask 3.0, SQLite (row_factory), Werkzeug Security, Bootstrap 5.3, Bootstrap Icons, gunicorn

### Setup Locally
```bash
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

    DeveloperDeveloped by soloh_kim © 2026
Murang'a County Government - Huduma Bora, Maisha Bora