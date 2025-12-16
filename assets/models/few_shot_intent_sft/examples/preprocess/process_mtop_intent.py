#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
import json
import os
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, '../../'))

from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--dataset_path", default="mteb/mtop_intent", type=str)
    parser.add_argument("--dataset_name", default="en", type=str)
    parser.add_argument(
        "--dataset_cache_dir",
        default=(project_path / "hub_datasets").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/mtop_intent.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["mtop_intent"]


def main():
    args = get_args()

    dataset_dict = load_dataset(
        path=args.dataset_path,
        name=args.dataset_name,
        cache_dir=args.dataset_cache_dir,
    )
    print(dataset_dict)

    result = defaultdict(dict)
    for k, v in dataset_dict.items():
        for sample in tqdm(v):
            text = sample["text"]
            label = sample["label_text"]
            label = label.lower()

            result["version_0"][label.upper()] = [
                label,
            ]
            result["version_1"][label.upper()] = [
                " ".join(label.split("_")),
            ]
            result["version_2"][label.upper()] = [
                " ".join([w[0].upper() + w[1:] for w in label.split("_")]),
            ]
            result["version_3"][label.upper()] = [
                "".join([w[0].upper() + w[1:] for w in label.split("_")]),
            ]
            result["version_4"][label.upper()] = [
                label.upper(),
            ]

    result = json.dumps(result, indent=4, ensure_ascii=False)
    print(result)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for k, v in dataset_dict.items():
            for sample in tqdm(v):
                text = sample["text"]
                label = sample["label_text"]

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
                    "data_source": "mtop_intent",
                    "split": k
                }
                row = json.dumps(row, ensure_ascii=False)
                f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
