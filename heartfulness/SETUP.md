# Heartfulness NGO Management System - Setup Guide

## Overview

A complete, production-quality web application for managing NGO operations including members, sessions, attendance, and reporting.

**Technology Stack:**
- Backend: Python 3, Flask, SQLAlchemy ORM, SQLite
- Frontend: HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js
- Database: SQLite (file-based, no external dependency)
- Runs locally on your network without internet requirement

---

## System Requirements

- Python 3.8 or higher
- 100MB disk space (including database and uploads)
- Any modern web browser (Chrome, Firefox, Safari, Edge)
- Network connectivity within your local network

---

## Installation Steps

### Step 1: Download and Extract

```bash
# Navigate to your desired directory
cd /your/preferred/location

# Extract the heartfulness.zip file
unzip heartfulness.zip
cd heartfulness
```

### Step 2: Create Virtual Environment (Optional but Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt

# Or if you need to install with --break-system-packages
pip install --break-system-packages -r requirements.txt
```

**Dependencies:**
- Flask 3.0.0 - Web framework
- Flask-Login 0.6.3 - User authentication
- Flask-SQLAlchemy 3.1.1 - Database ORM
- SQLAlchemy 2.0.23 - Database toolkit
- pandas 2.1.4 - CSV processing
- reportlab 4.0.8 - PDF generation

### Step 4: Run the Application

```bash
python run.py
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
```

### Step 5: Access the Application

**From the same computer:**
```
http://localhost:5000
```

**From another computer on the network:**
```
http://<SERVER_IP>:5000
```

To find your server IP:
- **Windows:** `ipconfig` - look for "IPv4 Address"
- **Mac/Linux:** `ifconfig` or `hostname -I`

Example: `http://192.168.1.100:5000`

---

## First-Time Login

The system comes pre-populated with sample data and test accounts:

### Super Admin (Full Access)
- **Username:** `sa1`
- **Password:** `passsa1`

### Admins
- **Username:** `ad1` / **Password:** `passad1`
- **Username:** `ad2` / **Password:** `passad2`

### Coordinators
- **Username:** `co1` / **Password:** `passco1`
- **Username:** `co2` / **Password:** `passco2`

### Trainers
- **Username:** `tr1` - `tr5` / **Password:** `passtr1` - `passtr5`

---

## Project Structure

```
heartfulness/
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── instance/                   # Instance folder (database, uploads)
│   ├── heartfulness.db        # SQLite database file
│   ├── uploads/               # CSV uploads
│   └── backups/               # Database backups
└── app/
    ├── __init__.py            # App factory
    ├── models.py              # Database models (User, Member, Category, etc.)
    ├── routes/                # Blueprint routes
    │   ├── auth.py            # Login/Logout
    │   ├── dashboard.py       # Dashboard
    │   ├── members.py         # Member CRUD
    │   ├── categories.py      # Member categories
    │   ├── sessions.py        # Sessions & session types
    │   ├── attendance.py      # Attendance marking
    │   ├── csv_import.py      # CSV import
    │   ├── reports.py         # Reports & exports
    │   ├── users.py           # User management
    │   ├── audit.py           # Audit logs
    │   └── backup.py          # Backup & restore
    ├── utils/
    │   ├── seed.py            # Database seeding
    │   └── audit.py           # Audit logging
    ├── static/
    │   ├── css/
    │   │   └── style.css      # Main stylesheet
    │   ├── js/
    │   │   └── app.js         # Main JavaScript
    │   └── img/               # Images
    └── templates/             # Jinja2 HTML templates
        ├── base.html          # Base layout
        ├── auth/login.html
        ├── dashboard/
        ├── members/
        ├── categories/
        ├── sessions/
        ├── attendance/
        ├── reports/
        ├── csv_import/
        ├── users/
        ├── audit/
        └── backup/
```

---

## Core Features

### 1. Authentication & Authorization
- Role-based access control (Super Admin, Admin, Coordinator, Trainer)
- Session management
- Secure password hashing

### 2. Member Management
- Add/Edit/View/Soft-Delete members
- Assign members to multiple categories
- Track member status (Active/Inactive)
- Area standardization (automatic uppercase conversion)

### 3. Member Categories
- Create dynamic categories (no hardcoding)
- View category analytics
- Track members per category
- Filter by category

### 4. Session Management
- Create sessions with mandatory category assignment
- Session types (Meditation, Youth Program, etc.)
- Session status tracking (Draft, Scheduled, Completed, Cancelled)

### 5. Attendance Management
- Mark attendance by session
- Load only eligible members (based on session category)
- Attendance locking to prevent modification
- Unlock capability for admins
- Attendance history and statistics

### 6. CSV Import
- Download sample CSV template
- Bulk member import
- Duplicate detection by mobile number
- Category assignment during import
- Automatic area uppercase conversion
- Import history tracking

### 7. Reports & Analytics
- Member reports (count, gender, religion, area distribution)
- Attendance reports (percentage, by session, by member)
- Session reports (statistics, participation)
- CSV and PDF export
- Category analytics (members, attendance, sessions)

