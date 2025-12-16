#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import json
import os
import random
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

import numpy as np
import pandas as pd
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--excel_file",
        default=(project_path / "telemarketing_intent_cn.xlsx").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/telemarketing_intent_cn.jsonl"),
        type=str
    )
    parser.add_argument("--seed", default=3407, type=str, help="https://arxiv.org/abs/2109.08203")

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["telemarketing_intent_cn"]


def main():
    args = get_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    df = pd.read_excel(args.excel_file)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for i, row in tqdm(df.iterrows(), total=len(df)):
            source = row["source"]
            selected = row["selected"]
            text = row["text"]
            label = row["label1"]

            text = str(text).strip()
            if text in text_set:
                continue
            text_set.add(text)

            if label in ("无关领域",):
                continue

            if selected != 1:
                continue
            if source not in ("download", "common", "translate"):
                continue

            labels = dict()
            for version, label_to_intents in label_map.items():
                intents = label_to_intents[label]
                labels[version] = intents

            row = {
                "text": text,
                "label": label,
                # "intents": labels,
                "data_source": "telemarketing_intent_cn",
                "split": "train" if random.random() < 0.9 else "test"
            }
            row = json.dumps(row, ensure_ascii=False)
            f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
