import torch
import json
from pathlib import Path
from cn_clip.clip.model import convert_weights, CLIP
from cn_clip.clip.bert_tokenizer import FullTokenizer


class CLIPModelLoader:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = model_path
        self.tokenizer = FullTokenizer()
        self.model = self._init_model()

    def _init_model(self):
        vision_model_config_file = Path("E:/Graduation_project/Chinese-CLIP/cn_clip/clip/model_configs/ViT-B-16.json")
        text_model_config_file = Path(
            "E:/Graduation_project/Chinese-CLIP/cn_clip/clip/model_configs/RoBERTa-wwm-ext-base-chinese.json")

        print("正在加载模型配置...")
        with open(vision_model_config_file, 'r') as fv, open(text_model_config_file, 'r') as ft:
            vision_config = json.load(fv)
            text_config = json.load(ft)

        model_info = {
            'embed_dim': vision_config['embed_dim'],
            'image_resolution': vision_config['image_resolution'],
            'vision_layers': eval(vision_config['vision_layers']) if isinstance(vision_config['vision_layers'],
                                                                                str) else vision_config[
                'vision_layers'],
            'vision_width': vision_config['vision_width'],
            'vision_patch_size': vision_config['vision_patch_size'],
            'vocab_size': text_config.get('vocab_size', 30522),
            'text_attention_probs_dropout_prob': 0.1,
            'text_hidden_act': 'gelu',
            'text_hidden_dropout_prob': 0.1,
            'text_hidden_size': text_config.get('hidden_size', 768),
            'text_initializer_range': 0.02,
            'text_intermediate_size': 3072,
            'text_max_position_embeddings': 512,
            'text_num_attention_heads': text_config.get('num_attention_heads', 12),
            'text_num_hidden_layers': text_config.get('num_hidden_layers', 12),
            'text_type_vocab_size': 2
        }

        print("正在初始化模型...")
        model = CLIP(**model_info)
        convert_weights(model)
        model.cuda()

        print("加载权重文件...")
        checkpoint = torch.load(self.model_path, map_location=self.device)

        # 化训权重格式：{'state_dict': {...}}
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            if next(iter(state_dict.items()))[0].startswith('module'):
                state_dict = {k[len('module.'):]: v for k, v in state_dict.items() if "bert.pooler" not in k}
            model.load_state_dict(state_dict)
            print("已加载化训权重")
        # 预训练权重格式：纯 state_dict
        elif isinstance(checkpoint, dict):
            # 过滤掉 bert.pooler 相关參数（如果有）
            filtered = {k: v for k, v in checkpoint.items() if "bert.pooler" not in k}
            model.load_state_dict(filtered, strict=False)
            print("已加载预训练权重")
        else:
            raise ValueError(f"未识别的权重文件格式: {type(checkpoint)}")

        model.eval()
        return model