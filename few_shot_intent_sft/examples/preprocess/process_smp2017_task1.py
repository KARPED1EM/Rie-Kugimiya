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

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_dir", default="data/smp2017_task1", type=str)
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/smp2017_task1.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["smp2017_task1"]


def main():
    args = get_args()

    data_dir = Path(args.data_dir)

    split_to_file = {
        "train": "train",
        "develop": "validation",
        "test": "test",
    }

    # label map
    result = defaultdict(dict)
    for split_dir, split in split_to_file.items():
        split_dir = data_dir / split_dir
        for filename in split_dir.glob("*.txt"):
            name = filename.stem
            label = name.split("_", maxsplit=1)[-1]

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
        for split_dir, split in split_to_file.items():
            split_dir = data_dir / split_dir
            for filename in split_dir.glob("*.txt"):
                name = filename.stem
                label = name.split("_", maxsplit=1)[-1]
                with open(filename.as_posix(), "r", encoding="utf-8") as fin:
                    for row in fin:
                        text = str(row).strip()
                        text = text.replace("﻿", "")

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
                            "data_source": "smp2017_task1",
                            "split": split
                        }
                        row = json.dumps(row, ensure_ascii=False)
                        fout.write("{}\n".format(row))

    return


if __name__ == '__main__':
    main()
