#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
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

    parser.add_argument("--data_file", default="data/cmid/CMID.json", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/cmid_4class.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["cmid_4class"]


def main():
    args = get_args()

    with open(args.data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # label map
    result = defaultdict(dict)
    for sample in data:
        text = sample["originalText"]
        label_4class = sample["label_4class"]
        label_36class = sample["label_36class"]

        if len(label_4class) != 1:
            print(label_4class)
            raise AssertionError
        if len(label_36class) != 1:
            print(label_36class)
            raise AssertionError
        label_4class = label_4class[0]
        label_36class = label_36class[0]

        label = label_4class
        # label = label_36class

        if str(label).startswith("'"):
            label = label[1:]
        if str(label).endswith("'"):
            label = label[:-1]

        result["version_0"][label] = [
            label,
        ]
    result = json.dumps(result, indent=4, ensure_ascii=False)
    # print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        for sample in data:
            text = sample["originalText"]
            label_4class = sample["label_4class"]
            label_36class = sample["label_36class"]

            text = text.strip()
            if text in text_set:
                continue
            text_set.add(text)

            if len(label_4class) != 1:
                print(label_4class)
                raise AssertionError
            if len(label_36class) != 1:
                print(label_36class)
                raise AssertionError
            label_4class = label_4class[0]
            label_36class = label_36class[0]

            label = label_4class
            # label = label_36class

            if str(label).startswith("'"):
                label = label[1:]
            if str(label).endswith("'"):
                label = label[:-1]

            labels = dict()
            for version, label_to_intents in label_map.items():
                try:
                    intents = label_to_intents[label]
                except Exception as e:
                    print(label)
                    print(text)
                    raise e
                labels[version] = intents

            num = random.random()
            if num < 0.8:
                split = "train"
            elif num < 0.9:
                split = "validation"
            else:
                split = "test"

            row = {
                "text": text,
                "label": label,
                # "intents": labels,
                "data_source": "dmslots",
                "split": split
            }
            row = json.dumps(row, ensure_ascii=False)
            fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
