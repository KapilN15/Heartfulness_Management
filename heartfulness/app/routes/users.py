from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User
from app import db
from app.utils.audit import log_action

users_bp = Blueprint('users', __name__)


def can_manage():
    return current_user.has_role('admin', 'super_admin')


@users_bp.route('/users')
@login_required
def index():
    if not can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.index'))

    search   = request.args.get('search', '')
    role_f   = request.args.get('role', '')
    status_f = request.args.get('status', '')

    q = User.query
    if search:
        q = q.filter(db.or_(
            User.username.ilike(f'%{search}%'),
            User.full_name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
        ))
    if role_f:   q = q.filter_by(role=role_f)
    if status_f: q = q.filter_by(status=status_f)

    users = q.order_by(User.id).all()
    return render_template('users/index.html', users=users,
                           search=search, role_f=role_f, status_f=status_f)


@users_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add():
    if not can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username  = request.form.get('username', '').strip()
        password  = request.form.get('password', '')
        role      = request.form.get('role', '')
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip()

        if current_user.role == 'admin' and role not in ('coordinator', 'trainer'):
            flash('Admins can only create Coordinators and Trainers.', 'danger')
            return redirect(url_for('users.add'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('users.add'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('users.add'))

        user = User(username=username, role=role, full_name=full_name,
                    email=email, status='active', created_by=current_user.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_action('Create User', f'Created user {username} with role {role}')
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('users.index'))

    allowed_roles = ['coordinator', 'trainer']
    if current_user.role == 'super_admin':
        allowed_roles = ['super_admin', 'admin', 'coordinator', 'trainer']
    return render_template('users/form.html', user=None, action='Add', allowed_roles=allowed_roles)


@users_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.index'))
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        user.full_name = request.form.get('full_name', '').strip()
        user.email     = request.form.get('email', '').strip()
        user.status    = request.form.get('status', 'active')
        if current_user.role == 'super_admin':
            user.role = request.form.get('role', user.role)
        db.session.commit()
        log_action('Edit User', f'Edited user {user.username}')
        flash('User updated.', 'success')
        return redirect(url_for('users.index'))

    allowed_roles = ['super_admin', 'admin', 'coordinator', 'trainer']
    return render_template('users/form.html', user=user, action='Edit', allowed_roles=allowed_roles)


@users_bp.route('/users/change-password/<int:id>', methods=['POST'])
@login_required
def change_password(id):
    if not current_user.has_role('super_admin'):
        flash('Only Super Admin can change passwords.', 'danger')
        return redirect(url_for('users.index'))
    user     = User.query.get_or_404(id)
    new_pass = request.form.get('new_password', '')
    if len(new_pass) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('users.index'))
    user.set_password(new_pass)
    db.session.commit()
    log_action('Change Password', f'Changed password for {user.username}')
    flash(f'Password changed for {user.username}.', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/users/toggle-status/<int:id>', methods=['POST'])
@login_required
def toggle_status(id):
    if not can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('users.index'))
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Cannot disable your own account.', 'danger')
        return redirect(url_for('users.index'))
    user.status = 'inactive' if user.status == 'active' else 'active'
    db.session.commit()
    log_action('Toggle User Status', f'Set {user.username} to {user.status}')
    flash(f'User {user.username} is now {user.status}.', 'success')
    return redirect(url_for('users.index'))
