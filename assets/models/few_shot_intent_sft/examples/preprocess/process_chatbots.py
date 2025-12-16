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

from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_file", default="data/chatbots/Intent.json", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/chatbots.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["chatbots"]


def main():
    args = get_args()

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        with open(args.data_file, "r", encoding="utf-8") as fin:
            data = json.load(fin)
        intents = data["intents"]

        for js in intents:
            label = js["intent"]
            text_list = js["text"]

            for text in text_list:

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
                    "data_source": "crosswoz",
                    "split": split
                }
                row = json.dumps(row, ensure_ascii=False)
                fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
