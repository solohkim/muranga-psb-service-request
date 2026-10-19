# Murang'a County PSB - Service Request System
**Huduma Bora, Maisha Bora | County Government E-Service Portal**

> Built for Murang'a County Public Service Board Interview 2026 - Cybersecurity Focus by Solomon Kim

### Live Links
- **GitHub:** https://github.com/solohkim/muranga-psb-service-request
- **Live Demo:** https://muranga-psb-service-request.onrender.com

### Overview
A secure citizen e-service portal where citizens can register, submit service requests with location (8 wards: Kiharu, Kangema, Mathioya, Kigumo, Maragua, Kandara, Gatanga, Makuyu) and photo evidence, and track status. Admins manage all requests, update status with remarks, and view evidence thumbnails. Built with Murang'a County green/gold theme - classy, responsive, professional.

### Core Features
- **Citizen:** Registration, Login/Logout, Dashboard with stats (Total/Pending/In Progress/Resolved), Submit Request with category, ward, description, photo upload, Track timeline
- **Admin:** View all requests with citizen info, evidence thumbnails, update status (Pending/In Progress/Resolved), add admin remarks, real-time counts
- **UI:** Murang'a green #0a5c26 / gold #FFD54F, Bootstrap 5.3, Bootstrap Icons, responsive, avatar initials, status badges, clickable logos

### Bonus Features (10% - Beyond Requirements)
- **Cybersecurity Hardening:** Session timeout after 15min inactive (OWASP), security headers (X-Frame-Options DENY, X-Content-Type-Options nosniff, Cache-Control no-store), role-based access control (RBAC), secure password hashing (Werkzeug), secure_filename + allowed file types validation
- **UX Enhancements:** Evidence image thumbnails in admin, avatar initials, status color badges, clickable logo navigation, timeline tracking
- **Performance:** SQLite with row_factory, optimized queries, gunicorn ready for deployment

### Tech Stack
Flask 3.0, SQLite, Werkzeug Security, Bootstrap 5.3, Bootstrap Icons, gunicorn

### Setup Locally
```bash
pip install -r requirements.txt
python app.py
# Open http://127.0.0.1:5000

JAVASCRIPT 

Email: admin@muranga.go.ke
Password: admin123

JAVASCRIPT

Create a new account via Register page
OR
Email: test@citizen.com / Password: test123

$BASH

Muranga_PSB_Service_Request_System/
├── app.py                    # Main Flask app + Session Timeout + Security Headers + RBAC
├── requirements.txt          # Flask, Werkzeug, gunicorn
├── README.md                 # Project documentation
├── .gitignore                # Ignore DB and uploads
├── static/
│   └── uploads/
│       └── .gitkeep          # Citizen evidence photos storage
└── templates/
    ├── login.html            # Green/Gold pro login - classy UI
    ├── register.html         # Citizen registration
    ├── dashboard.html        # Citizen dashboard - stats + requests + timeline
    ├── submit_request.html   # Submit new service request form
    ├── new_request.html      # Alternative request form
    └── admin_dashboard.html  # Admin control panel - classy stats + thumbnails + status update
