import io
import csv
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, case
from app.models import Member, Session, Attendance, SessionCategory, Category
from app import db

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def index():
    return render_template('reports/index.html')


# ── Members Report ─────────────────────────────────────────────
@reports_bp.route('/reports/members')
@login_required
def members_report():
    status_f   = request.args.get('status', '')
    gender_f   = request.args.get('gender', '')
    religion_f = request.args.get('religion', '')
    area_f     = request.args.get('area', '')
    category_f = request.args.get('category', '')

    q = Member.query
    if status_f:   q = q.filter_by(status=status_f)
    if gender_f:   q = q.filter_by(gender=gender_f)
    if religion_f: q = q.filter_by(religion=religion_f)
    if area_f:     q = q.filter(Member.area.ilike(f'%{area_f}%'))
    if category_f:
        cat = Category.query.get(int(category_f))
        if cat: q = q.filter(Member.categories.contains(cat))

    all_members = q.all()
    total   = len(all_members)
    active  = sum(1 for m in all_members if m.status == 'active')
    inactive= total - active

    # Distribution counts based on filtered set
    from collections import Counter
    gender_c   = Counter(m.gender   or 'Unknown' for m in all_members)
    religion_c = Counter(m.religion or 'Unknown' for m in all_members)
    area_c     = Counter(m.area     or 'Unknown' for m in all_members)

    gender   = sorted(gender_c.items(),   key=lambda x: -x[1])
    religion = sorted(religion_c.items(), key=lambda x: -x[1])
    area     = sorted(area_c.items(),     key=lambda x: -x[1])[:10]

    categories = Category.query.filter_by(status='active').all()
    religions  = [r[0] for r in db.session.query(Member.religion).distinct().all() if r[0]]
    areas      = [a[0] for a in db.session.query(Member.area).distinct().all() if a[0]]

    return render_template('reports/members.html',
        total=total, active=active, inactive=inactive,
        gender=gender, religion=religion, area=area,
        status_f=status_f, gender_f=gender_f, religion_f=religion_f,
        area_f=area_f, category_f=category_f,
        categories=categories, religions=religions, areas=areas)


# ── Attendance Report ──────────────────────────────────────────
@reports_bp.route('/reports/attendance')
@login_required
def attendance_report():
    cat_f      = request.args.get('category', '')
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')

    q = db.session.query(
        Session.session_id, Session.session_name, Session.date,
        SessionCategory.name.label('category_name'),
        func.count(Attendance.id).label('total'),
        func.sum(case((Attendance.status == 'present', 1), else_=0)).label('present')
    ).outerjoin(Attendance, Attendance.session_id == Session.id
    ).outerjoin(SessionCategory, SessionCategory.id == Session.category_id
    ).filter(Session.status == 'completed')

    if cat_f:     q = q.filter(Session.category_id == int(cat_f))
    if date_from:
        from datetime import datetime
        try: q = q.filter(Session.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except: pass
    if date_to:
        from datetime import datetime
        try: q = q.filter(Session.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except: pass

    sessions   = q.group_by(Session.id).order_by(Session.date.desc()).all()
    session_cats = SessionCategory.query.filter_by(status='active').all()

    return render_template('reports/attendance.html',
        sessions=sessions, session_cats=session_cats,
        cat_f=cat_f, date_from=date_from, date_to=date_to)


# ── Sessions Report ────────────────────────────────────────────
@reports_bp.route('/reports/sessions')
@login_required
def sessions_report():
    cat_f = request.args.get('category', '')

    q = db.session.query(
        SessionCategory.name,
        func.count(Session.id).label('total'),
        func.sum(case((Session.status == 'completed',  1), else_=0)).label('completed'),
        func.sum(case((Session.status == 'scheduled',  1), else_=0)).label('scheduled'),
        func.sum(case((Session.status == 'cancelled',  1), else_=0)).label('cancelled'),
        func.sum(case((Session.status == 'draft',      1), else_=0)).label('draft'),
    ).outerjoin(Session, Session.category_id == SessionCategory.id)

    if cat_f: q = q.filter(SessionCategory.id == int(cat_f))
    stats = q.group_by(SessionCategory.id).all()

    session_cats = SessionCategory.query.filter_by(status='active').all()
    return render_template('reports/sessions.html', stats=stats, session_cats=session_cats, cat_f=cat_f)


# ── CSV Exports ────────────────────────────────────────────────
@reports_bp.route('/reports/export/members.csv')
@login_required
def export_members_csv():
    status_f   = request.args.get('status', '')
    gender_f   = request.args.get('gender', '')
    religion_f = request.args.get('religion', '')
    area_f     = request.args.get('area', '')
    category_f = request.args.get('category', '')

    q = Member.query
    if status_f:   q = q.filter_by(status=status_f)
    if gender_f:   q = q.filter_by(gender=gender_f)
    if religion_f: q = q.filter_by(religion=religion_f)
    if area_f:     q = q.filter(Member.area.ilike(f'%{area_f}%'))
    if category_f:
        cat = Category.query.get(int(category_f))
        if cat: q = q.filter(Member.categories.contains(cat))

    members = q.all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Member ID','Full Name','Gender','Age','Religion','Mobile','Area','Categories','Join Date','Status'])
    for m in members:
        cats = ', '.join(c.name for c in m.categories)
        w.writerow([m.member_id, m.full_name, m.gender, m.age, m.religion,
                    m.mobile_number, m.area, cats, m.join_date, m.status])
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode()), mimetype='text/csv',
                     as_attachment=True, download_name='members_report.csv')


