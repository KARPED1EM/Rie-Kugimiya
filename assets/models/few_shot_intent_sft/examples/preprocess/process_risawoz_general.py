#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Inform
Greeting
Request
Bye
General
"""
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

    parser.add_argument("--dataset_path", default="GEM/RiSAWOZ", type=str)
    parser.add_argument(
        "--dataset_cache_dir",
        default=(project_path / "hub_datasets").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/ri_sawoz_general.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["ri_sawoz_general"]


def main():
    args = get_args()

    dataset_dict = load_dataset(
        path=args.dataset_path,
        cache_dir=args.dataset_cache_dir,
    )
    print(dataset_dict)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as fout:
        for split, dataset in dataset_dict.items():
            for sample in tqdm(dataset):
                dialogue = sample["dialogue"]

                for user_utterance, user_actions in zip(dialogue["user_utterance"], dialogue["user_actions"]):
                    text = user_utterance.strip()
                    if text in text_set:
                        continue
                    text_set.add(text)

                    for user_action in user_actions:
                        label = user_action[0]
                        category1 = user_action[1]

                        if label not in ("Bye", "Greeting"):
                            continue
                        if category1 not in ("通用",):
                            continue

                        labels = dict()
                        for version, label_to_intents in label_map.items():
                            intents = label_to_intents[label]
                            labels[version] = intents

                        row = {
                            "text": text,
                            "label": label,
                            # "intents": labels,
                            "data_source": "ri_sawoz_general",
                            "split": split
                        }
                        row = json.dumps(row, ensure_ascii=False)
                        fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
