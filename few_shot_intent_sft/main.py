#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datasets import load_dataset, DownloadMode
from tqdm import tqdm


dataset = load_dataset(
    "few_shot_intent_sft.py",
    # name="a_intent_prompt",
    # name="amazon_massive_intent_en_us_prompt",
    # name="amazon_massive_intent_zh_cn_prompt",
    name="atis_intents_prompt",
    # name="banking77_prompt",
    # name="bi_text11_prompt",
    # name="bi_text27_prompt",
    # name="book6_prompt",
    # name="carer_prompt",
    # name="chatbots_prompt",
    # name="chinese_news_title_prompt",
    # name="cmid_4class_prompt",
    # name="cmid_36class_prompt",
    # name="coig_cqia_prompt",
    # name="conv_intent_prompt",
    # name="crosswoz_prompt",
    # name="dmslots_prompt",
    # name="dnd_style_intents_prompt",
    # name="emo2019_prompt",
    # name="finance21_prompt",
    # name="ide_intent_prompt",
    # name="jarvis_intent_prompt",
    # name="out_of_scope_prompt",
    # name="ri_sawoz_domain_prompt",
    # name="ri_sawoz_general_prompt",
    # name="small_talk_prompt",
    # name="smp2017_task1_prompt",
    # name="smp2019_task1_domain_prompt",
    # name="smp2019_task1_intent_prompt",
    # name="star_wars_prompt",
    # name="suicide_intent_prompt",
    # name="telemarketing_intent_cn_prompt",
    # name="vira_intents_prompt",
    # split="train",
    # split="validation",
    split="test",
    # streaming=True,
    cache_dir=None,
    download_mode=DownloadMode.FORCE_REDOWNLOAD
)

for sample in tqdm(dataset):
    # print(sample)
    prompt = sample["prompt"]
    response = sample["response"]
    not_applicable = sample["not_applicable"]
    intent_version = sample["intent_version"]

    print(prompt)
    print(response)
    print("-" * 150)
    exit(0)


if __name__ == '__main__':
    pass
