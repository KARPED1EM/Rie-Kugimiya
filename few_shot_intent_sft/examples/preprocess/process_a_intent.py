#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import random
import re
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

import pandas as pd
from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_dir", default="data/a_intent", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/a_intent.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["a_intent"]


def main():
    args = get_args()

    data_dir = Path(args.data_dir)

    split_to_file = {
        "train.csv": "train",
    }

    # label map
    result = defaultdict(dict)
    for split_file, split in split_to_file.items():
        filename = data_dir / split_file
        with open(filename, "r", encoding="utf-8") as fin:
            for row in fin:
                row = str(row).strip()
                row = row.split("\t")

                if len(row) != 2:
                    continue
                text = row[0]
                label = row[1]

                result["version_0"][label] = [
                    label,
                ]
                result["version_1"][label] = [
                    " ".join(label.split("-")),
                ]
                result["version_2"][label] = [
                    " ".join([w[0].upper() + w[1:] for w in label.split("-")]),
                ]
                result["version_3"][label] = [
                    " ".join([w[0].upper() + w[1:] for w in label.split("-")]),
                ]
                result["version_4"][label] = [
                    "_".join([w[0].upper() + w[1:] for w in label.split("-")]),
                ]

    result = json.dumps(result, indent=4, ensure_ascii=False)
    # print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        for split_file, split in split_to_file.items():
            filename = data_dir / split_file
            with open(filename, "r", encoding="utf-8") as fin:
                for row in fin:
                    row = str(row).strip()
                    row = row.split("\t")
                    if len(row) != 2:
                        print(row)
                        raise AssertionError

                    text = row[0]
                    label = row[1]
                    text = text.strip()

                    if text in text_set:
                        continue
                    text_set.add(text)

                    if label == "Other":
                        continue
                    # print(text)
                    # print(label)

                    labels = dict()
                    for version, label_to_intents in label_map.items():
                        intents = label_to_intents[label]
                        labels[version] = intents

                    row = {
                        "text": text,
                        "label": label,
                        # "intents": labels,
                        "data_source": "a_intent",
                        "split": split
                    }
                    row = json.dumps(row, ensure_ascii=False)
                    fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
