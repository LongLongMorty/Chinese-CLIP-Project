import os
# 必须在任何 OpenMP/FAISS/PyTorch 导入前设置，避免 OMP 失点错误 #15
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from flask import Flask, request, jsonify, current_app, session, send_file
from flask_cors import CORS
from image_searcher import ImageSearcher
from io import BytesIO
from PIL import Image
from auth.routes import auth_bp
from flask_login import LoginManager, current_user
import os
import logging
import threading
from datetime import datetime
from auth.models import db, get_user_by_id, init_db
from auth.models import get_product_by_id, get_product_by_code, Product, User, Favorite
from auth.models import (
    BrowseHistory, ClickHistory, SearchHistory,
    record_browse, record_click, record_search, get_user_behavior_weights,
)
from query_expander import expand_query

app = Flask(__name__)
from flask_login import LoginManager
from flask_login import login_user, logout_user, login_required
# 初始化LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# 配置日志
logging.basicConfig(level=logging.INFO)

# 开启CORS支持

# 配置CORS
CORS(app,
    supports_credentials=True,
    origins=['http://localhost:5173', 'http://127.0.0.1:5173'],  # Vue开发服务器的URL
    allow_headers=['Content-Type', 'Authorization'],
    expose_headers=['Content-Type', 'X-CSRFToken'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
)
app.config['SESSION_TYPE'] = 'filesystem'  # 或使用其他会话存储
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 允许从同一站点发送 cookie
app.config['SESSION_COOKIE_SECURE'] = False  # 开发环境设为 False，生产环境设为 True
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止 JavaScript 访问 cookie
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 会话有效期（秒）
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_NAME'] = 'chinese_clip_session'
app.config['SESSION_PERMANENT'] = True
# 设置 secret_key
app.secret_key = os.getenv('SECRET_KEY', '114514')  # 替换 'your_unique_secret_key' 为一个安全的值

# 数据库配置 - 替换下面的连接信息为您的MySQL配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/image_search_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # 开发环境中可设置为True，查看SQL语句

# 初始化数据库连接
db.init_app(app)

# 配置路径
BASE_DIR = r"E:\Graduation_project"
# 微调权重
MODEL_PATH = os.path.join(BASE_DIR, "clip-data/pretrained_weights/chinese-clip-vit-base-patch16/clip_cn_vit-b-16.pt")
IMAGE_FEATURES_PATH = os.path.join(BASE_DIR, "clip-data/datasets/MUGE/json/train/train_imgs.img_feat.jsonl")
IMAGE_DIR = os.path.join(BASE_DIR, "clip-data/datasets/MUGE/extracted/imgs")

# 将路径存入app.config
app.config['MODEL_PATH'] = MODEL_PATH
app.config['IMAGE_FEATURES_PATH'] = IMAGE_FEATURES_PATH
app.config['IMAGE_DIR'] = IMAGE_DIR

# 初始化 LoginManager - 确保在蓝图注册前初始化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # 设置登录视图


# 定义未授权处理函数 - 这会处理需要登录的请求
@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"status": "error", "message": "Unauthorized access. Please login first."}), 401


# 定义 user_loader 函数
@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)  # 替换为你的用户加载逻辑


# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/auth')


