from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Session, Member, Attendance, SessionCategory
from app import db
from app.utils.audit import log_action

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/attendance')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_f = request.args.get('status', 'scheduled')

    q = Session.query
    if search:
        q = q.filter(Session.session_name.ilike(f'%{search}%'))
    if status_f:
        q = q.filter_by(status=status_f)

    sessions = q.order_by(Session.date.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('attendance/index.html', sessions=sessions, search=search, status_f=status_f)


@attendance_bp.route('/attendance/mark/<int:session_id>', methods=['GET', 'POST'])
@login_required
def mark(session_id):
    if not current_user.can('mark_attendance'):
        flash('Access denied.', 'danger')
        return redirect(url_for('attendance.index'))

    s = Session.query.get_or_404(session_id)
    
    if s.attendance_locked and not current_user.has_role('admin', 'super_admin'):
        flash('Attendance is locked for this session. Contact an Admin to reopen.', 'warning')
        return redirect(url_for('attendance.index'))

    # Load members based on session category
    session_cat = s.category
    if session_cat:
        # Get members who have this category AND are active
        from app.models import Category
        cat = Category.query.filter_by(name=session_cat.name).first()
        if cat:
            members = cat.members.filter_by(status='active').order_by(Member.full_name).all()
        else:
            members = []
    else:
        # Fallback: if no category, load all active members
        members = Member.query.filter_by(status='active').order_by(Member.full_name).all()

    existing = {a.member_id: a for a in Attendance.query.filter_by(session_id=session_id).all()}

    if request.method == 'POST':
        present_ids = set(request.form.getlist('present'))
        
        for member in members:
            att = existing.get(member.id)
            status = 'present' if str(member.id) in present_ids else 'absent'
            if att:
                att.status = status
                att.marked_by = current_user.id
            else:
                att = Attendance(session_id=session_id, member_id=member.id,
                                 status=status, marked_by=current_user.id)
                db.session.add(att)

        s.attendance_locked = True
        db.session.commit()
        log_action('Mark Attendance', f'Marked attendance for session {s.session_id} - {s.session_name}')
        flash('Attendance saved and locked.', 'success')
        return redirect(url_for('attendance.index'))

    return render_template('attendance/mark.html', session=s, members=members, existing=existing)


@attendance_bp.route('/attendance/reopen/<int:session_id>', methods=['POST'])
@login_required
def reopen(session_id):
    if not current_user.has_role('admin', 'super_admin'):
        flash('Only Admin or Super Admin can reopen attendance.', 'danger')
        return redirect(url_for('attendance.index'))
    s = Session.query.get_or_404(session_id)
    s.attendance_locked = False
    db.session.commit()
    log_action('Reopen Attendance', f'Reopened attendance for session {s.session_id}')
    flash('Attendance unlocked for editing.', 'success')
    return redirect(url_for('attendance.mark', session_id=session_id))


@attendance_bp.route('/attendance/view/<int:session_id>')
@login_required
def view_session(session_id):
    s = Session.query.get_or_404(session_id)
    records = db.session.query(Attendance, Member).join(
        Member, Attendance.member_id == Member.id
    ).filter(Attendance.session_id == session_id).order_by(Member.full_name).all()
    present = sum(1 for a, m in records if a.status == 'present')
    total = len(records)
    pct = round(present / total * 100, 1) if total > 0 else 0
    return render_template('attendance/view_session.html', session=s, records=records,
                           present=present, total=total, pct=pct)
