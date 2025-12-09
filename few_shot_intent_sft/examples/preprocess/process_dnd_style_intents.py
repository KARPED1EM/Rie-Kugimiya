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

    parser.add_argument("--dataset_path", default="neurae/dnd_style_intents", type=str)
    parser.add_argument(
        "--dataset_cache_dir",
        default=(project_path / "hub_datasets").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/dnd_style_intents.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["dnd_style_intents"]


def main():
    args = get_args()

    dataset_dict = load_dataset(
        path=args.dataset_path,
        cache_dir=args.dataset_cache_dir,
    )
    print(dataset_dict)

    result = defaultdict(dict)
    for k, v in dataset_dict.items():
        for sample in tqdm(v):
            text = sample["examples"]
            label = sample["label_names"]
            label = label.lower()

            result["version_0"][label] = [
                label,
            ]
            result["version_1"][label] = [
                "_".join(label.split(" ")),
            ]
            result["version_2"][label] = [
                " ".join([w[0].upper() + w[1:] for w in label.split(" ")]),
            ]
            result["version_3"][label] = [
                "".join([w[0].upper() + w[1:] for w in label.split(" ")]),
            ]
            result["version_4"][label] = [
                label.upper(),
            ]

    result = json.dumps(result, indent=4, ensure_ascii=False)
    # print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for k, v in dataset_dict.items():
            for sample in tqdm(v):
                text = sample["examples"]
                label = sample["label_names"]
                label = label.lower()
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
                    "data_source": "dnd_style_intents",
                    "split": k
                }
                row = json.dumps(row, ensure_ascii=False)
                f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
