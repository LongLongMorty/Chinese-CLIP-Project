import os
import sys
import time
import random
from tqdm import tqdm  # 用于显示进度条

# 获取项目根目录路径并添加到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)  # 上一级目录(项目根目录)
sys.path.append(root_dir)  # 添加到Python路径

# 导入需要的模块
from models import db
from product import Product, add_product


class ProductImporter:
    """商品数据导入工具"""

    def __init__(self, app=None):
        """
        初始化商品导入器

        Args:
            app: Flask应用实例，用于创建数据库上下文
        """
        self.app = app
        self.total_imported = 0
        self.errors = 0

    def import_from_pairs_file(self, file_path, batch_size=500):
        """
        从pairs文件导入商品数据

        Args:
            file_path: pairs文件路径
            batch_size: 批处理大小，每处理多少条记录提交一次事务

        Returns:
            tuple: (导入成功的记录数, 错误记录数)
        """
        self.total_imported = 0
        self.errors = 0

        # 首先计算文件总行数，用于进度显示
        total_lines = sum(1 for _ in open(file_path, 'r', encoding='utf-8'))

        print(f"开始导入商品数据，文件: {file_path}，共 {total_lines} 条记录")

        # 使用Flask应用上下文
        app_context = self.app.app_context() if self.app else None
        if app_context:
            app_context.push()

        start_time = time.time()
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
                                self.total_imported += 1
                            else:
                                self.errors += 1

                            # 每批次提交一次，减少数据库负担
                            batch_count += 1
                            if batch_count >= batch_size:
                                db.session.commit()
                                batch_count = 0
                        except Exception as e:
                            self.errors += 1
                            print(f"\n导入商品ID={product_id}失败: {str(e)}")

                # 提交剩余的事务
                if batch_count > 0:
                    db.session.commit()

        except Exception as e:
            if batch_count > 0:
                db.session.rollback()
            print(f"导入商品数据失败: {str(e)}")
        finally:
            if app_context:
                app_context.pop()

        end_time = time.time()
        elapsed = end_time - start_time

        print(f"\n商品数据导入完成:")
        print(f"- 成功导入: {self.total_imported} 条记录")
        print(f"- 失败记录: {self.errors} 条")
        print(f"- 耗时: {elapsed:.2f} 秒")

        return (self.total_imported, self.errors)

    def verify_image_files(self, img_dir):
        """
        验证图片文件是否存在

        Args:
            img_dir: 图片目录路径

        Returns:
            tuple: (图片存在数量, 图片缺失数量)
        """
        if not self.app:
            print("无法验证图片文件: 未提供Flask应用实例")
            return (0, 0)

        with self.app.app_context():
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
                    print(f"商品编号 {product.product_code} 的图片不存在: {img_path}")

            print(f"\n图片验证完成:")
            print(f"- 存在图片: {present} 个")
            print(f"- 缺失图片: {missing} 个")

            return (present, missing)