from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, date
from app.models import Session, SessionCategory
from app import db
from app.utils.audit import log_action

sessions_bp = Blueprint('sessions', __name__)


def parse_date(val):
    if not val or str(val).strip() in ('', 'None', 'nan'):
        return date.today()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(val).strip()[:10], fmt).date()
        except Exception:
            pass
    return date.today()


@sessions_bp.route('/sessions')
@login_required
def index():
    page     = request.args.get('page', 1, type=int)
    search   = request.args.get('search', '')
    status_f = request.args.get('status', '')
    cat_f    = request.args.get('category', '')

    q = Session.query
    if search:
        q = q.filter(db.or_(
            Session.session_name.ilike(f'%{search}%'),
            Session.session_id.ilike(f'%{search}%'),
            Session.venue.ilike(f'%{search}%'),
        ))
    if status_f: q = q.filter_by(status=status_f)
    if cat_f:    q = q.filter_by(category_id=int(cat_f))

    sessions   = q.order_by(Session.date.desc()).paginate(page=page, per_page=15, error_out=False)
    categories = SessionCategory.query.filter_by(status='active').all()
    return render_template('sessions/index.html', sessions=sessions, search=search,
                           status_f=status_f, cat_f=cat_f, categories=categories)


@sessions_bp.route('/sessions/add', methods=['GET', 'POST'])
@login_required
def add():
    if not current_user.can('manage_sessions'):
        flash('Access denied.', 'danger')
        return redirect(url_for('sessions.index'))
    categories = SessionCategory.query.filter_by(status='active').all()

    if request.method == 'POST':
        session_name = request.form.get('session_name', '').strip()
        if not session_name:
            flash('Session name is required.', 'danger')
            return render_template('sessions/form.html', session=None, categories=categories, action='Add')
        s = Session(
            session_id  = Session.generate_session_id(),
            session_name= session_name,
            category_id = request.form.get('category_id', type=int),
            date        = parse_date(request.form.get('date')),
            start_time  = request.form.get('start_time', ''),
            end_time    = request.form.get('end_time', ''),
            venue       = request.form.get('venue', '').strip(),
            status      = request.form.get('status', 'scheduled'),
            created_by  = current_user.id,
        )
        db.session.add(s)
        db.session.commit()
        log_action('Create Session', f'Created session {s.session_id} - {s.session_name}')
        flash('Session created successfully.', 'success')
        return redirect(url_for('sessions.index'))

    return render_template('sessions/form.html', session=None, categories=categories, action='Add')


@sessions_bp.route('/sessions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.can('manage_sessions'):
        flash('Access denied.', 'danger')
        return redirect(url_for('sessions.index'))
    s          = Session.query.get_or_404(id)
    categories = SessionCategory.query.filter_by(status='active').all()

    if request.method == 'POST':
        s.session_name = request.form.get('session_name', '').strip()
        s.category_id  = request.form.get('category_id', type=int)
        s.date         = parse_date(request.form.get('date'))
        s.start_time   = request.form.get('start_time', '')
        s.end_time     = request.form.get('end_time', '')
        s.venue        = request.form.get('venue', '').strip()
        s.status       = request.form.get('status', 'scheduled')
        db.session.commit()
        log_action('Edit Session', f'Edited session {s.session_id} - {s.session_name}')
        flash('Session updated.', 'success')
        return redirect(url_for('sessions.index'))

    return render_template('sessions/form.html', session=s, categories=categories, action='Edit')


@sessions_bp.route('/sessions/complete/<int:id>', methods=['POST'])
@login_required
def complete(id):
    if not current_user.can('manage_sessions'):
        flash('Access denied.', 'danger')
        return redirect(url_for('sessions.index'))
    s = Session.query.get_or_404(id)
    s.status = 'completed'
    db.session.commit()
    log_action('Complete Session', f'Marked session {s.session_id} as completed.')
    flash('Session marked as completed.', 'success')
    return redirect(url_for('sessions.index'))


@sessions_bp.route('/sessions/cancel/<int:id>', methods=['POST'])
@login_required
def cancel(id):
    if not current_user.can('manage_sessions'):
        flash('Access denied.', 'danger')
        return redirect(url_for('sessions.index'))
    s = Session.query.get_or_404(id)
    s.status = 'cancelled'
    db.session.commit()
    log_action('Cancel Session', f'Cancelled session {s.session_id}.')
    flash('Session cancelled.', 'success')
    return redirect(url_for('sessions.index'))


@sessions_bp.route('/session-categories')
@login_required
def categories():
    cats = SessionCategory.query.order_by(SessionCategory.id.desc()).all()
    return render_template('sessions/categories.html', categories=cats)


@sessions_bp.route('/session-categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    if not name:
        flash('Category name is required.', 'danger')
        return redirect(url_for('sessions.categories'))
    if SessionCategory.query.filter_by(name=name).first():
        flash('Category already exists.', 'warning')
        return redirect(url_for('sessions.categories'))
    cat = SessionCategory(name=name, description=desc, status='active', created_by=current_user.id)
    db.session.add(cat)
    db.session.commit()
    log_action('Create Session Category', f'Created session category: {name}')
    flash('Category created.', 'success')
    return redirect(url_for('sessions.categories'))


@sessions_bp.route('/session-categories/edit/<int:id>', methods=['POST'])
@login_required
def edit_category(id):
    cat = SessionCategory.query.get_or_404(id)
    cat.name        = request.form.get('name', '').strip()
    cat.description = request.form.get('description', '').strip()
    cat.status      = request.form.get('status', 'active')
    db.session.commit()
    log_action('Edit Session Category', f'Edited session category: {cat.name}')
    flash('Category updated.', 'success')
    return redirect(url_for('sessions.categories'))
