from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.utils.audit import log_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.status == 'active':
            login_user(user, remember=False)
            log_action('Login', f'User {username} logged in successfully.')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username or password.', 'danger')
            log_action('Login Failed', f'Failed login attempt for username: {username}')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_action('Logout', f'User {current_user.username} logged out.')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/set-theme', methods=['POST'])
@login_required
def set_theme():
    from app import db
    theme = request.form.get('theme', 'light')
    current_user.theme = theme
    db.session.commit()
    return {'status': 'ok'}
