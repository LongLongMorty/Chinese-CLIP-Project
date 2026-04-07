import os
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Tuple
from model_loader import CLIPModelLoader
from faiss_index import FAISSIndexManager
from cn_clip.clip.utils import tokenize

# 设置环境变量
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'


class ImageSearcher:
    def __init__(self, model_path, image_features_path, image_dir, pairs_file_path=None):
        # 初始化模型加载器
        self.model_loader = CLIPModelLoader(model_path)
        self.model = self.model_loader.model
        self.tokenizer = self.model_loader.tokenizer
        self.device = self.model_loader.device

        # 初始化FAISS索引管理器
        self.index_manager = FAISSIndexManager(image_features_path, image_dir)
        self.index_manager.load_or_create_index(
            r"E:\Graduation_project\clip-data\datasets\MUGE\faiss_index\image_index.index"
        )

        # 加载图片描述信息
        self.image_descriptions = {}
        if pairs_file_path:
            self.load_pairs_descriptions(pairs_file_path)

    def load_pairs_descriptions(self, pairs_file_path):
        try:
            with open(pairs_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        image_id = parts[0]
                        description = parts[1]
                        category_id = parts[2] if len(parts) > 2 else ""

                        self.image_descriptions[image_id] = {
                            "description": description,
                            "category_id": category_id
                        }
            print(f"成功加载 {len(self.image_descriptions)} 个图片描述信息")
        except Exception as e:
            print(f"加载图片描述信息失败: {str(e)}")

    def search(self, text, top_k=100):
        # 文本预处理（与训练时保持一致）
        text = text.lower().replace("“", '"').replace("”", '"')
        return self._cached_search(text, top_k)

    @lru_cache(maxsize=256)
    def _cached_search(self, text, top_k):
        """LRU 缓存：相同的 query 直接返回缓存结果"""
        with torch.no_grad():
            # 使用官方 tokenize：自动添加 [CLS]/[SEP]，补齐到 context_length=52
            token_ids = tokenize([text], context_length=52).to(self.device)

            text_features = self.model.encode_text(token_ids)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            text_features = text_features.cpu().numpy().astype('float32')

            distances, indices = self.index_manager.index.search(text_features, top_k)
            return indices[0].tolist(), distances[0].tolist()

    def search_by_image(self, image, top_k=100):
        with torch.no_grad():
            image = self.preprocess_image(image).unsqueeze(0).to(self.device)

            image_features = self.model.encode_image(image)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            image_features = image_features.cpu().numpy().astype('float32')
            distances, indices = self.index_manager.index.search(image_features, top_k)

            return indices[0], distances[0]

    def recommend_by_product_codes(self, product_codes, top_k=20, exclude_codes=None):
        """
        基于收藏商品列表进行内容推荐：
          1. 从 FAISS 索引还原每件收藏商品的特征向量
          2. 对所有向量取均值并归一化，得到"用户偏好向量"
          3. 使用 FAISS 搜索最相似的 top_k 个商品
          4. 过滤掉 exclude_codes 中的商品（通常是已收藏的商品）
        返回 (indices, distances) 与其他 search 方法保持一致。
        """
        if exclude_codes is None:
            exclude_codes = set(product_codes)
        else:
            exclude_codes = set(exclude_codes) | set(product_codes)

        # 还原特征向量
        feature_vecs = []
        for code in product_codes:
            vec = self.index_manager.get_feature_by_image_id(str(code))
            if vec is not None:
                feature_vecs.append(vec)

        if not feature_vecs:
            return [], []

        # 均值池化并归一化
        mean_vec = np.mean(np.stack(feature_vecs, axis=0), axis=0).astype('float32')
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
        mean_vec = mean_vec.reshape(1, -1)

        # 搜索更多候选，以便过滤后仍有足够结果
        search_k = min(top_k + len(exclude_codes) + 50, self.index_manager.index.ntotal)
        distances, indices_arr = self.index_manager.index.search(mean_vec, search_k)

        # 过滤已收藏商品
        result_indices, result_distances = [], []
        for idx, dist in zip(indices_arr[0].tolist(), distances[0].tolist()):
            if idx < 0 or idx >= len(self.index_manager.image_ids):
                continue
            code = self.index_manager.image_ids[idx]
            if code in exclude_codes:
                continue
            result_indices.append(idx)
            result_distances.append(dist)
            if len(result_indices) >= top_k:
                break

        return result_indices, result_distances

    # ── 多查询检索 + RRF 融合 ──────────────────────────────────────────────────

    def search_multi_query(
        self,
        queries: List[str],
        top_k: int = 100,
    ) -> List[Tuple[str, float]]:
        """
        对多个 query 分别检索，用 RRF（倒数排名融合）合并为一个排名列表。

        Args:
            queries:  查询词列表（第一个通常是原始词，后续是扩展词）。
            top_k:    每个 query 各检索 top_k 个候选。
        Returns:
            [(product_code, rrf_score), ...] 降序排列。
        """
        from query_expander import reciprocal_rank_fusion

        ranked_lists: List[List[Tuple[str, float]]] = []
        for q in queries:
            indices, distances = self.search(q, top_k)
            ranked: List[Tuple[str, float]] = []
            for idx, dist in zip(indices, distances):
                if idx < 0 or idx >= len(self.index_manager.image_ids):
                    continue
                code = self.index_manager.image_ids[idx]
                ranked.append((code, float(dist)))
            ranked_lists.append(ranked)

        return reciprocal_rank_fusion(ranked_lists)

    # ── 加权偏好向量推荐 ───────────────────────────────────────────────────────

    def recommend_by_weighted_codes(
        self,
        weighted_codes: Dict[str, float],
        top_k: int = 20,
        exclude_codes: set = None,
    ) -> Tuple[List[int], List[float]]:
        """
        基于加权商品列表进行内容推荐：
          1. 用每件商品的权重对其 FAISS 特征向量进行加权求和并归一化
          2. 使用 FAISS 搜索最相似的 top_k 个商品
          3. 过滤掉 exclude_codes 中的商品

        Args:
            weighted_codes: {product_code: weight}，权重越大影响越强。
            top_k:          返回结果数。
            exclude_codes:  需过滤的商品集合（通常是已收藏 + 已浏览）。
        Returns:
            (indices, distances) 与其他 search 方法格式一致。
        """
        if exclude_codes is None:
            exclude_codes = set(weighted_codes.keys())
        else:
            exclude_codes = set(exclude_codes) | set(weighted_codes.keys())

        weighted_sum: np.ndarray = None
        total_weight = 0.0

        for code, weight in weighted_codes.items():
            vec = self.index_manager.get_feature_by_image_id(str(code))
            if vec is not None:
                if weighted_sum is None:
                    weighted_sum = vec * weight
                else:
                    weighted_sum += vec * weight
                total_weight += weight

        if weighted_sum is None or total_weight == 0.0:
            return [], []

        # 归一化偏好向量
        mean_vec = (weighted_sum / total_weight).astype('float32')
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
        mean_vec = mean_vec.reshape(1, -1)

        search_k = min(top_k + len(exclude_codes) + 50, self.index_manager.index.ntotal)
        distances, indices_arr = self.index_manager.index.search(mean_vec, search_k)

        result_indices, result_distances = [], []
        for idx, dist in zip(indices_arr[0].tolist(), distances[0].tolist()):
            if idx < 0 or idx >= len(self.index_manager.image_ids):
                continue
            code = self.index_manager.image_ids[idx]
            if code in exclude_codes:
                continue
            result_indices.append(idx)
            result_distances.append(dist)
            if len(result_indices) >= top_k:
                break

        return result_indices, result_distances


        if image.mode != 'RGB':
            image = image.convert('RGB')

        image = image.resize((224, 224))
        image = torch.FloatTensor(np.array(image)).permute(2, 0, 1)
        image = image / 255.0

        mean = torch.tensor([0.48145466, 0.4578275, 0.40821073])
        std = torch.tensor([0.26862954, 0.26130258, 0.27577711])
        image = (image - mean[:, None, None]) / std[:, None, None]

        return image

    def get_search_results(self, indices, distances):
        """获取格式化的搜索结果，包括描述信息"""
        results = []
        for idx, dist in zip(indices, distances):
            image_id = self.index_manager.image_ids[idx]
            img_path = self.index_manager.get_image_path(image_id)
            similarity = float(dist)  # 转换为标准Python浮点数，便于JSON序列化

            # 获取图片描述信息
            description = "暂无描述"
            category_id = ""
            if str(image_id) in self.image_descriptions:
                description = self.image_descriptions[str(image_id)]["description"]
                category_id = self.image_descriptions[str(image_id)]["category_id"]

            result = {
                "image_id": str(image_id),
                "image_path": str(img_path),
                "similarity": similarity,
                "description": description,
                "category_id": category_id
            }
            results.append(result)

        return results

    def display_results(self, indices, distances):
        for idx, dist in zip(indices, distances):
            image_id = self.index_manager.image_ids[idx]
            img_path = self.index_manager.get_image_path(image_id)

            # 获取图片描述信息
            description = "暂无描述"
            if str(image_id) in self.image_descriptions:
                description = self.image_descriptions[str(image_id)]["description"]

            try:
                if img_path.exists():
                    img = Image.open(img_path)
                    img.show()
                    print(f"图片: {image_id}, 描述: {description}, 相似度: {dist:.4f}")
                else:
                    print(f"找不到图片: {img_path}")
            except Exception as e:
                print(f"无法显示图片 {image_id}: {str(e)}")


def main():
    # 配置路径
    model_path = r"E:/Graduation_project/clip-data/experiments/muge_finetune_vit-b-16_roberta-base_bs128_8gpu/checkpoints/epoch_latest.pt"
    image_features_path = r"E:/Graduation_project/clip-data/datasets/MUGE/json/train/train_imgs.img_feat.jsonl"
    image_dir = r"E:/Graduation_project/clip-data/datasets/MUGE/extracted/imgs"
    pairs_file_path = r"E:/Graduation_project/clip-data/datasets/MUGE/extracted/pairs"

    try:
        searcher = ImageSearcher(model_path, image_features_path, image_dir, pairs_file_path)

        while True:
            query = input("\n请输入搜索文本（输入 'q' 退出）: ")
            if query.lower() == 'q':
                break

            print("正在搜索...")
            indices, distances = searcher.search(query)
            searcher.display_results(indices, distances)

    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()