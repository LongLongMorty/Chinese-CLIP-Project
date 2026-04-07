import torch
import json
import numpy as np
from tqdm import tqdm
from clip.model import CLIP, convert_weights
import os
from transformers import BertTokenizer


class TextImageSearcher:
    def __init__(self, model_path, image_features_path):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # 初始化分词器
        self.tokenizer = BertTokenizer.from_pretrained("hfl/chinese-roberta-wwm-ext")
        # 加载模型配置文件
        vision_model_config_file = "E:\\Graduation_project\\Chinese-CLIP\\cn_clip\\clip\\model_configs\\ViT-B-16.json"
        text_model_config_file = "E:\\Graduation_project\\Chinese-CLIP\\cn_clip\\clip\\model_configs\\RoBERTa-wwm-ext-base-chinese.json"

        # 加载并处理模型配置
        with open(vision_model_config_file, 'r') as fv, open(text_model_config_file, 'r') as ft:
            model_info = json.load(fv)
            if isinstance(model_info['vision_layers'], str):
                model_info['vision_layers'] = eval(model_info['vision_layers'])

            text_config = json.load(ft)

            # 只保留CLIP类需要的参数
            clip_params = {
                'embed_dim': model_info['embed_dim'],
                'image_resolution': model_info['image_resolution'],
                'vision_layers': model_info['vision_layers'],
                'vision_width': model_info['vision_width'],
                'vision_patch_size': model_info['vision_patch_size'],
                'context_length': text_config.get('context_length', 52),
                'vocab_size': text_config.get('vocab_size', 30522),
                'transformer_width': text_config.get('transformer_width', 768),
                'transformer_heads': text_config.get('transformer_heads', 12),
                'transformer_layers': text_config.get('transformer_layers', 12),
                'context_length': 197
            }

        # 使用过滤后的参数初始化模型
        self.model = CLIP(**clip_params)
        convert_weights(self.model)
        self.model.cuda()

        # 修改加载模型权重的部分
        checkpoint = torch.load(model_path, map_location=self.device)
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            # 创建新的状态字典
            new_state_dict = {}

            # 处理状态字典的键名
            for k, v in state_dict.items():
                # 移除模块前缀
                if k.startswith('module.'):
                    k = k[len('module.'):]
                # 移除不需要的键
                if "bert.pooler" in k:
                    continue
                # 处理视觉编码器的键名
                if k.startswith('visual.'):
                    k = k[len('visual.'):]
                # 处理文本编码器的键名
                if k.startswith('text.'):
                    continue  # 暂时跳过文本编码器的权重

                new_state_dict[k] = v

            # 尝试加载处理后的状态字典
            try:
                self.model.load_state_dict(new_state_dict, strict=False)
                print("模型权重加载成功（部分权重可能未加载）")
            except Exception as e:
                print(f"加载模型权重时出现警告（这可能是正常的）：{str(e)}")

        self.model.eval()

        # 加载图像特征
        self.image_features = {}
        self.load_image_features(image_features_path)

    """文本分词处理"""
    def tokenize(self, text):

            tokens = self.tokenizer(
                text,
                padding='max_length',
                truncation=True,
                max_length=197,
                return_tensors="pt"
            )
            return tokens.input_ids

    def load_image_features(self, feature_path):
        """加载预先提取的图像特征"""
        print("正在加载图像特征...")
        with open(feature_path, 'r') as f:
            for line in tqdm(f):
                item = json.loads(line.strip())
                self.image_features[item['image_id']] = np.array(item['feature'])

    def search(self, text, top_k=5):
        """搜索最相似的图片"""
        with torch.no_grad():
            # 使用新的分词方法
            text_tokens = self.tokenize([text]).to(self.device)
            text_features = self.model(None, text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            text_features = text_features.cpu().numpy()

        similarities = {}
        for image_id, image_feature in self.image_features.items():
            similarity = np.dot(text_features, image_feature)
            similarities[image_id] = float(similarity)

        return sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]


def main():
    model_path = r"E:\Graduation_project\clip-data\experiments\muge_finetune_vit-b-16_roberta-base_bs128_8gpu\checkpoints\epoch_latest.pt"
    image_features_path = r"E:\Graduation_project\clip-data\datasets\MUGE\json\train\train_imgs.img_feat.jsonl"

    searcher = TextImageSearcher(model_path, image_features_path)

    while True:
        query = input("\n请输入搜索文本（输入 'q' 退出）: ")
        if query.lower() == 'q':
            break

        results = searcher.search(query)

        print("\n搜索结果：")
        for image_id, similarity in results:
            print(f"图片: {image_id}, 相似度: {similarity:.4f}")


if __name__ == "__main__":
    main()