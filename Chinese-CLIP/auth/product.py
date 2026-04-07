"""
产品模块 - 提供商品相关的功能和查询方法

该模块通过auth.models导入Product模型，并扩展了一系列产品查询和操作功能。
"""
from datetime import datetime
from sqlalchemy import func, desc, asc
from typing import List, Dict, Any, Optional, Tuple, Union

# 从models.py导入已定义的Product类和基本函数
from .models import db, Product, get_product_by_id, get_product_by_code, add_product


# 扩展产品查询功能

def search_products(query: str, limit: int = 10) -> List[Product]:
    """
    搜索商品 - 根据关键词搜索商品描述

    Args:
        query: 搜索关键词
        limit: 返回结果数量限制

    Returns:
        匹配的商品列表
    """
    search_term = f"%{query}%"
    return Product.query.filter(Product.description.like(search_term)).limit(limit).all()


def get_products_by_price_range(min_price: float, max_price: float,
                                page: int = 1, per_page: int = 20) -> Tuple[List[Product], int]:
    """
    根据价格范围获取商品

    Args:
        min_price: 最低价格
        max_price: 最高价格
        page: 页码
        per_page: 每页数量

    Returns:
        (商品列表, 总数)
    """
    query = Product.query.filter(
        Product.price >= min_price,
        Product.price <= max_price
    )

    # 获取总数
    total = query.count()

    # 分页
    products = query.order_by(Product.price.asc()) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()

    return products, total


def get_random_products(count: int = 5) -> List[Product]:
    """
    获取随机商品

    Args:
        count: 获取数量

    Returns:
        随机商品列表
    """
    return Product.query.order_by(func.random()).limit(count).all()


def get_products_by_ids(product_ids: List[str]) -> List[Product]:
    """
    根据多个ID批量获取商品

    Args:
        product_ids: 商品ID列表

    Returns:
        商品对象列表
    """
    if not product_ids:
        return []
    return Product.query.filter(Product.id.in_(product_ids)).all()


def get_latest_products(limit: int = 10) -> List[Product]:
    """
    获取最新添加的商品

    Args:
        limit: 返回数量限制

    Returns:
        最新商品列表
    """
    return Product.query.order_by(desc(Product.created_at)).limit(limit).all()


def get_highest_price_products(limit: int = 10) -> List[Product]:
    """
    获取价格最高的商品

    Args:
        limit: 返回数量限制

    Returns:
        价格最高的商品列表
    """
    return Product.query.order_by(desc(Product.price)).limit(limit).all()


def get_lowest_price_products(limit: int = 10) -> List[Product]:
    """
    获取价格最低的商品

    Args:
        limit: 返回数量限制

    Returns:
        价格最低的商品列表
    """
    return Product.query.order_by(asc(Product.price)).limit(limit).all()


def get_products_with_prefix(prefix: str, limit: int = 20) -> List[Product]:
    """
    获取商品编号以特定前缀开头的商品

    Args:
        prefix: 商品编号前缀
        limit: 返回数量限制

    Returns:
        匹配的商品列表
    """
    return Product.query.filter(
        Product.product_code.like(f"{prefix}%")
    ).limit(limit).all()


def update_product(product_id: str, **kwargs) -> Optional[Product]:
    """
    更新商品信息

    Args:
        product_id: 商品ID
        **kwargs: 需要更新的字段，如description, price等

    Returns:
        更新后的商品对象，如果找不到则返回None
    """
    product = get_product_by_id(product_id)
    if not product:
        return None

    # 更新提供的字段
    for key, value in kwargs.items():
        if hasattr(product, key):
            setattr(product, key, value)

    try:
        db.session.commit()
        return product
    except Exception as e:
        db.session.rollback()
        print(f"更新商品失败: {e}")
        return None


def delete_product(product_id: str) -> bool:
    """
    删除商品

    Args:
        product_id: 商品ID

    Returns:
        是否删除成功
    """
    product = get_product_by_id(product_id)
    if not product:
        return False

    try:
        db.session.delete(product)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"删除商品失败: {e}")
        return False


def get_product_count() -> int:
    """
    获取商品总数

    Returns:
        商品数量
    """
    return Product.query.count()


def get_products_stats() -> Dict[str, Any]:
    """
    获取商品统计信息

    Returns:
        包含统计信息的字典
    """
    # 总数
    total_count = Product.query.count()

    # 价格统计
    price_stats = db.session.query(
        func.min(Product.price).label("min_price"),
        func.max(Product.price).label("max_price"),
        func.avg(Product.price).label("avg_price"),
    ).first()

    # 最近添加
    recent_added = db.session.query(
        func.max(Product.created_at).label("latest_added")
    ).first()

    return {
        "total_count": total_count,
        "min_price": float(price_stats.min_price) if price_stats.min_price else 0,
        "max_price": float(price_stats.max_price) if price_stats.max_price else 0,
        "avg_price": float(price_stats.avg_price) if price_stats.avg_price else 0,
        "latest_added": recent_added.latest_added if recent_added.latest_added else None
    }


def get_products_paginated(page: int = 1, per_page: int = 20,
                           sort_by: str = "created_at",
                           sort_order: str = "desc") -> Tuple[List[Product], int, int, int]:
    """
    获取分页的商品列表

    Args:
        page: 页码
        per_page: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向 ("asc" or "desc")

    Returns:
        (商品列表, 总数, 总页数, 当前页)
    """
    # 验证排序字段是否有效
    if not hasattr(Product, sort_by):
        sort_by = "created_at"

    # 构建排序条件
    if sort_order.lower() == "asc":
        order_clause = asc(getattr(Product, sort_by))
    else:
        order_clause = desc(getattr(Product, sort_by))

    # 查询总数
    total_count = Product.query.count()

    # 计算总页数
    total_pages = (total_count + per_page - 1) // per_page

    # 调整页码
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages

    # 获取当前页的数据
    products = Product.query.order_by(order_clause) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()

    return products, total_count, total_pages, page