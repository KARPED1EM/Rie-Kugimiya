#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
https://huggingface.co/datasets/FastFit/hwu_64

https://arxiv.org/abs/1903.05566

https://github.com/jianguoz/Few-Shot-Intent-Detection
"""
import argparse
from collections import defaultdict
import json
import os
import sys

pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(pwd, "../../"))

from datasets import load_dataset
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--dataset_path", default="FastFit/hwu_64", type=str)
    parser.add_argument(
        "--dataset_cache_dir",
        default=(project_path / "hub_datasets").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/hwu_64.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["hwu_64"]


def main():
    args = get_args()

    dataset_dict = load_dataset(
        path=args.dataset_path,
        cache_dir=args.dataset_cache_dir,
    )
    print(dataset_dict)

    # labels = set()
    # for k, v in dataset_dict.items():
    #     for sample in tqdm(v):
    #         text = sample["text"]
    #         label = sample["label"]
    #         names.add(label)
    #
    # result = defaultdict(dict)
    # for name in labels:
    #     result["version_0"][name] = [
    #         name,
    #     ]
    #     result["version_1"][name] = [
    #         " ".join(name.split(" ")),
    #     ]
    #     result["version_2"][name] = [
    #         " ".join([w[0].upper() + w[1:] for w in name.split(" ")]),
    #     ]
    #     result["version_3"][name] = [
    #         "".join([w[0].upper() + w[1:] for w in name.split(" ")]),
    #     ]
    #
    # result = json.dumps(result, indent=4, ensure_ascii=False)
    # print(result)
    # exit(0)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for k, v in dataset_dict.items():
            for sample in tqdm(v):
                text = sample["text"]
                label = sample["label"]

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
                    "data_source": "hwu_64",
                    "split": k
                }
                row = json.dumps(row, ensure_ascii=False)
                f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
