from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Association table for Member-Category many-to-many relationship
member_category = db.Table('member_category',
    db.Column('member_id', db.Integer, db.ForeignKey('members.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # super_admin, admin, coordinator, trainer
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    status = db.Column(db.String(10), default='active')  # active, inactive
    theme = db.Column(db.String(10), default='light')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

    def can(self, permission):
        perms = {
            'super_admin': ['all'],
            'admin': ['manage_members', 'import_csv', 'manage_sessions', 'mark_attendance',
                      'view_reports', 'manage_users', 'reopen_attendance'],
            'coordinator': ['manage_members', 'import_csv', 'manage_sessions', 'mark_attendance',
                            'view_reports', 'reopen_attendance'],
            'trainer': ['manage_members', 'import_csv', 'manage_sessions', 'mark_attendance', 'view_reports'],
        }
        role_perms = perms.get(self.role, [])
        return 'all' in role_perms or permission in role_perms

    @property
    def role_display(self):
        return self.role.replace('_', ' ').title()


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(10), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    religion = db.Column(db.String(50))
    mobile_number = db.Column(db.String(15))
    area = db.Column(db.String(100))
    join_date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(10), default='active')  # active, inactive
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categories = db.relationship('Category', secondary=member_category, backref=db.backref('members', lazy='dynamic'))
    attendance_records = db.relationship('Attendance', backref='member', lazy='dynamic')

    @staticmethod
    def generate_member_id():
        last = Member.query.order_by(Member.id.desc()).first()
        if last:
            num = int(last.member_id[1:]) + 1
        else:
            num = 1
        return f'M{num:04d}'


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    status = db.Column(db.String(10), default='active')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def active_member_count(self):
        return self.members.filter_by(status='active').count()

    @property
    def inactive_member_count(self):
        return self.members.filter_by(status='inactive').count()

    @property
    def total_member_count(self):
        return self.members.count()


class SessionCategory(db.Model):
    __tablename__ = 'session_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    status = db.Column(db.String(10), default='active')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship('Session', backref='category', lazy='dynamic')


class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(10), unique=True, nullable=False)
    session_name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('session_categories.id'))
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    venue = db.Column(db.String(150))
    status = db.Column(db.String(15), default='scheduled')  # draft, scheduled, completed, cancelled
    attendance_locked = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attendance_records = db.relationship('Attendance', backref='session', lazy='dynamic')

    @staticmethod
    def generate_session_id():
        last = Session.query.order_by(Session.id.desc()).first()
        if last:
            num = int(last.session_id[1:]) + 1
        else:
            num = 1
        return f'S{num:04d}'


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    status = db.Column(db.String(10), default='absent')  # present, absent
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('session_id', 'member_id', name='unique_session_member'),)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(50))
    role = db.Column(db.String(20))
    action = db.Column(db.String(100))
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs', foreign_keys=[user_id])


class ImportHistory(db.Model):
    __tablename__ = 'import_history'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    imported_count = db.Column(db.Integer, default=0)
    duplicate_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    imported_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    importer = db.relationship('User', backref='imports', foreign_keys=[imported_by])
