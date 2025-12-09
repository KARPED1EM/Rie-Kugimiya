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

    parser.add_argument("--data_file", default="data/dmslots/dmslots.txt", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/dmslots.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["dmslots"]


def repl(match):
    result = "{}".format(match.group(1))
    return result


def main():
    args = get_args()

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        with open(args.data_file, "r", encoding="utf-8") as fin:
            for row in fin:
                row = str(row).strip()
                row = row.split("|")

                if len(row) != 2:
                    raise AssertionError
                label = row[0]
                text = row[1]

                text = text.strip()
                if text in text_set:
                    continue
                text_set.add(text)

                if label in ("domain.dialog.salut", "domain.fillslot", "domain.non"):
                    continue
                if text.__contains__("**"):
                    continue

                text = re.sub(r"<.*?>(.*?)</.*?>", repl, text)
                if text.__contains__("<"):
                    print(text)
                    raise AssertionError

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
                    "text": text.strip(),
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
