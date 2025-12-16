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

    parser.add_argument("--data_dir", default="data/chinese_news_title", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/chinese_news_title.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["chinese_news_title"]


def main():
    args = get_args()

    data_dir = Path(args.data_dir)

    split_to_file = {
        "train_file.txt": "train",
        "test_file.txt": "test",
    }

    # make labels
    result = defaultdict(dict)
    for split_file, split in split_to_file.items():
        filename = data_dir / split_file
        with open(filename, "r", encoding="utf-8") as fin:
            for sample in fin:
                sample = str(sample).strip().split("\t")
                if len(sample) != 2:
                    raise AssertionError
                label = sample[0]

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
        for split_file, split in split_to_file.items():
            filename = data_dir / split_file
            with open(filename, "r", encoding="utf-8") as fin:
                for sample in fin:
                    sample = str(sample).strip().split("\t")
                    if len(sample) != 2:
                        raise AssertionError
                    label = sample[0]
                    text = sample[1]

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
                        "data_source": "chinese_news_title",
                        "split": split
                    }
                    row = json.dumps(row, ensure_ascii=False)
                    fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