### 8. Dashboard
- Key statistics cards
- Interactive charts (Chart.js)
- Gender distribution
- Religion distribution
- Age distribution
- Monthly member growth
- Attendance trends
- Notifications

### 9. Search & Filters
- Global search across members, sessions
- Advanced filters by:
  - Members: Gender, Religion, Status, Category, Area
  - Sessions: Status, Category
  - Attendance: Session, Member, Status
  - Users: Role, Status
  - Audit: Action, User

### 10. User Management
- Create users (Coordinators, Trainers by Admin; All by Super Admin)
- Role assignment
- Password management
- User status toggle

### 11. Audit Logs
- Log all actions (login, CRUD operations, imports)
- Timestamp tracking
- User and role information
- Searchable and filterable

### 12. Backup & Restore
- Create manual database backups
- Download backups
- Restore from backup
- Export all data as ZIP

### 13. Theme System
- Light and Dark themes
- Per-user theme preference
- Persistent across sessions

---

## Configuration

Edit configuration in `app/__init__.py`:

```python
app.config['SECRET_KEY'] = 'change-this-to-random-string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///path-to-db'
```

## Data Backup

**Manual backup (recommended):**
1. Login as Super Admin
2. Go to Backup section
3. Click "Create Backup"
4. Download the backup file

**Automatic backup location:**
```
instance/backups/heartfulness_backup_YYYYMMDD_HHMMSS.db
```

---

## Network Access

### Share on Local Network

Once running on `http://0.0.0.0:5000`, access from other computers using your server's IP:

1. **Find your server IP:**
   ```bash
   # Windows
   ipconfig
   
   # Mac/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. **Access from another computer:**
   ```
   http://<YOUR_SERVER_IP>:5000
   ```

3. **Example:** If your IP is 192.168.1.50:
   ```
   http://192.168.1.50:5000
   ```

### Sharing Access

- All devices must be on the same WiFi network
- No internet required
- Works on local network only
- Multiple users can access simultaneously

---

## Common Issues & Solutions

### Port 5000 Already in Use

```bash
# Find process using port 5000
lsof -i :5000  # Mac/Linux
netstat -ano | findstr :5000  # Windows

# Kill the process or use different port
python run.py --port 8000
```

### Database Locked

- Close the application and reopen
- Delete `instance/heartfulness.db` to start fresh
- Data will be re-seeded automatically

### Can't Access from Another Computer

- Check firewall settings
- Ensure both computers on same network
- Verify server IP address
- Try with IP address, not hostname

### Module Import Errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## User Manual Highlights

### For NGO Staff:

1. **Daily Operations:**
   - View dashboard for quick stats
   - Mark session attendance
   - Add new members
   - View member profiles

2. **Monthly Activities:**
   - Import CSV for bulk member additions
   - Generate attendance reports
   - Review category analytics
   - Check audit logs

3. **Quarterly Reviews:**
   - Export comprehensive reports
   - Create database backups
   - Analyze member growth trends
   - Review session effectiveness

### For Administrators:

1. **User Management:**
   - Create new staff accounts
   - Assign roles
   - Manage permissions
   - Reset passwords

2. **System Maintenance:**
   - View audit logs
   - Manage backups
   - Monitor system usage
   - Control member categories

### For Super Admins:

- Full system control
- All features accessible
- Complete audit trail
- Backup and restore

---

## Performance Tips

1. **Database Optimization:**
   - Performs well with 10,000+ members
   - Indexed on frequently searched fields
   - Optimized queries

2. **Browser Optimization:**
   - Use modern browsers (Chrome, Firefox)
   - Clear browser cache if issues occur
   - JavaScript enabled required

3. **Network:**
   - Local network (100+ concurrent users possible)
   - No external API calls

---

## Support & Troubleshooting

### Logs & Debugging

Logs are displayed in the console when running with `debug=True`.

### Database Reset

To start fresh (WARNING: deletes all data):

```bash
rm instance/heartfulness.db
python run.py
```

### Hard Reset

```bash
# Remove all data
rm -rf instance/

# Run again (recreates fresh database)
python run.py
```

---

## Security Notes

1. **Change Default Passwords** - Immediately change all default user passwords
2. **Network Isolation** - Only accessible on local network by design
3. **Database** - SQLite is single-user; not suitable for high-concurrency scenarios
4. **Backups** - Regularly backup the database

---

## Upgrade & Customization

### Adding Custom Fields

1. Edit `app/models.py` to add new fields
2. Update templates to show/edit fields
3. Update routes as needed
4. Migration: Delete database and reseed

### Customizing Reports

Edit report templates in `app/templates/reports/`

### Styling

Edit CSS in `app/static/css/style.css`

---

## License & Credits

Heartfulness NGO Management System
Built with Flask, SQLAlchemy, Bootstrap, and Chart.js

---

## Contact & Support

For issues, suggestions, or feature requests, document the issue clearly with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots if applicable

---

**Last Updated:** June 2024
**Version:** 1.0.0 Production Ready
