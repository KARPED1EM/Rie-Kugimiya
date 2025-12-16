#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_dir", default="data/crosswoz", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/crosswoz.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["crosswoz"]


def main():
    args = get_args()

    data_dir = Path(args.data_dir)

    split_to_file = {
        "train.json": "train",
        "val.json": "validation",
        "test.json": "test",
    }

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        for split_file, split in split_to_file.items():
            filename = data_dir / split_file
            with open(filename, "r", encoding="utf-8") as fin:
                split_data = json.load(fin)

            for k1, v1 in split_data.items():
                conversation = v1["messages"]
                for msg in conversation:
                    text = msg["content"]
                    dialog_act = msg["dialog_act"]
                    role = msg["role"]
                    if role == "sys":
                        continue

                    text = text.strip()
                    if text in text_set:
                        continue
                    text_set.add(text)

                    for act in dialog_act:
                        category1 = act[0]
                        if category1 != "General":
                            continue

                        label = act[1]

                        labels = dict()
                        for version, label_to_intents in label_map.items():
                            intents = label_to_intents[label]
                            labels[version] = intents

                        row = {
                            "text": text,
                            "label": label,
                            # "intents": labels,
                            "data_source": "crosswoz",
                            "split": split
                        }
                        row = json.dumps(row, ensure_ascii=False)
                        fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
