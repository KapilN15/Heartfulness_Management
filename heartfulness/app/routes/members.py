from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, date
from app.models import Member, Category
from app import db
from app.utils.audit import log_action

members_bp = Blueprint('members', __name__)


def require_permission(perm):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.can(perm):
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def parse_date(val):
    if not val or str(val).strip() in ('', 'None', 'nan'):
        return date.today()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(str(val).strip()[:10], fmt).date()
        except Exception:
            pass
    return date.today()


@members_bp.route('/members')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search     = request.args.get('search', '')
    gender_f   = request.args.get('gender', '')
    status_f   = request.args.get('status', '')
    area_f     = request.args.get('area', '')
    category_f = request.args.get('category', '')
    religion_f = request.args.get('religion', '')

    q = Member.query
    if search:
        q = q.filter(db.or_(
            Member.full_name.ilike(f'%{search}%'),
            Member.member_id.ilike(f'%{search}%'),
            Member.mobile_number.ilike(f'%{search}%'),
            Member.area.ilike(f'%{search}%'),
        ))
    if gender_f:   q = q.filter_by(gender=gender_f)
    if status_f:   q = q.filter_by(status=status_f)
    if area_f:     q = q.filter(Member.area.ilike(f'%{area_f}%'))
    if religion_f: q = q.filter_by(religion=religion_f)
    if category_f:
        cat = Category.query.get(int(category_f))
        if cat:
            q = q.filter(Member.categories.contains(cat))

    members    = q.order_by(Member.id.desc()).paginate(page=page, per_page=15, error_out=False)
    areas      = [a[0] for a in db.session.query(Member.area).distinct().all() if a[0]]
    religions  = [r[0] for r in db.session.query(Member.religion).distinct().all() if r[0]]
    categories = Category.query.filter_by(status='active').all()

    return render_template('members/index.html', members=members, search=search,
                           gender_f=gender_f, status_f=status_f, area_f=area_f,
                           category_f=category_f, religion_f=religion_f,
                           areas=areas, religions=religions, categories=categories)


@members_bp.route('/members/add', methods=['GET', 'POST'])
@login_required
@require_permission('manage_members')
def add():
    categories = Category.query.filter_by(status='active').all()
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required.', 'danger')
            return render_template('members/form.html', member=None, action='Add', categories=categories)

        member = Member(
            member_id    = Member.generate_member_id(),
            full_name    = full_name,
            gender       = request.form.get('gender', '').strip() or None,
            age          = request.form.get('age', type=int),
            religion     = request.form.get('religion', '').strip() or None,
            mobile_number= request.form.get('mobile_number', '').strip() or None,
            area         = (request.form.get('area', '').strip() or '').upper() or None,
            join_date    = parse_date(request.form.get('join_date')),
            status       = request.form.get('status', 'active'),
            created_by   = current_user.id,
        )
        for cat_id in request.form.getlist('categories'):
            cat = Category.query.get(int(cat_id))
            if cat:
                member.categories.append(cat)

        db.session.add(member)
        db.session.commit()
        log_action('Add Member', f'Added member {member.member_id} - {member.full_name}')
        flash(f'Member {member.full_name} added successfully with ID {member.member_id}.', 'success')
        return redirect(url_for('members.index'))

    return render_template('members/form.html', member=None, action='Add', categories=categories)


@members_bp.route('/members/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('manage_members')
def edit(id):
    member     = Member.query.get_or_404(id)
    categories = Category.query.filter_by(status='active').all()

    if request.method == 'POST':
        member.full_name    = request.form.get('full_name', '').strip()
        member.gender       = request.form.get('gender', '').strip() or None
        member.age          = request.form.get('age', type=int)
        member.religion     = request.form.get('religion', '').strip() or None
        member.mobile_number= request.form.get('mobile_number', '').strip() or None
        member.area         = (request.form.get('area', '').strip() or '').upper() or None
        member.join_date    = parse_date(request.form.get('join_date'))
        member.status       = request.form.get('status', 'active')

        member.categories.clear()
        for cat_id in request.form.getlist('categories'):
            cat = Category.query.get(int(cat_id))
            if cat:
                member.categories.append(cat)

        db.session.commit()
        log_action('Edit Member', f'Edited member {member.member_id} - {member.full_name}')
        flash('Member updated successfully.', 'success')
        return redirect(url_for('members.index'))

    return render_template('members/form.html', member=member, action='Edit', categories=categories)


@members_bp.route('/members/view/<int:id>')
@login_required
def view(id):
    member = Member.query.get_or_404(id)
    from app.models import Attendance, Session as Sess
    records = db.session.query(Attendance, Sess).join(
        Sess, Attendance.session_id == Sess.id
    ).filter(Attendance.member_id == id).order_by(Sess.date.desc()).limit(20).all()

    total   = len(records)
    present = sum(1 for a, s in records if a.status == 'present')
    pct     = round(present / total * 100, 1) if total > 0 else 0
    return render_template('members/view.html', member=member, records=records,
                           total_att=total, present_att=present, pct=pct)


@members_bp.route('/members/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('manage_members')
def delete(id):
    member = Member.query.get_or_404(id)
    member.status = 'inactive'
    db.session.commit()
    log_action('Delete Member', f'Soft-deleted member {member.member_id} - {member.full_name}')
    flash(f'Member {member.full_name} has been deactivated.', 'success')
    return redirect(url_for('members.index'))
