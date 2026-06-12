from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import Category, Member, Session, Attendance, SessionCategory
from app import db
from app.utils.audit import log_action

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/categories')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_f = request.args.get('status', '')

    q = Category.query
    if search:
        q = q.filter(Category.name.ilike(f'%{search}%'))
    if status_f:
        q = q.filter_by(status=status_f)

    categories = q.order_by(Category.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('categories/index.html', categories=categories, search=search, status_f=status_f)


@categories_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        desc = request.form.get('description', '').strip()
        
        if not name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('categories.add'))
        
        if Category.query.filter_by(name=name).first():
            flash('Category already exists.', 'warning')
            return redirect(url_for('categories.add'))
        
        cat = Category(name=name, description=desc, status='active', created_by=current_user.id)
        db.session.add(cat)
        db.session.commit()
        log_action('Create Category', f'Created member category: {name}')
        flash('Category created successfully.', 'success')
        return redirect(url_for('categories.index'))
    
    return render_template('categories/form.html', category=None, action='Add')


@categories_bp.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    cat = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        cat.name = request.form.get('name', '').strip()
        cat.description = request.form.get('description', '').strip()
        cat.status = request.form.get('status', 'active')
        db.session.commit()
        log_action('Edit Category', f'Edited category: {cat.name}')
        flash('Category updated.', 'success')
        return redirect(url_for('categories.index'))
    
    return render_template('categories/form.html', category=cat, action='Edit')


@categories_bp.route('/categories/view/<int:id>')
@login_required
def view(id):
    cat = Category.query.get_or_404(id)
    
    # Get analytics
    total_members = cat.total_member_count
    active_members = cat.active_member_count
    inactive_members = cat.inactive_member_count
    
    # Calculate attendance percentage
    # Find sessions where category members attended
    sessions_query = db.session.query(Session).join(SessionCategory).filter(
        SessionCategory.name == cat.name, Session.status == 'completed'
    ).all()
    
    total_attendance = 0
    present_attendance = 0
    for s in sessions_query:
        total = Attendance.query.filter_by(session_id=s.id).count()
        present = Attendance.query.filter_by(session_id=s.id, status='present').count()
        total_attendance += total
        present_attendance += present
    
    attendance_pct = round(present_attendance / total_attendance * 100, 1) if total_attendance > 0 else 0
    total_sessions = len(sessions_query)
    
    # Get recent members in this category
    members = cat.members.filter_by(status='active').order_by(Member.created_at.desc()).limit(15).all()
    
    return render_template('categories/view.html', category=cat,
                           total_members=total_members, active_members=active_members,
                           inactive_members=inactive_members, attendance_pct=attendance_pct,
                           total_sessions=total_sessions, members=members)


@categories_bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    cat = Category.query.get_or_404(id)
    cat.status = 'inactive'
    db.session.commit()
    log_action('Disable Category', f'Disabled category: {cat.name}')
    flash(f'Category {cat.name} has been disabled.', 'success')
    return redirect(url_for('categories.index'))
