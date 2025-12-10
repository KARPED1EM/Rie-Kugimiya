# -*- coding: utf-8 -*-
"""
中文意图识别模型训练

直接运行即可：python train_intent.py
"""

import json
import os
from collections import Counter
from pathlib import Path

import torch
import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
from sklearn.metrics import accuracy_score, f1_score, classification_report
import numpy as np


# 自动检测项目路径
SCRIPT_DIR = Path(__file__).parent.absolute()
if SCRIPT_DIR.name == "scripts":
    PROJECT_ROOT = SCRIPT_DIR.parent
else:
    PROJECT_ROOT = SCRIPT_DIR

# 数据集路径
DATA_PATH = (
    PROJECT_ROOT / "few_shot_intent_sft" / "data" / "telemarketing_intent_cn.jsonl"
)

# 模型保存路径
OUTPUT_DIR = PROJECT_ROOT / "intent_model"

# 训练参数
MAX_INTENTS = 50
MIN_SAMPLES = 10
BATCH_SIZE = 16
EPOCHS = 3


def load_data(file_path, max_intents, min_samples):
    """加载数据"""
    print(f"加载数据: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"数据集不存在: {file_path}")

    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                data.append(
                    {
                        "text": item["text"],
                        "label": item["label"],
                        "split": item.get("split", "train"),
                    }
                )

    df = pd.DataFrame(data)
    print(f"原始数据: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    # 过滤
    intent_counts = Counter(df["label"])
    valid_intents = [
        intent for intent, count in intent_counts.items() if count >= min_samples
    ]
    df = df[df["label"].isin(valid_intents)]

    top_intents = [intent for intent, _ in intent_counts.most_common(max_intents)]
    df = df[df["label"].isin(top_intents)]

    print(f"过滤后: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    # 标签映射
    unique_intents = sorted(df["label"].unique())
    intent2id = {intent: i for i, intent in enumerate(unique_intents)}
    id2intent = {i: intent for intent, i in intent2id.items()}

    df["label_id"] = df["label"].map(intent2id)

    # 划分数据集
    train_df = df[df["split"] == "train"]
    test_df = df[df["split"] == "test"]

    if len(test_df) == 0:
        from sklearn.model_selection import train_test_split

        train_df, test_df = train_test_split(
            df, test_size=0.2, random_state=42, stratify=df["label_id"]
        )

    train_dataset = Dataset.from_pandas(
        train_df[["text", "label_id"]].rename(columns={"label_id": "label"})
    )
    test_dataset = Dataset.from_pandas(
        test_df[["text", "label_id"]].rename(columns={"label_id": "label"})
    )

    dataset = DatasetDict({"train": train_dataset, "test": test_dataset})

    print(f"训练集: {len(train_dataset)} 样本")
    print(f"测试集: {len(test_dataset)} 样本")

    return dataset, intent2id, id2intent


def compute_metrics(eval_pred):
    """评估指标"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=-1)

    accuracy = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average="weighted")

    return {"accuracy": accuracy, "f1": f1}


def main():
    print("=" * 60)
    print("中文意图识别模型训练")
    print("=" * 60)
    print(f"\n项目路径: {PROJECT_ROOT}")
    print(f"数据集: {DATA_PATH}")
    print(f"模型保存: {OUTPUT_DIR}\n")

    # 检查数据集
    if not DATA_PATH.exists():
        print(f"❌ 错误: 数据集不存在")
        print(f"路径: {DATA_PATH}\n")

        # 列出可用数据集
        data_dir = PROJECT_ROOT / "few_shot_intent_sft" / "data"
        if data_dir.exists():
            print("可用的数据集:")
            for f in sorted(data_dir.glob("*.jsonl"))[:10]:
                print(f"  - {f.name}")
        return

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 加载数据
    print("=" * 60)
    print("步骤 1/4: 加载数据")
    print("=" * 60)
    dataset, intent2id, id2intent = load_data(DATA_PATH, MAX_INTENTS, MIN_SAMPLES)
    num_labels = len(intent2id)

    print(f"\n意图列表 (共 {num_labels} 个):")
    for i, intent in enumerate(sorted(intent2id.keys())[:10]):
        print(f"  {i+1}. {intent}")
    if num_labels > 10:
        print(f"  ... 还有 {num_labels - 10} 个")

    # 加载模型
    print(f"\n{'='*60}")
    print("步骤 2/4: 加载模型")
    print("=" * 60)
    print("模型: hfl/chinese-bert-wwm-ext")
    print("首次运行需要下载模型，请稍候...\n")

    tokenizer = AutoTokenizer.from_pretrained("hfl/chinese-bert-wwm-ext")
    model = AutoModelForSequenceClassification.from_pretrained(
        "hfl/chinese-bert-wwm-ext", num_labels=num_labels
    )

    model.config.id2label = id2intent
    model.config.label2id = intent2id

    print("✅ 模型加载完成")

    # 数据预处理
    print(f"\n{'='*60}")
    print("步骤 3/4: 数据预处理")
    print("=" * 60)

    def tokenize(examples):
        return tokenizer(
            examples["text"], truncation=True, padding="max_length", max_length=128
        )

    tokenized_dataset = dataset.map(tokenize, batched=True)
    print("✅ 数据预处理完成")

    # 训练
    print(f"\n{'='*60}")
    print("步骤 4/4: 开始训练")
    print("=" * 60)
    print(f"批次大小: {BATCH_SIZE}")
    print(f"训练轮数: {EPOCHS}")
    print(f"预估时间: 4-6 小时\n")

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        num_train_epochs=EPOCHS,
        weight_decay=0.01,
        logging_steps=100,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        fp16=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"],
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # 评估
    print(f"\n{'='*60}")
    print("评估模型")
    print("=" * 60)
    results = trainer.evaluate()
    print(f"准确率: {results['eval_accuracy']:.4f}")
    print(f"F1 Score: {results['eval_f1']:.4f}")

    # 保存
    print(f"\n{'='*60}")
    print("保存模型")
    print("=" * 60)
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    mapping_path = OUTPUT_DIR / "intent_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(
            {"intent2id": intent2id, "id2intent": id2intent},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✅ 模型已保存到: {OUTPUT_DIR}")

    # 分类报告
    predictions = trainer.predict(tokenized_dataset["test"])
    pred_labels = np.argmax(predictions.predictions, axis=-1)
    true_labels = predictions.label_ids

    print(f"\n{'='*60}")
    print("分类报告")
    print("=" * 60)
    print(
        classification_report(
            true_labels,
            pred_labels,
            target_names=list(intent2id.keys()),
            zero_division=0,
        )
    )

    print(f"\n{'='*60}")
    print("✅ 训练完成！")
    print("=" * 60)
    print(f"模型位置: {OUTPUT_DIR}")
    print("\n下一步: 运行 predict_intent.py 进行预测")


if __name__ == "__main__":
    main()
