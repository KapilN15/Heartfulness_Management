from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import AuditLog, User
from app import db

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/audit-logs')
@login_required
def index():
    if not current_user.has_role('super_admin'):
        flash('Only Super Admin can view audit logs.', 'danger')
        return redirect(url_for('dashboard.index'))

    page       = request.args.get('page', 1, type=int)
    search     = request.args.get('search', '')
    role_f     = request.args.get('role', '')
    action_f   = request.args.get('action', '')
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')

    q = AuditLog.query
    if search:
        q = q.filter(db.or_(
            AuditLog.username.ilike(f'%{search}%'),
            AuditLog.action.ilike(f'%{search}%'),
            AuditLog.description.ilike(f'%{search}%'),
        ))
    if role_f:   q = q.filter_by(role=role_f)
    if action_f: q = q.filter(AuditLog.action.ilike(f'%{action_f}%'))
    if date_from:
        from datetime import datetime
        try:
            q = q.filter(AuditLog.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        except Exception:
            pass
    if date_to:
        from datetime import datetime
        try:
            q = q.filter(AuditLog.timestamp <= datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
        except Exception:
            pass

    logs = q.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=25, error_out=False)

    # Distinct actions for filter dropdown
    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all() if r[0]]

    return render_template('audit/index.html', logs=logs,
                           search=search, role_f=role_f, action_f=action_f,
                           date_from=date_from, date_to=date_to, actions=actions)
