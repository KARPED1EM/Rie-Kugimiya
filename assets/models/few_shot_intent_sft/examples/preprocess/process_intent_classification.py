#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
import random
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

from datasets import load_dataset
import numpy as np
import pandas as pd
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv_file",
        default="data/intent_classification/train.csv",
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/intent_classification.jsonl"),
        type=str
    )
    parser.add_argument("--seed", default=3407, type=str, help="https://arxiv.org/abs/2109.08203")

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["intent_classification"]


def main():
    args = get_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    df = pd.read_csv(args.csv_file)
    names = df["intent"].tolist()
    names = list(set(names))

    result = defaultdict(dict)
    for name in names:
        result["version_0"][name] = [
            name,
        ]

    result = json.dumps(result, indent=4, ensure_ascii=False)
    print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for i, row in df.iterrows():
            text = row["text"]
            label = row["intent"]

            text = text.strip()
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
                "data_source": "intent_classification",
                "split": "train" if random.random() < 0.9 else "test"
            }
            row = json.dumps(row, ensure_ascii=False)
            f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
