#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文意图识别预测 - Windows 版本

使用方法：
    python predict_windows.py
"""

import json
import os

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# ==================== 配置区域 ====================
# 模型路径
MODEL_PATH = r"C:\Users\ASUS\Desktop\Rie-Kugimiya\intent_model"

# ==================== 配置区域结束 ====================


class IntentPredictor:
    """意图预测器"""
    
    def __init__(self, model_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}\n请先运行 train_windows.py 训练模型")
        
        print(f"加载模型: {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()
        
        # 加载意图映射
        mapping_path = os.path.join(model_path, "intent_mapping.json")
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            self.id2intent = {int(k): v for k, v in mapping["id2intent"].items()}
            self.intent2id = mapping["intent2id"]
        
        print(f"✅ 模型加载完成！支持 {len(self.id2intent)} 种意图\n")
    
    def predict(self, text, top_k=3):
        """
        预测文本意图
        
        Args:
            text: 输入文本
            top_k: 返回前 k 个预测结果
        
        Returns:
            预测结果列表
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            
            # Top-k
            topk_probs, topk_ids = torch.topk(probs[0], k=min(top_k, len(probs[0])))
        
        results = []
        for i in range(len(topk_ids)):
            results.append({
                "intent": self.id2intent[topk_ids[i].item()],
                "confidence": float(topk_probs[i].item())
            })
        
        return results
    
    def predict_batch(self, texts, top_k=1):
        """批量预测"""
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
        
        results = []
        for i in range(len(texts)):
            topk_probs, topk_ids = torch.topk(probs[i], k=min(top_k, len(probs[i])))
            
            predictions = []
            for j in range(len(topk_ids)):
                predictions.append({
                    "intent": self.id2intent[topk_ids[j].item()],
                    "confidence": float(topk_probs[j].item())
                })
            
            results.append({
                "text": texts[i],
                "predictions": predictions
            })
        
        return results


def main():
    print("=" * 60)
    print("中文意图识别预测")
    print("=" * 60)
    print()
    
    # 检查模型是否存在
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 错误: 模型文件不存在")
        print(f"   路径: {MODEL_PATH}")
        print(f"\n请先运行 train_windows.py 训练模型")
        return
    
    # 加载预测器
    try:
        predictor = IntentPredictor(MODEL_PATH)
    except Exception as e:
        print(f"❌ 加载模型失败: {e}")
        return
    
    # 示例测试
    print("=" * 60)
    print("示例测试")
    print("=" * 60)
    
    test_texts = [
        "你好",
        "谢谢你",
        "不需要",
        "我考虑一下",
        "什么意思？",
    ]
    
    for text in test_texts:
        results = predictor.predict(text, top_k=3)
        print(f"\n文本: {text}")
        print(f"意图: {results[0]['intent']} (置信度: {results[0]['confidence']:.2%})")
        if len(results) > 1:
            print(f"其他可能:")
            for i, result in enumerate(results[1:], 2):
                print(f"  {i}. {result['intent']} (置信度: {result['confidence']:.2%})")
    
    # 交互式预测
    print(f"\n{'='*60}")
    print("交互式预测")
    print("=" * 60)
    print("输入文本进行意图识别（输入 'quit' 退出）\n")
    
    while True:
        try:
            text = input("请输入文本: ").strip()
            
            if text.lower() in ['quit', 'exit', 'q', '退出']:
                print("\n再见！")
                break
            
            if not text:
                continue
            
            results = predictor.predict(text, top_k=3)
            
            print(f"\n预测结果:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['intent']} (置信度: {result['confidence']:.2%})")
            print()
            
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}\n")


if __name__ == "__main__":
    main()
