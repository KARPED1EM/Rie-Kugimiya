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

from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_dir", default="data/book6", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/book6.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["book6"]


def main():
    args = get_args()

    data_dir = Path(args.data_dir)

    split_to_file = {
        "train_full.txt": "train",
        "test_full.txt": "test",
    }

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        for split_file, split in split_to_file.items():
            filename = data_dir / split_file
            with open(filename, "r", encoding="utf-8") as fin:
                for row in fin:
                    row = str(row).strip()
                    row = row.replace("\\", "")
                    row = row.split(" __label__")

                    text = row[0]
                    label = row[1]

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
                        "data_source": "book6",
                        "split": split
                    }
                    row = json.dumps(row, ensure_ascii=False)
                    fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
