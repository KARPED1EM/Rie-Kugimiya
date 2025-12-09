#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import random
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_file", default="data/smp2019_task1/train.json", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/smp2019_task1_domain.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["smp2019_task1_domain"]


def main():
    args = get_args()

    with open(args.data_file, "r", encoding="utf-8") as fin:
        data = json.load(fin)

    # label map
    result = defaultdict(dict)
    for row in data:
        text = row["text"]
        label = row["domain"]
        intent = row["intent"]
        label = label.lower()

        result["version_0"][label] = [
            label,
        ]
        result["version_1"][label] = [
            " ".join(label.split("_")),
        ]
        result["version_2"][label] = [
            " ".join([w[0].upper() + w[1:] for w in label.split("_")]),
        ]
        result["version_3"][label] = [
            "".join([w[0].upper() + w[1:] for w in label.split("_")]),
        ]
        result["version_4"][label] = [
            label.upper(),
        ]

    result = json.dumps(result, indent=4, ensure_ascii=False)
    # print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        for row in data:
            text = row["text"]
            label = row["domain"]
            intent = row["intent"]
            label = label.lower()

            text = text.strip()
            if text in text_set:
                continue
            text_set.add(text)

            labels = dict()
            for version, label_to_intents in label_map.items():
                intents = label_to_intents[label]
                labels[version] = intents

            num = random.random()
            if num < 0.9:
                split = "train"
            elif num < 0.95:
                split = "validation"
            else:
                split = "test"

            row = {
                "text": text,
                "label": label,
                # "intents": labels,
                "data_source": "smp2019_task1_domain",
                "split": split
            }
            row = json.dumps(row, ensure_ascii=False)
            fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
