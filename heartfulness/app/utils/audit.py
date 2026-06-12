from flask import request
from flask_login import current_user
from app.models import AuditLog
from app import db


def log_action(action, description=''):
    try:
        log = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            username=current_user.username if current_user.is_authenticated else 'system',
            role=current_user.role if current_user.is_authenticated else 'system',
            action=action,
            description=description,
            ip_address=request.remote_addr if request else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