@reports_bp.route('/reports/export/members.pdf')
@login_required
def export_members_pdf():
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch

    status_f   = request.args.get('status', '')
    gender_f   = request.args.get('gender', '')
    q = Member.query
    if status_f: q = q.filter_by(status=status_f)
    if gender_f: q = q.filter_by(gender=gender_f)
    members = q.all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = [Paragraph('Heartfulness NGO – Member Report', styles['Title']), Spacer(1, 0.2*inch)]

    data = [['Member ID','Full Name','Gender','Age','Religion','Mobile','Area','Categories','Status']]
    for m in members:
        cats = ', '.join(c.name for c in m.categories)
        data.append([m.member_id, m.full_name or '', m.gender or '', str(m.age or ''),
                     m.religion or '', m.mobile_number or '', m.area or '', cats, m.status])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
        ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,0), 8),
        ('FONTSIZE',    (0,1),(-1,-1), 7),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#EFF6FF')]),
        ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#BFDBFE')),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]))
    elements.append(t)
    doc.build(elements)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='members_report.pdf')


@reports_bp.route('/reports/export/attendance.csv')
@login_required
def export_attendance_csv():
    cat_f     = request.args.get('category', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    q = db.session.query(
        Session.session_id, Session.session_name, Session.date,
        SessionCategory.name.label('cat_name'),
        func.count(Attendance.id).label('total'),
        func.sum(case((Attendance.status == 'present', 1), else_=0)).label('present')
    ).outerjoin(Attendance, Attendance.session_id == Session.id
    ).outerjoin(SessionCategory, SessionCategory.id == Session.category_id
    ).filter(Session.status == 'completed')

    if cat_f: q = q.filter(Session.category_id == int(cat_f))
    if date_from:
        from datetime import datetime
        try: q = q.filter(Session.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except: pass
    if date_to:
        from datetime import datetime
        try: q = q.filter(Session.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except: pass

    sessions = q.group_by(Session.id).order_by(Session.date.desc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Session ID','Session Name','Category','Date','Total','Present','Absent','Attendance %'])
    for s in sessions:
        absent = (s.total or 0) - (s.present or 0)
        pct    = round((s.present or 0) / s.total * 100, 1) if s.total else 0
        w.writerow([s.session_id, s.session_name, s.cat_name or '', s.date,
                    s.total or 0, s.present or 0, absent, pct])
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode()), mimetype='text/csv',
                     as_attachment=True, download_name='attendance_report.csv')
