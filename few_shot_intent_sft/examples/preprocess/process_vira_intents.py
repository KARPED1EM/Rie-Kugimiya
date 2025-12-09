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
import requests
from tqdm import tqdm

from few_shot_intent_sft import DatasetLabels
from project_settings import project_path


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--dataset_path", default="codesj/vira-intents-live", type=str)
    parser.add_argument(
        "--dataset_cache_dir",
        default=(project_path / "hub_datasets").as_posix(),
        type=str
    )
    parser.add_argument(
        "--output_file",
        default=(project_path / "data/vira_intents.jsonl"),
        type=str
    )

    args = parser.parse_args()
    return args


label_map = DatasetLabels.label_map["vira_intents"]


names = [
    "COVID-19 is not as dangerous as they say",
    "Do I need to continue safety measures after getting the vaccine?",
    "How long until I will be protected after taking the vaccine?",
    "How many people already got the vaccine?",
    "I am afraid the vaccine will change my DNA",
    "I am concerned getting the vaccine because I have a pre-existing condition",
    "I am concerned I will be a guinea pig",
    "I'm concerned the vaccine will make me sick.",
    "I am not sure if I can trust the government",
    "I am young and healthy so I don't think I should vaccinate",
    "I distrust this vaccine",
    "How much will I have to pay for the vaccine",
    "I don't think the vaccine is necessary",
    "I don't trust the companies producing the vaccines",
    "I don't want my children to get the vaccine",
    "I think the vaccine was not tested on my community",
    "I'm not sure it is effective enough",
    "I'm waiting to see how it affects others",
    "COVID vaccines can be worse than the disease itself",
    "Long term side-effects were not researched enough",
    "Are regular safety measures enough to stay healthy?",
    "Should people that had COVID get the vaccine?",
    "Side effects and adverse reactions worry me",
    "The COVID vaccine is not safe",
    "The vaccine should not be mandatory",
    "Do vaccines work against the mutated strains of COVID-19?",
    "They will put a chip/microchip to manipulate me",
    "What can this chatbot do?",
    "What is in the vaccine?",
    "Which one of the vaccines should I take?",
    "Will I test positive after getting the vaccine?",
    "Can other vaccines protect me from COVID-19?",
    "Do I qualify for the vaccine?",
    "I don't trust vaccines if they're from China or Russia",
    "Are the side effects worse for the second shot",
    "Can I get a second dose even after a COVID exposure?",
    "Can I get other vaccines at the same time?",
    "Can I get the vaccine if I have allergies?",
    "Can I get the vaccine if I have had allergic reactions to vaccines before?",
    "Can I have the vaccine as a Catholic?",
    "Can I have the vaccine if I'm allergic to penicillin?",
    "Can I still get COVID even after being vaccinated?",
    "Can you mix the vaccines?",
    "COVID-19 vaccines cause brain inflammation",
    "Do the COVID-19 vaccines cause Bell's palsy?",
    "Do the mRNA vaccines contain preservatives, like thimerosal?",
    "Do the vaccines work in obese people?",
    "Do you have to be tested for COVID before you vaccinated?",
    "Does the vaccine contain animal products?",
    "Does the vaccine contain live COVID virus?",
    "Does the vaccine impact pregnancy?",
    "Does the vaccine work if I do not experience any side effects?",
    "How can I stay safe until I'm vaccinated?",
    "How do I know I'm getting a legitimate, authorized vaccine?",
    "How do I report an adverse reaction or side-effect",
    "How long do I have to wait between doses?",
    "How many doses do I need?",
    "How was the vaccine tested?",
    "I am concerned about getting the vaccine because of my medications.",
    "I don't want the v-safe app monitoring or tracking me",
    "I don't want to share my personal information",
    "Is breastfeeding safe with the vaccine",
    "Is the Johnson & Johnson vaccine less effective than the others?",
    "Is the vaccine halal?",
    "Is the vaccine Kosher?",
    "Is there vaccine safety monitoring?",
    "Other vaccines have caused long-term health problems",
    "Should I get the COVID-19 vaccine if I am immunocompromised",
    "Should I get the vaccine if I've tested positive for antibodies?",
    "The vaccine includes fetal tissue or abortion by-products",
    "The vaccine was rushed",
    "Vaccine side effects are not getting reported",
    "What does vaccine efficacy mean?",
    "What if I still get infected even after receiving the vaccine?",
    "What if I've been treated with convalescent plasma?",
    "What if I've been treated with monoclonal antibodies?",
    "What is mRNA?",
    "What is the difference between mRNA and viral vector vaccines?",
    "When can I go back to normal life?",
    "Why are there different vaccines?",
    "Why do I need the COVID vaccine if I don't get immunized for flu",
    "Why do we need the vaccine if we can wait for herd immunity?",
    "Why get vaccinated if I can still transmit the virus?",
    "Will 1 dose of vaccine protect me?",
    "Can I take a pain reliever when I get vaccinated?",
    "Will the vaccine benefit me?",
    "Will the vaccine make me sterile or infertile?",
    "Can we change the vaccine quickly if the virus mutates?",
    "Can I get COVID-19 from the vaccine?",
    "I am still experiencing COVID symptoms even after testing negative, should I still take the vaccine?",
    "Can children get the vaccine?",
    "Can we choose which vaccine we want?",
    "How long does the immunity from the vaccine last?",
    "The mortality rate of COVID-19 is low, why should I get the vaccine?",
    "There are many reports of severe side effects or deaths from the vaccine",
    "How can I get the vaccine?",
    "I am worried about blood clots as a result of the vaccine",
    "what is covid?",
    "Who developed the vaccine?",
    "Which vaccines are available?",
    "What are the side effect of the vaccine?",
    "Can I meet in groups after I'm vaccinated?",
    "Is it safe to go to the gym indoors if I'm vaccinated?",
    "How do I protect myself indoors?",
    "What are the effects of long COVID?",
    "Do you need a social security number to get a COVID-19 vaccine?",
    "Do you need to be a U.S. citizen to get a COVID-19 vaccine?",
    "Is it okay for me to travel internationally if I'm vaccinated?",
    "Can my kids go back to school without a vaccine?",
    "Will I need a booster shot?",
    "If I live with an immuno-compromised individual, do I still need to wear a mask outdoors if I'm vaccinated?",
    "Does the vaccine prevent transmission?",
    "Why is AstraZeneca not approved in the USA?",
    "Do I need to change my masking and social distancing practices depending on which COVID-19 vaccine I got?",
    "Does the Pfizer vaccine cause myocarditis?",
    "Does the Pfizer vaccine cause heart problems?",
    "What can you tell me about COVID-19 vaccines?",
    "Are there medical contraindications to the vaccines?",
    "How many people died from COVID-19?",
    "What about reports of abnormal periods due to the vaccine?",
    "Do I need the vaccine?",
    "Tell me about the vaccine",
    "Is the Pfizer vaccine safe for young men?",
    "Will vaccination lead to more dangerous variants?",
    "Is it safe for my baby to get the vaccine?",
    "Did a volunteer in the Oxford trial die?",
    "Can I get COVID-19 twice?",
    "Are some vaccines safer for younger children than others?",
    "How long am I immune from COVID-19 if I had the virus?",
    "Are women more likely to get worse side effects than men?",
    "How do I convince my family and friends to get the COVID-19 vaccine?",
    "Why are COVID-19 vaccination rates slowing in the U.S.?",
    "I'm going to get vaccinated",
    "Is getting vaccinated painful?",
    "What do I do if I lose my COVID-19 vaccination card?",
    "Can I get swollen lymph nodes from the vaccine?",
    "Can my newborn become immune to COVID-19 if I'm vaccinated?",
    "COVID-19 is over, why should I get the vaccine?",
    "Did one woman die after getting the J&J vaccine?",
    "Do people become magnetic after getting vaccinated?",
    "Does the vaccine contain eggs?",
    "How is the COVID-19 vaccine different than others?",
    "How soon after I've had COVID-19 can I get the vaccination?",
    "Is it safe for my teen to get the vaccine?",
    "Is this Pfizer vaccine equally effective in kids as it is in adults?",
    "Were the COVID-19 vaccines tested on animals?",
    "What are the side effects of the vaccine in children?",
    "What is the delta variant?",
    "What is the J&J vaccine?",
    "What is the Moderna vaccine?",
    "What is the Pfizer vaccine?",
    "Where are we required to wear masks now?",
    "Who can get the Pfizer vaccine?",
    "Who can I talk to about COVID-19 in person?",
    "Why should I trust you?",
    "Will my child need my permission to get vaccinated?",
    "Will the US reach herd immunity?",
    "Will my child miss school when they get vaccinated?",
    "Is the vaccine FDA approved?",
    "Why do vaccinated people need to wear a mask indoors?",
    "Do vaccinated people need to quarantine if exposed to COVID-19?",
    "What is Ivermectin?",
    "Does the Johnson and Johnson vaccine cause Rare Nerve Syndrome?",
    "What is the difference between quarantine and isolation?",
    "Does the COVID-19 vaccine cause autism?",
    "Does the vaccine cause impotence?",
    "Who is required to get vaccinated under the federal vaccine mandate?",
    "Is the Delta variant more dangerous for kids?",
    "Will there be a booster shot for J&J and Moderna?",
    "Is the booster the same as the original vaccine?",
    "What are the side effects of booster shots?",
    "What is the difference between the third shot and a booster shot?",
    "How common are vaccine side effects?",
    "Why do my kids need a vaccine if they're unlikely to get sick with COVID-19?",
    "What happens if there is a COVID-19 case at my child's school?",
    "Are booster shot side effects worse than those from the second shot?",
    "Is the booster shot dangerous?",
    "Can I get the vaccine if I have Multiple Sclerosis?",
    "Do children receive the same dose of Pfizer as adults?",
    "What is the Omicron variant?",
    "How effective is the vaccine against the Omicron variant?",
    "How can I get free masks?",
    "Are the rapid, at-home tests accurate?",
    "Does a COVID-19 vaccine booster protect me against the omicron variant?",
    "What is the new omicron variant (BA.2)?",
    "Is the fourth shot available in the US?",
    "What mask should I be wearing?",
    "How do I request at-home tests for my family?",
    "Will insurance cover costs of the tests requested?",
    "Does the COVID-19 vaccine protect me against the \"stealth variant\"?",
    "Does the COVID-19 vaccine cause heart attacks?",
    "Does the COVID-19 vaccine affect white blood cells?",
    "Have the COVID-19 vaccines completed clinical trials?",
    "What is deltacron?",
    "How do I find the COVID-19 Community levels of my county?",
    "What is breakthrough infection?",
    "Does the COVID-19 vaccine cause tinnitus?",
    "My kids get too many injections as it is",
    "How many doses does my child under 5 need?",
    "Kids can still spread COVID after getting vaccinated",
    "Is the vaccine effective for children under 5",
    "Do I need the second booster dose?",
    "How is the Novavax vaccine different from the other vaccines?",
    "What is Paxlovid?",
    "Are children under 5 eligible for a vaccine?",
    "What is the Novavax vaccine?",
    "Was the vaccine tested in kids before authorization?",
    "What are the long-term effects of the vaccine for my kids?",
    "Can my child get the booster?",
    "Is the vaccine safe for children under 5?",
    "How do I explain the benefits of the vaccine to my school age children?",
    "What are the side effects of the Novavax vaccine?",
    "Can my infant or child get a Moderna vaccine?",
    "I prefer to wait and see how vaccines work for my child",
    "It's too experimental for my kids",
    "What does bivalent mean?",
    "Were the new boosters tested?",
    "Why didn't the new booster undergo clinical trials?",
    "Do I need another booster?",
    "How do the new boosters work?",
    "How many boosters can I get?",
    "Will the old boosters still be available?"
]


def main():
    args = get_args()

    dataset_dict = load_dataset(
        path=args.dataset_path,
        cache_dir=args.dataset_cache_dir,
    )
    print(dataset_dict)

    result = defaultdict(dict)
    for name in names:
        result["version_0"][name] = [
            name,
        ]

    result = json.dumps(result, indent=4, ensure_ascii=False)
    print(result)

    text_set = set()
    with open(args.output_file, "w", encoding="utf-8") as f:
        for k, v in dataset_dict.items():
            for sample in tqdm(v):
                text = sample["text"]
                label = sample["label"]

                text = str(text).strip()
                if text in text_set:
                    continue
                text_set.add(text)

                label = names[label]
                labels = dict()
                for version, label_to_intents in label_map.items():
                    intents = label_to_intents[label]
                    labels[version] = intents

                row = {
                    "text": text.strip(),
                    "label": label,
                    # "intents": labels,
                    "data_source": "vira_intents",
                    "split": k
                }
                row = json.dumps(row, ensure_ascii=False)
                f.write("{}\n".format(row))
    return


if __name__ == '__main__':
    main()
