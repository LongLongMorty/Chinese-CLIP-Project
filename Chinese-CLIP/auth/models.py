from flask import Flask
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import random
import sadisplay
# 初始化 SQLAlchemy 和 Bcrypt
db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model, UserMixin):
    """用户数据模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __init__(self, username, password, email=None, role='user'):
        self.username = username
        self.set_password(password)
        self.email = email
        self.role = role

    def set_password(self, password):
        """设置加密密码"""
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """验证密码"""
        return bcrypt.check_password_hash(self.password, password)

    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """将用户对象转换为字典（用于JSON响应）"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }

    def get_id(self):
        """用于Flask-Login的用户ID"""
        return str(self.id)


class Product(db.Model):
    """商品数据模型"""
    __tablename__ = 'products'

    id = db.Column(db.String(64), primary_key=True)  # 商品ID，对应pairs文件第一列
    description = db.Column(db.String(255), nullable=True)  # 商品描述，对应pairs文件第二列
    product_code = db.Column(db.String(64), index=True, nullable=False)  # 商品编号，对应pairs文件第三列
    price = db.Column(db.Float, default=0.0)  # 商品价格，随机生成
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """将商品对象转换为字典（用于JSON响应）"""
        return {
            'id': self.id,
            'description': self.description,
            'product_code': self.product_code,
            'price': self.price,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_code = db.Column(db.String(50), db.ForeignKey('products.product_code'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 只在这里定义关系
    user = db.relationship('User', backref=db.backref('favorites', lazy='dynamic', cascade='all, delete-orphan'))
    # 确保用户只能收藏同一商品一次
    __table_args__ = (db.UniqueConstraint('user_id', 'product_code', name='uix_user_product'),)


class BrowseHistory(db.Model):
    """浏览历史记录（权重 0.3）"""
    __tablename__ = 'browse_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_code = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, default=0)   # 累计浏览时长（秒）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship(
        'User',
        backref=db.backref('browse_history', lazy='dynamic', cascade='all, delete-orphan')
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_code', name='uix_browse_user_product'),
    )


class ClickHistory(db.Model):
    """点击历史记录（权重 0.6）"""
    __tablename__ = 'click_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_code = db.Column(db.String(50), nullable=False)
    click_count = db.Column(db.Integer, default=1)   # 累计点击次数
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship(
        'User',
        backref=db.backref('click_history', lazy='dynamic', cascade='all, delete-orphan')
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_code', name='uix_click_user_product'),
    )


class SearchHistory(db.Model):
    """搜索历史记录"""
    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    expanded_queries = db.Column(db.Text, nullable=True)   # JSON 存储扩展后的查询词组
    result_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(
        'User',
        backref=db.backref('search_history', lazy='dynamic', cascade='all, delete-orphan')
    )


# 用户相关函数
def get_user_by_username(username):
    """根据用户名获取用户"""
    return User.query.filter_by(username=username).first()


def get_user_by_email(email):
    """根据邮箱获取用户"""
    return User.query.filter_by(email=email).first()


def get_user_by_id(user_id):
    """根据用户ID获取用户"""
    return User.query.get(int(user_id))


def add_user(username, password, email=None, role='user'):
    """添加新用户"""
    # 检查用户名是否已存在
    if get_user_by_username(username):
        return False

    # 如果提供了邮箱，检查邮箱是否已存在
    if email and get_user_by_email(email):
        return False

    # 创建新用户
    new_user = User(username=username, password=password, email=email, role=role)
    db.session.add(new_user)

    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"添加用户失败: {e}")
        return False


# 商品相关函数
def get_product_by_id(product_id):
    """根据ID获取商品"""
    return Product.query.get(product_id)


def get_product_by_code(product_code):
    """根据商品编号获取商品"""
    return Product.query.filter_by(product_code=product_code).first()


def get_products_by_category(category_id, page=1, per_page=20):
    """根据类别获取商品列表（分页）"""
    # 这里假设我们使用商品编号的前3位作为类别
    like_pattern = f"{category_id}%"
    return Product.query.filter(Product.product_code.like(like_pattern)).paginate(
        page=page, per_page=per_page, error_out=False
    )


def add_product(product_id, description, product_code, price=None):
    """添加新商品"""
    # 检查商品是否已存在
    existing_product = get_product_by_id(product_id)
    if existing_product:
        return existing_product

    # 如果没有提供价格，生成随机价格
    if price is None:
        price = random.uniform(1, 10000)
        price = round(price, 2)  # 保留两位小数

    # 创建新商品
    new_product = Product(
        id=product_id,
        description=description,
        product_code=product_code,
        price=price
    )
    db.session.add(new_product)

    try:
        db.session.commit()
        return new_product
    except Exception as e:
        db.session.rollback()
        print(f"添加商品失败: {e}")
        return None


def init_db():
    """初始化数据库，创建表和默认用户"""
    # 创建所有表（包含 browse_history / click_history / search_history）
    db.create_all()

    # 检查是否需要创建默认用户
    if not get_user_by_username('admin'):
        add_user('admin', 'admin123', email='admin@example.com', role='admin')
        print("已创建管理员用户")

    if not get_user_by_username('LongLongMorty'):
        add_user('LongLongMorty', 'password123', role='user')
        print("已创建默认用户")

    print("数据库初始化完成！")


# ── 行为数据辅助函数 ──────────────────────────────────────────────────────────

def record_browse(user_id: int, product_code: str, duration: int = 0):
    """记录或更新浏览记录，累加浏览时长"""
    record = BrowseHistory.query.filter_by(
        user_id=user_id, product_code=product_code
    ).first()
    if record:
        record.duration += duration
        record.updated_at = datetime.utcnow()
    else:
        record = BrowseHistory(
            user_id=user_id,
            product_code=product_code,
            duration=duration,
        )
        db.session.add(record)
    try:
        db.session.commit()
        return record
    except Exception as e:
        db.session.rollback()
        print(f"记录浏览历史失败: {e}")
        return None


def record_click(user_id: int, product_code: str):
    """记录或更新点击记录，累加点击次数"""
    record = ClickHistory.query.filter_by(
        user_id=user_id, product_code=product_code
    ).first()
    if record:
        record.click_count += 1
        record.updated_at = datetime.utcnow()
    else:
        record = ClickHistory(user_id=user_id, product_code=product_code, click_count=1)
        db.session.add(record)
    try:
        db.session.commit()
        return record
    except Exception as e:
        db.session.rollback()
        print(f"记录点击历史失败: {e}")
        return None


def record_search(user_id: int, query: str, expanded_queries: list = None, result_count: int = 0):
    """记录搜索历史"""
    import json
    record = SearchHistory(
        user_id=user_id,
        query=query,
        expanded_queries=json.dumps(expanded_queries, ensure_ascii=False) if expanded_queries else None,
        result_count=result_count,
    )
    db.session.add(record)
    try:
        db.session.commit()
        return record
    except Exception as e:
        db.session.rollback()
        print(f"记录搜索历史失败: {e}")
        return None


def get_user_behavior_weights(user_id: int, top_n: int = 50):
    """
    汇总用户行为，返回加权的 {product_code: weight} 字典。
    权重规则：收藏 1.0 > 点击 0.6 > 浏览 0.3
    点击权重随点击次数对数增长，浏览权重随浏览时长对数增长。
    """
    import math

    weights: dict = {}

    # 收藏（最高权重 1.0）
    favs = Favorite.query.filter_by(user_id=user_id).all()
    for fav in favs:
        weights[fav.product_code] = weights.get(fav.product_code, 0.0) + 1.0

    # 点击（权重 0.6，随次数对数增长）
    clicks = ClickHistory.query.filter_by(user_id=user_id) \
        .order_by(ClickHistory.click_count.desc()).limit(top_n).all()
    for c in clicks:
        bonus = 0.6 * (1 + math.log(c.click_count + 1, 10))
        weights[c.product_code] = weights.get(c.product_code, 0.0) + bonus

    # 浏览（权重 0.3，随时长对数增长，最低保底）
    browses = BrowseHistory.query.filter_by(user_id=user_id) \
        .order_by(BrowseHistory.duration.desc()).limit(top_n).all()
    for b in browses:
        bonus = 0.3 * (1 + math.log(max(b.duration, 1) + 1, 10))
        weights[b.product_code] = weights.get(b.product_code, 0.0) + bonus

    return weights
