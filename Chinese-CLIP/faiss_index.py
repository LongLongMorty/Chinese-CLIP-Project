import json
import numpy as np
import faiss
from pathlib import Path

# 限制 FAISS OpenMP 线程数为 1，避免与 PyTorch 线程池冲突导致 C 级崩溃
faiss.omp_set_num_threads(1)


class FAISSIndexManager:
    def __init__(self, image_features_path, image_dir):
        self.image_features_path = image_features_path
        self.image_dir = image_dir
        self.image_id_to_path = {}
        self.image_ids = []
        self.index = None

    def load_or_create_index(self, index_path):
        """
        加载策略（按优先级）：
          1. 直接加载已有的 FlatIP 索引（.index 文件）——最快最稳定
          2. 若不存在，从 jsonl 特征文件从头构建 FlatIP 索引并保存

        放弃 HNSW 在线转换：HNSW 构建需要 reconstruct_n 一次性载入
        全部向量（~265 MB）再建图，极易因内存峰值引发 C 级崩溃。
        若未来需要 HNSW，请用独立脚本离线构建。
        """
        index_path = Path(index_path)

        # ---- 1. 加载已有 FlatIP 索引 ----
        if index_path.exists():
            try:
                print(f"加载 FlatIP 索引: {index_path}")
                self.index = faiss.read_index(str(index_path))
                self._load_image_ids_from_features()
                print(f"FlatIP 索引加载成功，{self.index.ntotal} 条特征，"
                      f"image_ids: {len(self.image_ids)}")
                return
            except Exception as e:
                print(f"FlatIP 索引加载失败: {e}，将从头构建...")
                self.image_ids = []
                self.image_id_to_path = {}

        # ---- 2. 从 jsonl 特征文件从头构建 FlatIP 索引 ----
        print("未找到索引文件，从特征文件构建 FlatIP 索引...")
        self.index = self._create_flat_index(index_path)

    def _load_image_ids_from_features(self):
        """从 jsonl 特征文件中按顺序加载 image_ids，确保与 FAISS 向量顺序一致"""
        print("从特征文件加载 image_ids 顺序...")
        image_dir = Path(self.image_dir)
        with open(self.image_features_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line.strip())
                image_id = str(item["image_id"])
                self.image_ids.append(image_id)
                self.image_id_to_path[image_id] = str(image_dir / f"{image_id}.jpg")
        print(f"加载完成，共 {len(self.image_ids)} 个 image_id")

    def _create_flat_index(self, index_path):
        """从 jsonl 特征文件从头构建 FlatIP 索引，分批写入避免内存峰值"""
        batch_size = 10000
        dimension = None
        index = None
        batch_features = []
        total_added = 0

        print("读取特征文件，构建 FlatIP 索引（分批写入）...")
        with open(self.image_features_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line.strip())
                image_id = str(item["image_id"])
                feature = item["feature"]

                if dimension is None:
                    dimension = len(feature)
                    index = faiss.IndexFlatIP(dimension)
                    print(f"向量维度: {dimension}，开始构建 FlatIP 索引...")

                self.image_ids.append(image_id)
                self.image_id_to_path[image_id] = str(Path(self.image_dir) / f"{image_id}.jpg")
                batch_features.append(feature)

                if len(batch_features) >= batch_size:
                    index.add(np.array(batch_features, dtype='float32'))
                    total_added += len(batch_features)
                    print(f"  已添加 {total_added} 条向量...")
                    batch_features = []

        if batch_features:
            index.add(np.array(batch_features, dtype='float32'))
            total_added += len(batch_features)

        print(f"FlatIP 索引构建完成，共 {total_added} 条向量，保存到 {index_path}...")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(index_path))
        print(f"索引已保存")
        return index

    def get_image_path(self, image_id):
        path = self.image_id_to_path.get(str(image_id))
        if not path:
            path = str(Path(self.image_dir) / f"{image_id}.jpg")
        return Path(path)

    def get_feature_by_image_id(self, image_id):
        """根据 image_id 从 FAISS 索引中还原对应的特征向量，找不到时返回 None"""
        try:
            image_id = str(image_id)
            if image_id not in self.image_id_to_path:
                return None
            idx = self.image_ids.index(image_id)
            vec = np.zeros((1, self.index.d), dtype='float32')
            self.index.reconstruct(idx, vec[0])
            return vec[0]
        except Exception:
            return None