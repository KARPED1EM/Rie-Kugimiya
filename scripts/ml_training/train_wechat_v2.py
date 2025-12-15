# -*- coding: utf-8 -*-
"""
微信聊天意图识别模型训练（优化版）

特点：
1. 基于 telemarketing_intent_cn 数据集
2. 黑名单过滤不适合微信聊天的意图
3. 支持混合 crosswoz 数据集（可选）
4. 样本平衡和数据增强
5. 适配 Windows 本地训练

直接运行：python train_wechat_v2.py
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
from sklearn.model_selection import train_test_split
import numpy as np


# ============================================================================
# 配置参数
# ============================================================================

# 自动检测项目路径
SCRIPT_DIR = Path(__file__).parent.absolute()
if SCRIPT_DIR.name == "scripts":
    PROJECT_ROOT = SCRIPT_DIR.parent
else:
    PROJECT_ROOT = SCRIPT_DIR

# 数据集路径
DATA_DIR = PROJECT_ROOT / "few_shot_intent_sft" / "data"
TELEMARKETING_DATA = DATA_DIR / "telemarketing_intent_cn.jsonl"
CROSSWOZ_DATA = DATA_DIR / "crosswoz.jsonl"  # 可选

# 模型保存路径
OUTPUT_DIR = PROJECT_ROOT / "wechat_intent_model"

# 训练参数
MIN_SAMPLES = 20  # 每个意图最少样本数（提高质量）
MAX_SAMPLES_PER_INTENT = 300  # 每个意图最多样本数（平衡数据）
BATCH_SIZE = 16
EPOCHS = 4  # 增加到4轮
TEST_SIZE = 0.2
RANDOM_SEED = 42

# 是否混合 CrossWOZ 数据集（更自然的对话）
USE_CROSSWOZ = True


# ============================================================================
# 微信聊天意图黑名单
# ============================================================================

# 不适合微信聊天的意图（电销特定、敏感内容等）
BLACKLIST_INTENTS = {
    # 电销特定意图
    "查询类",
    "查询(产品信息)",
    "查询(价格)",
    "查询(优惠)",
    "查询(库存)",
    "查询(物流)",
    "查询(订单)",
    "查询(账户)",
    "查询(余额)",
    "实体(产品)",
    "实体(价格)",
    "实体(时间)",
    "实体(地点)",
    "实体(人名)",
    "实体(公司)",
    "实体识别",
    "产品推荐",
    "促销活动",
    "优惠信息",
    "下单",
    "支付",
    "退款",
    "投诉",
    "售后",
    # 敏感内容
    "政治敏感",
    "污言秽语",
    "色情低俗",
    "暴力血腥",
    "违法犯罪",
    "广告营销",
    "诈骗信息",
    # 不常用或容易误判的意图
    "肯定(没问题)",  # 容易误判"你脑子没问题吧"
    "否定(没有)",  # 容易误判
    "转人工",
    "挂断电话",
    "保持通话",
    "重复",
    "澄清",
    "确认信息",
    "核实身份",
    "录音提示",
    "系统提示",
}

# 保留的通用对话意图
KEEP_INTENTS = {
    # 问候和礼貌
    "招呼用语",
    "礼貌用语",
    "感谢",
    "道歉",
    "问候",
    "告别",
    "结束用语",
    # 肯定和否定
    "肯定",
    "肯定(好的)",
    "肯定(是的)",
    "肯定(可以)",
    "肯定(同意)",
    "否定",
    "否定(不是)",
    "否定(不要)",
    "否定(不可以)",
    "拒绝",
    # 疑问
    "疑问",
    "疑问(是什么)",
    "疑问(为什么)",
    "疑问(怎么样)",
    "疑问(在哪里)",
    "疑问(什么时候)",
    "反问",
    # 情感
    "开心",
    "难过",
    "生气",
    "惊讶",
    "担心",
    "无聊",
    "兴奋",
    # 请求和建议
    "请求",
    "请求(帮助)",
    "建议",
    "邀请",
    "提醒",
    # 回应
    "同意",
    "不同意",
    "理解",
    "不理解",
    "知道了",
    "不知道",
    # 其他常用
    "闲聊",
    "调侃",
    "玩笑",
    "夸奖",
    "批评",
    "抱怨",
    "安慰",
    "鼓励",
    "关心",
    "祝福",
}


# ============================================================================
# 数据加载和处理
# ============================================================================


def load_telemarketing_data(file_path):
    """加载 telemarketing_intent_cn 数据集"""
    print(f"📂 加载数据: {file_path.name}")

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
    print(f"   原始数据: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    # 应用黑名单
    df = df[~df["label"].isin(BLACKLIST_INTENTS)]
    print(f"   黑名单过滤后: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    # 过滤样本数不足的意图
    intent_counts = Counter(df["label"])
    valid_intents = [
        intent for intent, count in intent_counts.items() if count >= MIN_SAMPLES
    ]
    df = df[df["label"].isin(valid_intents)]
    print(f"   样本数过滤后: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    return df


def load_crosswoz_data(file_path):
    """加载 CrossWOZ 数据集（更自然的对话）"""
    if not file_path.exists():
        print(f"⚠️  CrossWOZ 数据集不存在: {file_path.name}")
        return pd.DataFrame()

    print(f"📂 加载 CrossWOZ 数据: {file_path.name}")

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
    print(f"   原始数据: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    # 映射 CrossWOZ 意图到通用意图
    intent_mapping = {
        "greet": "招呼用语",
        "thank": "礼貌用语",
        "bye": "结束用语",
    }

    df["label"] = df["label"].map(intent_mapping)
    df = df.dropna(subset=["label"])

    print(f"   映射后: {len(df)} 样本, {len(df['label'].unique())} 个意图")

    return df


def balance_dataset(df, max_samples_per_intent):
    """平衡数据集：限制每个意图的最大样本数"""
    print(f"\n⚖️  平衡数据集（每个意图最多 {max_samples_per_intent} 样本）")

    balanced_dfs = []
    for intent in df["label"].unique():
        intent_df = df[df["label"] == intent]
        if len(intent_df) > max_samples_per_intent:
            intent_df = intent_df.sample(
                n=max_samples_per_intent, random_state=RANDOM_SEED
            )
        balanced_dfs.append(intent_df)

    balanced_df = pd.concat(balanced_dfs, ignore_index=True)
    print(f"   平衡后: {len(balanced_df)} 样本")

    return balanced_df


def prepare_dataset():
    """准备训练数据集"""
    print("=" * 70)
    print("📊 准备数据集")
    print("=" * 70)

    # 加载 telemarketing 数据
    df_telemarketing = load_telemarketing_data(TELEMARKETING_DATA)

    # 加载 CrossWOZ 数据（可选）
    if USE_CROSSWOZ and CROSSWOZ_DATA.exists():
        df_crosswoz = load_crosswoz_data(CROSSWOZ_DATA)
        if not df_crosswoz.empty:
            # 合并数据集
            df = pd.concat([df_telemarketing, df_crosswoz], ignore_index=True)
            print(f"\n✅ 合并数据集: {len(df)} 样本")
        else:
            df = df_telemarketing
    else:
        df = df_telemarketing

    # 平衡数据集
    df = balance_dataset(df, MAX_SAMPLES_PER_INTENT)

    # 统计意图分布
    intent_counts = Counter(df["label"])
    print(f"\n📈 意图分布（共 {len(intent_counts)} 个意图）:")
    for intent, count in intent_counts.most_common(10):
        print(f"   {intent}: {count} 样本")
    if len(intent_counts) > 10:
        print(f"   ... 还有 {len(intent_counts) - 10} 个意图")

    # 创建标签映射
    unique_intents = sorted(df["label"].unique())
    intent2id = {intent: i for i, intent in enumerate(unique_intents)}
    id2intent = {i: intent for intent, i in intent2id.items()}

    df["label_id"] = df["label"].map(intent2id)

    # 划分训练集和测试集
    train_df, test_df = train_test_split(
        df, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=df["label_id"]
    )

    print(f"\n📦 数据集划分:")
    print(f"   训练集: {len(train_df)} 样本")
    print(f"   测试集: {len(test_df)} 样本")

    # 转换为 Hugging Face Dataset
    train_dataset = Dataset.from_pandas(
        train_df[["text", "label_id"]].rename(columns={"label_id": "label"})
    )
    test_dataset = Dataset.from_pandas(
        test_df[["text", "label_id"]].rename(columns={"label_id": "label"})
    )

    dataset = DatasetDict({"train": train_dataset, "test": test_dataset})

    return dataset, intent2id, id2intent


# ============================================================================
# 模型训练
# ============================================================================


def compute_metrics(eval_pred):
    """评估指标"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=-1)

    accuracy = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average="weighted")

    return {"accuracy": accuracy, "f1": f1}