# 添加请求前处理函数，记录当前时间和用户
@app.before_request
def before_request():
    # 更新当前时间
    app.config['CURRENT_TIME'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # 获取当前用户
    if current_user.is_authenticated:
        app.config['CURRENT_USER'] = current_user.username
    else:
        app.config['CURRENT_USER'] = 'guest'

# 标记搜索服务是否正在初始化
_search_service_ready = False
_search_service_error = None

def _init_search_service_background():
    """在后台线程中初始化搜索服务，避免阻塞 Flask 启动"""
    global _search_service_ready, _search_service_error
    with app.app_context():
        try:
            app.logger.info("[后台] 开始初始化搜索服务...")
            app.config['searcher'] = ImageSearcher(
                app.config['MODEL_PATH'],
                app.config['IMAGE_FEATURES_PATH'],
                app.config['IMAGE_DIR']
            )
            _search_service_ready = True
            app.logger.info("[后台] 搜索服务初始化完成，可以开始搜索")
        except Exception as e:
            _search_service_error = str(e)
            app.logger.error(f"[后台] 初始化搜索服务失败: {str(e)}")
            app.logger.exception(e)

# 初始化搜索服务 - 将在第一个请求到达前初始化
def init_search_service():
    """启动后台线程初始化搜索服务，Flask 可立即响应请求"""
    t = threading.Thread(target=_init_search_service_background, daemon=True)
    t.start()
    app.logger.info("搜索服务正在后台初始化，Flask 已就绪，请稍后再发起搜索请求...")


@app.route('/api/images/<product_code>')
def serve_image(product_code):
    """直接提供图片文件，避免 base64 编码开销"""
    img_dir = app.config.get('IMAGE_DIR')
    img_path = os.path.join(img_dir, f"{product_code}.jpg")
    if os.path.exists(img_path):
        return send_file(img_path, mimetype='image/jpeg')
    return jsonify({"status": "error", "message": "图片不存在"}), 404


@app.route('/api/search', methods=['POST'])
def search_images():
    data = request.get_json()
    query = data.get('query', '')
    top_k = int(data.get('top_k', 100))  # 默认值改为20

    if not query:
        return jsonify({"status": "error", "message": "查询文本不能为空"}), 400

    try:
        app.logger.info(f"执行文本搜索: '{query}', top_k={top_k}")

        # 获取searcher实例
        searcher = app.config.get('searcher')
        if not searcher:
            if _search_service_error:
                return jsonify({"status": "error", "message": f"搜索服务初始化失败: {_search_service_error}"}), 500
            return jsonify({"status": "error", "message": "搜索服务正在初始化中，请稍后重试（模型/索引加载需约1-3分钟）"}), 503

        # ── 查询扩展 ────────────────────────────────────────────────────────
        expanded_queries = expand_query(query, max_synonyms=2)
        app.logger.info(f"查询扩展: {expanded_queries}")

        # ── 多查询检索 + RRF 融合 ───────────────────────────────────────────
        if len(expanded_queries) > 1:
            fused_list = searcher.search_multi_query(expanded_queries, top_k=top_k * 3)
            # fused_list: [(product_code, rrf_score), ...]
            fused_codes = [code for code, _ in fused_list]
            fused_scores = {code: score for code, score in fused_list}
        else:
            indices_raw, distances_raw = searcher.search(query, top_k * 2)
            fused_codes = [
                searcher.index_manager.image_ids[idx]
                for idx in indices_raw
                if 0 <= idx < len(searcher.index_manager.image_ids)
            ]
            fused_scores = {
                searcher.index_manager.image_ids[idx]: float(dist)
                for idx, dist in zip(indices_raw, distances_raw)
                if 0 <= idx < len(searcher.index_manager.image_ids)
            }

        app.logger.info(f"融合后候选数: {len(fused_codes)}")

        # ── 异步记录搜索历史 ────────────────────────────────────────────────
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        elif '_user_id' in session:
            user_id = session['_user_id']
        elif 'user_id' in session:
            user_id = session['user_id']

        if user_id is not None:
            try:
                record_search(
                    user_id=user_id,
                    query=query,
                    expanded_queries=expanded_queries,
                    result_count=len(fused_codes),
                )
            except Exception:
                pass  # 记录失败不影响搜索返回

        # ── 构建返回结果 ────────────────────────────────────────────────────
        results = []
        img_dir = app.config.get('IMAGE_DIR')
        processed_code_set = set()

        for product_code in fused_codes:
            if product_code in processed_code_set:
                continue
            processed_code_set.add(product_code)

            img_path = os.path.join(img_dir, f"{product_code}.jpg")
            if not os.path.exists(img_path):
                app.logger.warning(f"图片不存在: {img_path}")
                continue

            description = f"商品 {product_code}"
            price = 0.0
            has_product_info = False

            try:
                product = get_product_by_code(str(product_code))
                if product:
                    description = product.description
                    price = product.price
                    has_product_info = True
            except Exception as e:
                app.logger.warning(f"获取商品信息时出错: {str(e)}")

            results.append({
                "product_code": str(product_code),
                "image_url": f"/api/images/{product_code}",
                "similarity": fused_scores.get(product_code, 0.0),
                "description": description,
                "price": price,
                "has_product_info": has_product_info,
            })
            app.logger.info(f"添加结果 #{len(results)}: 编码={product_code}")

            if len(results) >= top_k:
                break

        app.logger.info(f"最终返回 {len(results)} 个结果（扩展词: {expanded_queries}）")

        return jsonify({
            "status": "success",
            "results": results,
            "result_count": len(results),
            "expanded_queries": expanded_queries,
            "timestamp": app.config.get('CURRENT_TIME', datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            "user": app.config.get('CURRENT_USER', 'guest')
        })

    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        app.logger.error(f"搜索图片时出错: {str(e)}")
        app.logger.error(trace)
        return jsonify({"status": "error", "message": str(e), "traceback": trace}), 500

def get_product_by_code(product_code):
    """通过商品编码查询商品信息"""
    try:
        return db.session.query(Product).filter(Product.product_code == product_code).first()
    except Exception as e:
        app.logger.error(f"通过商品编码查询商品信息时出错: {str(e)}")
        return None


# 添加到收藏
@app.route('/api/favorites/add', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    data = request.get_json()
    product_code = data.get('product_code')
    user_id = session['user_id']

    if not product_code:
        return jsonify({"status": "error", "message": "缺少商品编号"}), 400

    try:
        # 检查商品是否存在
        product = Product.query.filter_by(product_code=product_code).first()
        if not product:
            return jsonify({"status": "error", "message": "商品不存在"}), 404

        # 检查是否已经收藏
        existing_favorite = Favorite.query.filter_by(
            user_id=user_id,
            product_code=product_code
        ).first()

        if existing_favorite:
            return jsonify({"status": "info", "message": "此商品已在收藏中"}), 200

        # 创建新收藏
        new_favorite = Favorite(
            user_id=user_id,
            product_code=product_code
        )

        db.session.add(new_favorite)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "成功添加到收藏",
            "favorite_id": new_favorite.id
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"添加收藏时出错: {str(e)}")
        return jsonify({"status": "error", "message": "添加收藏失败"}), 500


# 移除收藏
@app.route('/api/favorites/remove', methods=['POST'])
def remove_favorite():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    data = request.get_json()
    product_code = data.get('product_code')
    user_id = session['user_id']

    if not product_code:
        return jsonify({"status": "error", "message": "缺少商品编号"}), 400

    try:
        # 查找收藏记录
        favorite = Favorite.query.filter_by(
            user_id=user_id,
            product_code=product_code
        ).first()

        if not favorite:
            return jsonify({"status": "error", "message": "未找到该收藏记录"}), 404

        # 删除收藏
        db.session.delete(favorite)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "已从收藏中移除"
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"移除收藏时出错: {str(e)}")
        return jsonify({"status": "error", "message": "移除收藏失败"}), 500


# 获取用户收藏列表
@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    user_id = session['user_id']

    try:
        # 查询用户的所有收藏及对应的商品信息
        favorites_query = db.session.query(Favorite, Product) \
            .join(Product, Favorite.product_code == Product.product_code) \
            .filter(Favorite.user_id == user_id) \
            .order_by(Favorite.created_at.desc())

        favorites_list = []

        for favorite, product in favorites_query:
            # 添加到结果列表
            favorites_list.append({
                "favorite_id": favorite.id,
                "product_code": product.product_code,
                "description": product.description,
                "price": float(product.price) if product.price else 0,
                "image_url": f"/api/images/{product.product_code}",
                "created_at": favorite.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({
            "status": "success",
            "favorites": favorites_list,
            "count": len(favorites_list)
        }), 200

    except Exception as e:
        app.logger.error(f"获取收藏列表时出错: {str(e)}")
        return jsonify({"status": "error", "message": "获取收藏列表失败"}), 500


@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """检查用户认证状态"""
    app.logger.info(f"检查认证状态，会话内容: {dict(session)}")

    try:
        # 方法1: 使用Flask-Login的current_user
        if current_user.is_authenticated:
            user = User.query.get(current_user.id)
            app.logger.info(f"用户 {user.username} 认证成功 (通过current_user)")

            return jsonify({
                "status": "success",
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                }
            })

        # 方法2: 直接从会话中获取_user_id
        elif '_user_id' in session:
            user_id = session['_user_id']
            app.logger.info(f"用户ID从会话中获取: {user_id} (通过_user_id)")

            user = User.query.get(user_id)

            if not user:
                app.logger.warning(f"认证检查失败: 无法找到ID为{user_id}的用户")
                session.clear()  # 清除无效会话
                return jsonify({
                    "status": "error",
                    "authenticated": False,
                    "message": "用户不存在",
                    "debug_info": {"user_id": user_id}
                }), 401

            app.logger.info(f"用户 {user.username} 认证成功 (通过_user_id)")

            return jsonify({
                "status": "success",
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                }
            })

        else:
            app.logger.warning("认证检查失败: 会话中没有user_id或_user_id")
            return jsonify({
                "status": "error",
                "authenticated": False,
                "message": "未登录或会话已过期",
                "debug_info": {
                    "session_keys": list(session.keys()) if session else [],
                    "has_user_id": 'user_id' in session,
                    "has_flask_login_user_id": '_user_id' in session,
                    "cookie_received": bool(request.cookies)
                }
            }), 401
    except Exception as e:
        app.logger.exception("认证检查时出错")
        return jsonify({
            "status": "error",
            "message": f"服务器错误: {str(e)}",
            "authenticated": False
        }), 500
@app.route('/auth/refresh', methods=['POST'])
def refresh_session():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({"status": "error", "message": "缺少用户名"}), 400

    # 查找用户
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"status": "error", "message": "用户不存在"}), 404

    # 如果用户存在，刷新会话
    session['user_id'] = user.id
    session['username'] = user.username
    session.permanent = True

    return jsonify({
        "status": "success",
        "message": "会话已刷新",
        "user": {
            "id": user.id,
            "username": user.username
        }
    })


