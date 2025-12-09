#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--dataset_path", default="m-a-p/COIG-CQIA", type=str)
    parser.add_argument(
        "--dataset_cache_dir",
        default=(project_path / "hub_datasets").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/coig_cqia.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["coig_cqia"]


def main():
    args = get_args()

    dataset_dict = load_dataset(
        path=args.dataset_path,
        cache_dir=args.dataset_cache_dir,
        # streaming=True
    )
    print(dataset_dict)

    result = defaultdict(dict)
    for split, dataset in dataset_dict.items():
        for sample in tqdm(dataset):
            instruction = sample["instruction"]
            task_type = sample["task_type"]
            minor = task_type["minor"]
            label = minor[0]

            result["version_0"][label] = minor

    result = json.dumps(result, indent=4, ensure_ascii=False)
    # print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for split, dataset in dataset_dict.items():
            for sample in tqdm(dataset):
                text = sample["instruction"]
                task_type = sample["task_type"]
                minor = task_type["minor"]
                label = minor[0]

                if label in ("词性标注", "分词", "文本分类", "推理", "摘要", "填空",
                             "词分割", "标题", "自然语言理解", "繁体", "对话", "诗词",
                             "分类", "相似案例匹配", "知识", "宋词", "扩写", "剧评",
                             "概念解析", "逻辑推理", "知识问答", "百科问答", "wikihow",
                             "小红书风格文本", "详细介绍", "知乎问答", "考研", "影评",
                             "书评", "拼音", "生成注释,幽默", "缩写", "因果分析", "问答", "选择题"):
                    continue

                if text in text_set:
                    continue
                text_set.add(text)

                labels = dict()
                for version, label_to_intents in label_map.items():
                    intents = label_to_intents[label]
                    labels[version] = intents

                row = {
                    "text": text,
                    "label": label,
                    # "intents": labels,
                    "data_source": "coig_cqia",
                    "split": split
                }
                row = json.dumps(row, ensure_ascii=False)
                f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
