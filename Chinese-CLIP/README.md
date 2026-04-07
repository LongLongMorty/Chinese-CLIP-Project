# Chinese-CLIP 商品图文检索系统

基于 [Chinese-CLIP](https://github.com/OFA-Sys/Chinese-CLIP) 的中文电商商品图文跨模态检索系统，支持以文搜图、以图搜图，并集成用户行为追踪与个性化推荐。

---

## 目录

- [项目简介](#项目简介)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [API 接口文档](#api-接口文档)
- [数据库模型](#数据库模型)
- [配置说明](#配置说明)

---

## 项目简介

本项目为毕业设计项目，基于阿里达摩院开源的 **Chinese-CLIP**（中文 CLIP）模型，在 MUGE 电商数据集上进行微调，实现面向中文商品的图文跨模态检索。

用户可通过输入中文关键词或上传商品图片，在海量商品库中快速找到相似商品，并支持收藏、浏览历史及基于用户行为的个性化推荐。

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Vue Router |
| 后端 | Python 3 + Flask + Flask-Login + Flask-SQLAlchemy |
| 数据库 | MySQL |
| 向量检索 | FAISS（FlatIP 内积索引） |
| 模型 | Chinese-CLIP ViT-B/16 + RoBERTa-base（MUGE 微调） |
| 包管理 | Anaconda (PyTorch 环境) + npm |

---

## 系统架构

```
用户（浏览器）
    │
    ▼
Vue 3 前端（:5173）
    │  HTTP / REST API
    ▼
Flask 后端（:5000）
    ├── Chinese-CLIP 模型（文本/图片特征提取）
    ├── FAISS 向量索引（FlatIP ANN 检索）
    ├── 查询扩展模块（同义词词典 + RRF 融合）
    └── MySQL 数据库（用户、商品、行为记录）
```

---

## 功能特性

### 核心检索
- **文本搜索**：输入中文关键词（如"红色连衣裙"），CLIP 文本编码器提取特征，通过 FAISS 余弦检索最相似商品图片
- **图片搜索**：上传商品图片，CLIP 图像编码器提取特征，在商品库中检索视觉相似商品
- **查询扩展**：内置电商场景同义词词典，自动扩展查询词（如"运动鞋" → 跑步鞋、球鞋、训练鞋），多查询结果通过 **RRF（Reciprocal Rank Fusion）** 融合排名，提升召回率

### 用户系统
- 用户注册 / 登录 / 退出（密码 bcrypt 加密）
- 基于 Flask-Login 的 Session 认证
- 支持用户名或邮箱登录

### 行为追踪与推荐
- 记录搜索历史、浏览历史、点击历史
- 基于用户行为权重生成个性化商品推荐
- 收藏夹管理（添加 / 删除 / 查询）

### 性能优化
- CLIP 搜索结果 **LRU 缓存**（相同查询直接命中缓存）
- FAISS FlatIP 索引预加载，首次构建后持久化
- 搜索服务在**后台线程**异步初始化，不阻塞 Flask 启动

---

## 模型评测

主要计算检索任务的 Recall@1/5/10，同时给出 mean recall（Recall@1/5/10的平均数）。
在 MUGE valid 验证集上的表现为：

```json
{"success": true, "score": 76.09158679446219, "scoreJson": {"score": 76.09158679446219, "mean_recall": 76.09158679446219, "r1": 57.40814696485623, "r5": 82.06869009584665, "r10": 88.7979233226837}}
```

**评估结论**：
- **mean_recall** 达到了 **76.09%**
- **$r_{5}$** 相较于 **$r_{1}$** 提升较大，达到了 **82.07%**
- **$r_{10}$** 与 **$r_{5}$** 差不多，达到了 **88.80%**

综合考虑，可以在系统搜索时一次展示 **top-5** 的图片即可达到较好的检索覆盖率。

---

## 项目结构

```
Chinese-CLIP/
├── app.py                      # Flask 主应用 & 所有 API 路由
├── image_searcher.py           # 图文检索核心逻辑（CLIP + FAISS）
├── model_loader.py             # CLIP 模型加载器
├── faiss_index.py              # FAISS 索引管理（构建/加载/检索）
├── query_expander.py           # 查询扩展模块（同义词词典 + RRF）
├── dataset_transform.py        # 数据集预处理工具
├── import_products_with_prices.py  # 商品数据导入脚本
├── charts.py                   # 图表/统计工具
├── requirements.txt            # Python 依赖
├── start.ps1                   # 一键启动脚本（Windows PowerShell）
│
├── auth/                       # 用户认证模块
│   ├── models.py               # 数据库模型（User / Product / Favorite 等）
│   ├── routes.py               # 认证路由（/auth/login、/auth/register、/auth/logout）
│   ├── utils.py                # 工具函数
│   ├── product.py              # 商品相关辅助
│   └── product_importer.py     # 商品批量导入
│
├── cn_clip/                    # Chinese-CLIP 模型库
│   ├── clip/                   # CLIP 模型定义（ViT + BERT）
│   ├── eval/                   # 评测脚本（零样本 / KNN / FAISS）
│   ├── training/               # 微调训练脚本
│   └── preprocess/             # 数据预处理
│
├── frontend/image-search/      # Vue 3 前端
│   ├── src/                    # 源码目录
│   ├── package.json
│   └── vite.config.js
│
└── run_scripts/                # 模型微调运行脚本（Shell）
```

---

## 环境要求

- Windows 10/11（`start.ps1` 依赖 PowerShell；Linux/macOS 可手动启动）
- [Anaconda](https://www.anaconda.com/) 并创建名为 `PyTorch` 的 conda 虚拟环境
- Python >= 3.8
- CUDA >= 11.1（GPU 推理，建议；CPU 模式也可运行但较慢）
- Node.js >= 18
- MySQL >= 8.0

### Python 依赖安装

```bash
conda activate PyTorch
pip install -r requirements.txt
# 根据 CUDA 版本安装对应的 PyTorch，例如：
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 前端依赖安装

```bash
cd frontend/image-search
npm install
```

---

## 快速开始

### 1. 准备数据与模型权重

将以下文件放置到对应目录（与 `app.py` 中路径配置一致）：

| 文件 | 路径 |
|------|------|
| 微调模型权重 | `clip-data/pretrained_weights/chinese-clip-vit-base-patch16/clip_cn_vit-b-16.pt` |
| 图片特征文件 | `clip-data/datasets/MUGE/json/train/train_imgs.img_feat.jsonl` |
| 商品图片目录 | `clip-data/datasets/MUGE/extracted/imgs/` |
| FAISS 索引（可选，首次自动构建） | `clip-data/datasets/MUGE/faiss_index/image_index.index` |

### 2. 初始化数据库

```bash
# 在 MySQL 中创建数据库
mysql -u root -p -e "CREATE DATABASE image_search_db DEFAULT CHARSET=utf8mb4;"

# 执行数据迁移（Flask-SQLAlchemy 自动建表）
conda activate PyTorch
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 导入商品数据（可选）
python import_products_with_prices.py
```

### 3. 一键启动（Windows）

```powershell
# 在项目根目录执行
.\start.ps1
```

脚本将自动打开两个 PowerShell 窗口分别运行后端和前端：

- 后端：http://localhost:5000  
- 前端：http://localhost:5173

### 4. 手动启动

```bash
# 后端
conda activate PyTorch
set KMP_DUPLICATE_LIB_OK=TRUE
python app.py

# 前端（另开终端）
cd frontend/image-search
npm run dev
```

---

## API 接口文档

### 检索

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/search` | 文本搜索商品图片 |
| `POST` | `/api/image-search` | 图片搜索商品图片 |
| `GET` | `/api/images/<product_code>` | 获取商品图片文件 |

**文本搜索请求示例：**
```json
POST /api/search
{
  "query": "红色运动鞋",
  "top_k": 20
}
```

**响应示例：**
```json
{
  "status": "success",
  "results": [
    {
      "product_code": "123456",
      "image_url": "/api/images/123456",
      "similarity": 0.87,
      "description": "红色跑步鞋",
      "price": 299.0
    }
  ],
  "result_count": 20,
  "expanded_queries": ["红色运动鞋", "红色跑步鞋", "红色球鞋"]
}
```

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/auth/login` | 用户登录 |
| `POST` | `/auth/register` | 用户注册 |
| `POST` | `/auth/logout` | 退出登录 |
| `GET` | `/api/auth/check` | 检查登录状态 |

### 收藏

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/favorites/add` | 添加收藏 |
| `POST` | `/api/favorites/remove` | 取消收藏 |
| `GET` | `/api/favorites` | 获取收藏列表 |
| `POST` | `/api/favorites/check` | 检查是否已收藏 |

### 行为记录与推荐

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/behavior/browse` | 记录浏览行为 |
| `POST` | `/api/behavior/click` | 记录点击行为 |
| `GET` | `/api/behavior/search-history` | 获取搜索历史 |
| `GET` | `/api/behavior/browse-history` | 获取浏览历史 |
| `GET` | `/api/recommend` | 获取个性化推荐 |

### 商品

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/products/<product_id>` | 按 ID 查询商品 |
| `GET` | `/api/products/code/<product_code>` | 按编码查询商品 |
| `GET` | `/health` | 服务健康检查 |

---

## 数据库模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `User` | `users` | 用户账号信息 |
| `Product` | `products` | 商品信息（ID、描述、编码、价格） |
| `Favorite` | `favorites` | 用户收藏记录 |
| `SearchHistory` | `search_history` | 搜索历史（含扩展词） |
| `BrowseHistory` | `browse_history` | 商品浏览历史 |
| `ClickHistory` | `click_history` | 商品点击历史 |

---

## 配置说明

主要配置项位于 [app.py](app.py) 文件顶部：

```python
# 数据库连接（修改为你的 MySQL 信息）
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/image_search_db'

# 模型与数据路径（修改为你的本地路径）
BASE_DIR = r"E:\Graduation_project"
MODEL_PATH = ...          # CLIP 模型权重路径
IMAGE_FEATURES_PATH = ... # 图片特征文件路径
IMAGE_DIR = ...           # 商品图片目录

# 密钥（生产环境请替换）
app.secret_key = os.getenv('SECRET_KEY', '114514')
```

一键启动脚本 [start.ps1](start.ps1) 中需修改 conda 环境的 Python 路径：

```powershell
$PYTHON = "D:\Anaconda3\envs\PyTorch\python.exe"  # 修改为你的 Python 路径
```