@app.route('/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    try:
        # 使用Flask-Login登出用户
        logout_user()

        # 额外清除会话
        session.clear()

        return jsonify({
            "status": "success",
            "message": "已成功登出"
        })
    except Exception as e:
        app.logger.exception(f"登出过程中出错")
        return jsonify({"status": "error", "message": f"服务器错误: {str(e)}"}), 500


# ─── 推荐接口 ────────────────────────────────────────────────────────────────
@app.route('/api/recommend', methods=['GET'])
def recommend():
    """
    基于用户多维行为（收藏 1.0 > 点击 0.6 > 浏览 0.3）构建加权偏好向量，
    通过 FAISS 检索相似商品，过滤已交互商品后返回推荐结果。
    未登录时返回 401；无行为数据时返回空列表。
    """
    # ── 鉴权 ──────────────────────────────────────────────────────────────────
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    elif '_user_id' in session:
        user_id = session['_user_id']
    elif 'user_id' in session:
        user_id = session['user_id']

    if user_id is None:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    top_k = int(request.args.get('top_k', 20))

    try:
        # ── 搜索服务是否就绪 ────────────────────────────────────────────────────
        searcher = app.config.get('searcher')
        if not searcher:
            if _search_service_error:
                return jsonify({"status": "error",
                                "message": f"搜索服务初始化失败: {_search_service_error}"}), 500
            return jsonify({"status": "error",
                            "message": "搜索服务正在初始化中，请稍后重试（约1-3分钟）"}), 503

        # ── 汇总行为权重 ────────────────────────────────────────────────────────
        weighted_codes = get_user_behavior_weights(user_id)

        if not weighted_codes:
            return jsonify({
                "status": "success",
                "results": [],
                "message": "暂无行为数据，无法生成推荐。请先浏览、点击或收藏一些商品！"
            }), 200

        # 所有交互过的商品都排除在推荐之外
        exclude_codes = set(weighted_codes.keys())

        app.logger.info(
            f"为用户 {user_id} 生成推荐：行为商品 {len(weighted_codes)} 件，"
            f"排除 {len(exclude_codes)} 件"
        )

        # ── 加权向量推荐 ────────────────────────────────────────────────────────
        indices, distances = searcher.recommend_by_weighted_codes(
            weighted_codes, top_k=top_k, exclude_codes=exclude_codes
        )

        if not indices:
            return jsonify({
                "status": "success",
                "results": [],
                "message": "暂时无法为您生成推荐，请稍后再试"
            }), 200

        # ── 构建返回结果 ────────────────────────────────────────────────────────
        img_dir = app.config.get('IMAGE_DIR')
        results = []
        for idx, dist in zip(indices, distances):
            try:
                product_code = searcher.index_manager.image_ids[idx]
                img_path = os.path.join(img_dir, f"{product_code}.jpg")
                if not os.path.exists(img_path):
                    continue

                description = f"商品 {product_code}"
                price = 0.0
                has_product_info = False

                try:
                    product = get_product_by_code(str(product_code))
                    if product:
                        description = product.description
                        price = product.price
                        has_product_info = True
                except Exception as e:
                    app.logger.warning(f"获取商品信息时出错: {str(e)}")

                results.append({
                    "product_code": str(product_code),
                    "image_url": f"/api/images/{product_code}",
                    "similarity": float(dist),
                    "description": description,
                    "price": price,
                    "has_product_info": has_product_info,
                })
            except Exception as e:
                app.logger.error(f"处理推荐结果索引 {idx} 出错: {str(e)}")
                continue

        # 收藏件数（仅用于前端展示）
        fav_count = Favorite.query.filter_by(user_id=user_id).count()
        app.logger.info(f"为用户 {user_id} 生成推荐 {len(results)} 条")
        return jsonify({
            "status": "success",
            "results": results,
            "result_count": len(results),
            "based_on_count": len(weighted_codes),
            "favorite_count": fav_count,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }), 200

    except Exception as e:
        import traceback
        app.logger.error(f"生成推荐时出错: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─── 用户行为追踪接口 ─────────────────────────────────────────────────────────

def _get_current_user_id():
    """统一获取当前登录用户 ID，未登录返回 None"""
    if current_user.is_authenticated:
        return current_user.id
    if '_user_id' in session:
        return session['_user_id']
    if 'user_id' in session:
        return session['user_id']
    return None


@app.route('/api/behavior/browse', methods=['POST'])
def track_browse():
    """
    记录浏览行为。
    Body: { product_code: str, duration: int (秒，可选，默认 0) }
    """
    user_id = _get_current_user_id()
    if user_id is None:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    data = request.get_json() or {}
    product_code = data.get('product_code')
    duration = int(data.get('duration', 0))

    if not product_code:
        return jsonify({"status": "error", "message": "缺少 product_code"}), 400

    record = record_browse(user_id, product_code, duration)
    if record is None:
        return jsonify({"status": "error", "message": "记录失败"}), 500

    return jsonify({"status": "success", "message": "浏览记录已更新"}), 200


@app.route('/api/behavior/click', methods=['POST'])
def track_click():
    """
    记录点击行为。
    Body: { product_code: str }
    """
    user_id = _get_current_user_id()
    if user_id is None:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    data = request.get_json() or {}
    product_code = data.get('product_code')

    if not product_code:
        return jsonify({"status": "error", "message": "缺少 product_code"}), 400

    record = record_click(user_id, product_code)
    if record is None:
        return jsonify({"status": "error", "message": "记录失败"}), 500

    return jsonify({"status": "success", "message": "点击记录已更新", "click_count": record.click_count}), 200


@app.route('/api/behavior/search-history', methods=['GET'])
def get_search_history():
    """
    获取当前用户的搜索历史（最近 20 条）。
    """
    user_id = _get_current_user_id()
    if user_id is None:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    try:
        import json as _json
        records = (
            SearchHistory.query
            .filter_by(user_id=user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(20)
            .all()
        )
        history = [
            {
                "query": r.query,
                "expanded_queries": _json.loads(r.expanded_queries) if r.expanded_queries else [],
                "result_count": r.result_count,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in records
        ]
        return jsonify({"status": "success", "history": history, "count": len(history)}), 200
    except Exception as e:
        app.logger.error(f"获取搜索历史失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/behavior/browse-history', methods=['GET'])
def get_browse_history():
    """获取当前用户的浏览历史（按浏览时长降序，最多 30 条）"""
    user_id = _get_current_user_id()
    if user_id is None:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    try:
        records = (
            BrowseHistory.query
            .filter_by(user_id=user_id)
            .order_by(BrowseHistory.duration.desc())
            .limit(30)
            .all()
        )
        img_dir = app.config.get('IMAGE_DIR', '')
        history = []
        for r in records:
            item = {
                "product_code": r.product_code,
                "duration": r.duration,
                "image_url": f"/api/images/{r.product_code}",
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else None,
            }
            try:
                p = get_product_by_code(r.product_code)
                if p:
                    item["description"] = p.description
                    item["price"] = p.price
            except Exception:
                pass
            history.append(item)
        return jsonify({"status": "success", "history": history, "count": len(history)}), 200
    except Exception as e:
        app.logger.error(f"获取浏览历史失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# 检查商品是否已收藏
@app.route('/api/favorites/check', methods=['POST'])
def check_favorite():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    data = request.get_json()
    product_code = data.get('product_code')
    user_id = session['user_id']

    if not product_code:
        return jsonify({"status": "error", "message": "缺少商品编号"}), 400

    try:
        # 检查是否已收藏
        favorite = Favorite.query.filter_by(
            user_id=user_id,
            product_code=product_code
        ).first()

        is_favorite = favorite is not None

        return jsonify({
            "status": "success",
            "is_favorite": is_favorite
        }), 200

    except Exception as e:
        app.logger.error(f"检查收藏状态时出错: {str(e)}")
        return jsonify({"status": "error", "message": "检查收藏状态失败"}), 500


@app.route('/api/image-search', methods=['POST'])
def search_by_image():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "未上传图片"}), 400

    image_file = request.files['image']
    top_k = int(request.form.get('top_k', 20))

    try:
        app.logger.info(f"执行图片搜索: top_k={top_k}")

        searcher = app.config.get('searcher')
        if not searcher:
            if _search_service_error:
                return jsonify({"status": "error", "message": f"搜索服务初始化失败: {_search_service_error}"}), 500
            return jsonify({"status": "error", "message": "搜索服务正在初始化中，请稍后重试（模型/索引加载需约1-3分钟）"}), 503

        # 用 FileStorage.save() 写入临时文件，再由 PIL 打开
        import tempfile
        suffix = os.path.splitext(image_file.filename or 'upload.jpg')[1] or '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            image_file.save(tmp)
            tmp_path = tmp.name
        try:
            app.logger.info(f"收到图片: filename={image_file.filename}, 大小={os.path.getsize(tmp_path)} 字节")
            img = Image.open(tmp_path).convert('RGB')
            app.logger.info(f"读取上传的图片, 尺寸: {img.size}")
        finally:
            os.unlink(tmp_path)

        indices, distances = searcher.search_by_image(img, top_k * 2)
        app.logger.info(f"搜索返回 {len(indices)} 个结果")

        results = []
        img_dir = app.config.get('IMAGE_DIR')

        for i, (idx, dist) in enumerate(zip(indices, distances)):
            try:
                if idx < 0 or idx >= len(searcher.index_manager.image_ids):
                    app.logger.warning(f"跳过无效索引: {idx}")
                    continue

                product_code = searcher.index_manager.image_ids[idx]
                img_path = os.path.join(img_dir, f"{product_code}.jpg")

                if not os.path.exists(img_path):
                    app.logger.warning(f"图片不存在: {img_path}")
                    continue

                description = f"商品 {product_code}"
                price = 0.0
                has_product_info = False

                try:
                    product = get_product_by_code(str(product_code))
                    if product:
                        description = product.description
                        price = product.price
                        has_product_info = True
                except Exception as e:
                    app.logger.warning(f"获取商品信息时出错: {str(e)}")

                results.append({
                    "product_code": str(product_code),
                    "image_url": f"/api/images/{product_code}",
                    "similarity": float(dist),
                    "description": description,
                    "price": price,
                    "has_product_info": has_product_info
                })

                if len(results) >= top_k:
                    break

            except Exception as e:
                app.logger.error(f"处理索引 {idx} 时出错: {str(e)}")
                continue

        app.logger.info(f"最终返回 {len(results)} 个结果")
        return jsonify({
            "status": "success",
            "results": results,
            "result_count": len(results),
            "timestamp": app.config.get('CURRENT_TIME', datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            "user": app.config.get('CURRENT_USER', 'guest')
        })

    except Exception as e:
        import traceback
        app.logger.error(f"图片搜索时出错: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        app.logger.info(f"尝试登录用户: {username}")

        if not username or not password:
            return jsonify({"status": "error", "message": "请提供用户名和密码"}), 400

        # 查找用户
        user = User.query.filter_by(username=username).first()

        if not user:
            app.logger.warning(f"登录失败: 用户 {username} 不存在")
            return jsonify({"status": "error", "message": "用户名或密码错误"}), 401

        # 验证密码
        if not user.check_password(password):
            app.logger.warning(f"登录失败: 用户 {username} 密码错误")
            return jsonify({"status": "error", "message": "用户名或密码错误"}), 401

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()

        # 使用Flask-Login登录用户
        login_user(user, remember=True)

        app.logger.info(f"用户 {username} 登录成功，ID: {user.id}")
        app.logger.debug(f"会话已设置: {dict(session)}")

        # 返回用户信息
        response = jsonify({
            "status": "success",
            "message": "登录成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            },
            "debug_info": {
                "session_id": request.cookies.get(app.config['SESSION_COOKIE_NAME']),
                "session_keys": list(session.keys())
            }
        })

        return response
    except Exception as e:
        app.logger.exception(f"登录过程中出错")
        return jsonify({"status": "error", "message": f"服务器错误: {str(e)}"}), 500

# 根路由 - 增加更多信息
@app.route('/', methods=['GET', 'OPTIONS'])
def root():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify({"status": "success", "message": "Preflight request successful"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # 返回当前时间和服务器状态
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({
        "status": "success",
        "message": "欢迎使用Chinese-CLIP商品检索API",
        "server_time": current_time,
        "endpoints": {
            "login": "/auth/login",
            "logout": "/auth/logout",
            "check_auth": "/auth/user/check-auth",
            "search": "/api/search",
            "image_search": "/api/image-search",
            "product_details": "/api/products/<product_id>",
            "product_by_code": "/api/products/code/<product_code>"
        }
    })


# 健康检查端点 - 用于监控服务状态
@app.route('/health', methods=['GET'])
def health_check():
    if _search_service_ready:
        search_status = "online"
    elif _search_service_error:
        search_status = f"error: {_search_service_error}"
    else:
        search_status = "initializing"
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "user": app.config.get('CURRENT_USER', 'guest'),
        "components": {
            "database": "online",
            "search_service": search_status
        }
    })


# 获取单个商品详情
@app.route('/api/products/<product_id>', methods=['GET'])
def get_product_details(product_id):
    try:
        # 从数据库获取商品信息
        product = get_product_by_id(product_id)
        if not product:
            return jsonify({"status": "error", "message": "商品不存在"}), 404

        # 创建结果对象
        result = {
            "image_id": product_id,
            "product_code": product.product_code,
            "image_url": f"/api/images/{product.product_code}",
            "description": product.description,
            "price": product.price,
            "created_at": product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else None
        }

        return jsonify({
            "status": "success",
            "product": result,
            "timestamp": app.config.get('CURRENT_TIME', datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            "user": app.config.get('CURRENT_USER', 'guest')
        })

    except Exception as e:
        app.logger.error(f"获取商品详情时出错: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# 根据商品编号获取商品
@app.route('/api/products/code/<product_code>', methods=['GET'])
def get_product_by_product_code(product_code):
    try:
        # 从数据库获取商品信息
        product = get_product_by_code(product_code)
        if not product:
            return jsonify({"status": "error", "message": "商品不存在"}), 404

        # 创建结果对象
        result = {
            "image_id": product.id,
            "product_code": product.product_code,
            "image_url": f"/api/images/{product.product_code}",
            "description": product.description,
            "price": product.price,
            "created_at": product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else None
        }

        return jsonify({
            "status": "success",
            "product": result,
            "timestamp": app.config.get('CURRENT_TIME', datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            "user": app.config.get('CURRENT_USER', 'guest')
        })

    except Exception as e:
        app.logger.error(f"获取商品详情时出错: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# 创建命令行命令来初始化数据库
@app.cli.command('init-db')
def init_db_command():
    """初始化数据库表结构"""
    with app.app_context():
        db.create_all()
        print('数据库表已创建')


if __name__ == '__main__':
    # 创建数据库表
    ''' 
    with app.app_context():
        db.create_all()
        app.logger.info("数据库表已创建")
    '''
    # 提供更多日志信息
    app.logger.info(f"启动API服务器，端口: 5000")
    # 在后台线程初始化搜索服务（不阻塞 Flask 启动）
    init_search_service()
    # 开发环境使用
    app.run(debug=False, host='0.0.0.0', port=5000)

    # 生产环境使用
    # app.run(debug=False, host='0.0.0.0', port=5000)