def train_model(dataset, intent2id, id2intent):
    """训练模型"""
    num_labels = len(intent2id)

    print("\n" + "=" * 70)
    print("🤖 加载模型")
    print("=" * 70)
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
    print("\n" + "=" * 70)
    print("🔧 数据预处理")
    print("=" * 70)

    def tokenize(examples):
        return tokenizer(
            examples["text"], truncation=True, padding="max_length", max_length=128
        )

    tokenized_dataset = dataset.map(tokenize, batched=True)
    print("✅ 数据预处理完成")

    # 训练配置
    print("\n" + "=" * 70)
    print("🚀 开始训练")
    print("=" * 70)
    print(f"批次大小: {BATCH_SIZE}")
    print(f"训练轮数: {EPOCHS}")
    print(f"预估时间: 4-6 小时（CPU）\n")

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        num_train_epochs=EPOCHS,
        weight_decay=0.01,
        logging_steps=50,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        fp16=False,  # Windows CPU 不支持 FP16
        report_to="none",  # 不上传到 wandb
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"],
        compute_metrics=compute_metrics,
    )

    # 开始训练
    trainer.train()

    return trainer, tokenizer


def evaluate_model(trainer, tokenized_dataset, intent2id):
    """评估模型"""
    print("\n" + "=" * 70)
    print("📊 评估模型")
    print("=" * 70)

    results = trainer.evaluate()
    print(f"准确率: {results['eval_accuracy']:.4f}")
    print(f"F1 Score: {results['eval_f1']:.4f}")

    # 详细分类报告
    predictions = trainer.predict(tokenized_dataset["test"])
    pred_labels = np.argmax(predictions.predictions, axis=-1)
    true_labels = predictions.label_ids

    print("\n" + "=" * 70)
    print("📋 分类报告")
    print("=" * 70)
    print(
        classification_report(
            true_labels,
            pred_labels,
            target_names=list(intent2id.keys()),
            zero_division=0,
        )
    )


def save_model(trainer, tokenizer, intent2id, id2intent):
    """保存模型"""
    print("\n" + "=" * 70)
    print("💾 保存模型")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    # 保存意图映射
    mapping_path = OUTPUT_DIR / "intent_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(
            {"intent2id": intent2id, "id2intent": id2intent},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✅ 模型已保存到: {OUTPUT_DIR}")

    # 保存意图列表（方便查看）
    intents_path = OUTPUT_DIR / "intents.txt"
    with open(intents_path, "w", encoding="utf-8") as f:
        f.write("微信聊天意图列表\n")
        f.write("=" * 50 + "\n\n")
        for i, intent in enumerate(sorted(intent2id.keys()), 1):
            f.write(f"{i}. {intent}\n")

    print(f"✅ 意图列表已保存到: {intents_path}")


# ============================================================================
# 主函数
# ============================================================================


def main():
    print("\n" + "=" * 70)
    print("🎯 微信聊天意图识别模型训练（优化版）")
    print("=" * 70)
    print(f"\n项目路径: {PROJECT_ROOT}")
    print(f"数据集: {TELEMARKETING_DATA.name}")
    if USE_CROSSWOZ:
        print(f"        + {CROSSWOZ_DATA.name} (可选)")
    print(f"模型保存: {OUTPUT_DIR}\n")

    # 检查数据集
    if not TELEMARKETING_DATA.exists():
        print(f"❌ 错误: 数据集不存在")
        print(f"路径: {TELEMARKETING_DATA}\n")

        # 列出可用数据集
        if DATA_DIR.exists():
            print("可用的数据集:")
            for f in sorted(DATA_DIR.glob("*.jsonl"))[:10]:
                print(f"  - {f.name}")
        return

    # 准备数据集
    dataset, intent2id, id2intent = prepare_dataset()

    # 训练模型
    trainer, tokenizer = train_model(dataset, intent2id, id2intent)

    # 数据预处理（用于评估）
    def tokenize(examples):
        return tokenizer(
            examples["text"], truncation=True, padding="max_length", max_length=128
        )

    tokenized_dataset = dataset.map(tokenize, batched=True)

    # 评估模型
    evaluate_model(trainer, tokenized_dataset, intent2id)

    # 保存模型
    save_model(trainer, tokenizer, intent2id, id2intent)

    # 完成
    print("\n" + "=" * 70)
    print("✅ 训练完成！")
    print("=" * 70)
    print(f"模型位置: {OUTPUT_DIR}")
    print(f"意图数量: {len(intent2id)}")
    print("\n下一步:")
    print("  1. 查看意图列表: intents.txt")
    print("  2. 运行预测: python predict_wechat.py")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
