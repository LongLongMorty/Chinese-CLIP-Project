from functools import wraps
from flask import jsonify
from flask_login import current_user


def role_required(role):
    """检查用户是否具有特定角色的装饰器"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"status": "error", "message": "需要登录"}), 401

            if current_user.role != role and role != "any":
                return jsonify({"status": "error", "message": "权限不足"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator