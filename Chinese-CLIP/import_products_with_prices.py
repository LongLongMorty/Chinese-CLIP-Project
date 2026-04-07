#!/usr/bin/env python3
"""
简化版商品数据导入脚本 - 直接定义所有必要的类和函数

使用方法:
python simple_import_products.py --file path/to/text_pairs.txt --img-dir path/to/images --db-uri mysql+pymysql://root:password@localhost/db_name
"""

import os
import sys
import time
import random
import argparse
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from tqdm import tqdm  # 用于显示进度条

# 获取项目根目录路径
root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(root_dir)  # 添加到Python路径

# 解析命令行参数
parser = argparse.ArgumentParser(description='导入商品数据到数据库并生成随机价格')
parser.add_argument('--file', '-f', required=True, help='text_pairs.txt文件路径')
parser.add_argument('--img-dir', '-i', required=True, help='图片目录路径')
parser.add_argument('--batch', '-b', type=int, default=500, help='批处理大小')
parser.add_argument('--db-uri', '-d', default='mysql+pymysql://root:root@localhost/image_search_db',
                    help='数据库URI')
parser.add_argument('--verify', '-v', action='store_true', help='验证图片文件是否存在')
args = parser.parse_args()

# 创建Flask应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = args.db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)


# 定义商品模型 - 这将创建与auth/product.py中相同结构的模型
class Product(db.Model):
    """商品数据模型"""
    __tablename__ = 'products'

    id = db.Column(db.String(64), primary_key=True)  # 商品ID，对应pairs文件第一列
    description = db.Column(db.String(255), nullable=True)  # 商品描述，对应pairs文件第二列
    product_code = db.Column(db.String(64), index=True)  # 商品编号，对应pairs文件第三列
    price = db.Column(db.Float, default=0.0)  # 商品价格，随机生成
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 创建数据库表
with app.app_context():
    db.create_all()
    print("数据库表已创建")


def add_product(product_id, description, product_code, price=None):
    """添加新商品"""
    # 检查商品是否已存在
    existing_product = Product.query.get(product_id)
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

    return new_product


def import_products_from_file(file_path, batch_size=500):
    """从文件导入商品数据"""
    total_imported = 0
    errors = 0

    # 计算文件总行数
    total_lines = sum(1 for _ in open(file_path, 'r', encoding='utf-8'))

    print(f"开始导入商品数据，文件: {file_path}，共 {total_lines} 条记录")
    print(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    start_time = time.time()

    with app.app_context():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                batch_count = 0

                # 使用tqdm显示进度条
                for line in tqdm(f, total=total_lines, desc="导入进度"):
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        product_id = parts[0]  # 商品ID
                        description = parts[1]  # 商品描述
                        product_code = parts[2]  # 商品编号

                        try:
                            # 生成随机价格 (1-10000)
                            price = random.uniform(1, 10000)
                            price = round(price, 2)  # 保留两位小数

                            # 添加商品到数据库
                            product = add_product(product_id, description, product_code, price)
                            if product:
                                total_imported += 1
                            else:
                                errors += 1

                            # 每批次提交一次，减少数据库负担
                            batch_count += 1
                            if batch_count >= batch_size:
                                db.session.commit()
                                batch_count = 0
                                print(f"\n已处理: {total_imported} 条记录")
                        except Exception as e:
                            errors += 1
                            print(f"\n导入商品ID={product_id}失败: {str(e)}")

                # 提交剩余的事务
                if batch_count > 0:
                    db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"导入商品数据失败: {str(e)}")
            import traceback
            traceback.print_exc()

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"\n商品数据导入完成:")
    print(f"- 成功导入: {total_imported} 条记录")
    print(f"- 失败记录: {errors} 条")
    print(f"- 耗时: {elapsed:.2f} 秒")

    return (total_imported, errors)


def verify_image_files(img_dir):
    """验证图片文件是否存在"""
    with app.app_context():
        # 获取所有商品
        products = Product.query.all()

        present = 0
        missing = 0

        print(f"开始验证图片文件...")
        for product in tqdm(products, desc="验证图片"):
            img_path = os.path.join(img_dir, f"{product.product_code}.jpg")

            if os.path.exists(img_path):
                present += 1
            else:
                missing += 1
                if missing <= 10:  # 只显示前10个缺失的图片，避免输出过多
                    print(f"商品编号 {product.product_code} 的图片不存在: {img_path}")
                elif missing == 11:
                    print("... 更多缺失图片省略显示 ...")

        print(f"\n图片验证完成:")
        print(f"- 存在图片: {present} 个")
        print(f"- 缺失图片: {missing} 个")

        return (present, missing)


# 执行导入
if __name__ == "__main__":
    try:
        print(f"开始导入商品数据，将为每个商品生成1-10000元的随机价格...")
        imported, errors = import_products_from_file(args.file, args.batch)

        # 验证图片文件
        if args.verify:
            print("\n开始验证图片文件...")
            present, missing = verify_image_files(args.img_dir)

            if missing > 0:
                print(f"警告: 有 {missing} 个商品缺少对应的图片文件")

        print("\n导入和验证过程已完成")

    except Exception as e:
        print(f"程序执行过程中发生错误: {str(e)}")
        import traceback

        traceback.print_exc()