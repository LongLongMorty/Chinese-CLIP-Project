from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from .models import get_user_by_username, get_user_by_email, User, db
import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', False)

    # 记录登录尝试
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"登录尝试 - 时间: {now_utc}, 用户: {username}")

    # 尝试通过用户名查找用户
    user = get_user_by_username(username)

    # 如果未找到，尝试通过邮箱查找
    if not user and '@' in username:
        user = get_user_by_email(username)

    if user and user.check_password(password):
        # 更新最后登录时间
        user.update_last_login()

        # 登录用户
        login_user(user, remember=remember)

        # 返回登录成功信息和重定向URL
        return jsonify({
            "status": "success",
            "message": "登录成功",
            "redirect": "/ImageSearch",  # 前端路由路径
            "user": user.to_dict()
        }), 200

    return jsonify({"status": "error", "message": "用户名或密码错误"}), 401


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success", "message": "退出登录成功"})


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    # 检查用户名是否已存在
    if get_user_by_username(username):
        return jsonify({"status": "error", "message": "用户名已被使用"}), 400

    # 如果提供了邮箱，检查邮箱是否已存在
    if email and get_user_by_email(email):
        return jsonify({"status": "error", "message": "邮箱已被注册"}), 400

    # 创建新用户
    new_user = User(username=username, password=password, email=email)
    db.session.add(new_user)

    try:
        db.session.commit()
        # 自动登录新注册用户
        login_user(new_user)
        return jsonify({
            "status": "success",
            "message": "注册成功",
            "redirect": "/ImageSearch",
            "user": new_user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"注册失败: {str(e)}"}), 500


@auth_bp.route('/user/current', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    return jsonify({
        "status": "success",
        "user": current_user.to_dict()
    })


@auth_bp.route('/user/check-auth', methods=['GET'])
def check_auth():
    """检查用户是否已认证"""
    if current_user.is_authenticated:
        return jsonify({
            "status": "success",
            "authenticated": True,
            "user": current_user.to_dict()
        })
    return jsonify({"status": "success", "authenticated": False}), 200