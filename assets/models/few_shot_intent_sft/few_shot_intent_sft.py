#!/usr/bin/python3
# -*- coding: utf-8 -*-
from collections import defaultdict
import json
from pathlib import Path
import random
import re
from typing import Any, Dict, List, Tuple

import datasets


# prompt dataset

class Variable(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return self.__str__()


class CommonVariable(Variable):
    def __init__(self, key: str, **kwargs):
        super(CommonVariable, self).__init__(**kwargs)
        self.key = key

        self.variable = self.kwargs[self.key]

    def __str__(self):
        return self.variable

    def __int__(self):
        return self.variable

    def __float__(self):
        return self.variable


class IntentDescriptionVariable(Variable):
    def __init__(self,
                 label_to_symbol: Dict[str, str],
                 label_to_intent: Dict[str, str],
                 label_to_intent_description: List[Tuple[str, str]],
                 **kwargs):
        super(IntentDescriptionVariable, self).__init__(**kwargs)
        self.label_to_symbol = label_to_symbol
        self.label_to_intent = label_to_intent
        self.label_to_intent_description = label_to_intent_description
        self.intent_description_template = self.kwargs["intent_description_template"]
        self.intent_description_sep = self.kwargs.get("intent_description_sep", "")

        label_to_symbol_list = list(sorted(self.label_to_symbol.items(), key=lambda x: x[1]))

        intent_description_list = list()
        for label, symbol in label_to_symbol_list:
            intent = self.label_to_intent[label]
            intent_description = self.label_to_intent_description[label]

            intent_description_template = Template(template=self.intent_description_template)
            item = intent_description_template.format(**{
                "intent_symbol": symbol,
                "intent": intent,
                "intent_description": intent_description,
            })
            intent_description_list.append(item)
        intent_description_list = self.intent_description_sep.join(intent_description_list)
        self.intent_description_list = intent_description_list.strip()

    def __str__(self):
        return self.intent_description_list


class ExamplesVariable(Variable):
    def __init__(self,
                 text_label_pairs: List[Tuple[str, str]],
                 label_to_intent: Dict[str, str],
                 label_to_symbol: Dict[str, str],
                 label_to_intent_description: List[Tuple[str, str]],
                 **kwargs):
        super(ExamplesVariable, self).__init__(**kwargs)
        self.label_to_intent = label_to_intent
        self.text_label_pairs = text_label_pairs
        self.label_to_symbol = label_to_symbol
        self.label_to_intent_description = label_to_intent_description
        self.example_template = self.kwargs["example_template"]
        self.example_sep = self.kwargs.get("example_sep", "")

        examples = list()
        for text, label in text_label_pairs:
            intent = label_to_intent[label]
            intent_symbol = self.label_to_symbol[label]
            intent_description = self.label_to_intent_description[label]

            example_template = Template(template=self.example_template)
            example = example_template.format(**{
                "text": text,
                "intent": intent,
                "intent_symbol": intent_symbol,
                "intent_description": intent_description,
            })
            examples.append(example)

        examples = self.example_sep.join(examples)
        self.examples = examples.strip()

    def __str__(self):
        return self.examples


class TextVariable(Variable):
    def __init__(self, text: str, **kwargs):
        super(TextVariable, self).__init__(**kwargs)
        self.text = text

    def __str__(self):
        return self.text


class IntentVariable(Variable):
    def __init__(self, intent: str, **kwargs):
        super(IntentVariable, self).__init__(**kwargs)
        self.intent = intent

    def __str__(self):
        return self.intent


class IntentSymbolVariable(Variable):
    def __init__(self, intent_symbol: str, **kwargs):
        super(IntentSymbolVariable, self).__init__(**kwargs)
        self.intent_symbol = intent_symbol

    def __str__(self):
        return str(self.intent_symbol)


class NotApplicableVariable(Variable):
    """not_applicable_variable: str or List[str]"""
    def __init__(self, key: str, **kwargs):
        super(NotApplicableVariable, self).__init__(**kwargs)
        self.key = key

        variable = self.kwargs[self.key]
        try:
            variable = json.loads(variable)
        except json.decoder.JSONDecodeError:
            pass

        if isinstance(variable, list):
            random.shuffle(variable)
            variable = variable[0]

        self.not_applicable_variable = variable

    def __str__(self):
        return self.not_applicable_variable


class Template(object):
    def __init__(self, template: str):
        self.template = template

    @staticmethod
    def get_input_variables(template: str):
        pattern = r"\{([a-z_]*?)\}"
        input_variables = re.findall(pattern, template, flags=re.IGNORECASE)
        return input_variables

    def format(self, **kwargs) -> str:
        input_variables = self.get_input_variables(self.template)
        kwargs_ = {
            k: kwargs[k] for k in input_variables
        }
        result = self.template.format(**kwargs_)
        return result


class PromptDataset(object):
    def __init__(self,
                 intent_file: str,
                 template_file: str,
                 data_source: str,
                 split: str = None,
                 ):
        self.intent_file = intent_file
        self.template_file = template_file
        self.data_source = data_source
        self.split = split

        # label to text
        label_to_text_list = self.load_label_to_text_list(intent_file, split=self.split)
        self.label_to_text_list = label_to_text_list

        # templates
        templates: List[Dict[str, Any]] = self.load_templates(template_file)
        self.templates = templates

    @staticmethod
    def load_label_to_text_list(intent_file: str, split: str = None):
        label_to_text_list: Dict[str, List[str]] = defaultdict(list)

        with open(intent_file, "r", encoding="utf-8") as f:
            for row in f:
                row = json.loads(row)
                text = row["text"]
                label = row["label"]
                split2 = row.get("split", None)
                if split is not None and split2 is not None and split2 != split:
                    continue

                label_to_text_list[label].append(text)

        return label_to_text_list

    @staticmethod
    def load_templates(template_file: str) -> List[dict]:
        prompt_template = ""
        response_template = ""
        kwargs = ""

        result: List[dict] = list()
        with open(template_file, "r", encoding="utf-8") as f:
            flag = None
            for row in f:
                row = str(row).strip()

                if row == "--- [define prompt template end] ---":
                    if len(prompt_template) != 0:
                        t = {
                            "prompt_template": prompt_template.strip(),
                            "response_template": response_template.strip(),
                            "kwargs": kwargs.strip(),
                        }
                        result.append(t)

                        prompt_template = ""
                        response_template = ""
                        kwargs = ""

                elif row == "prompt_template:":
                    if not len(prompt_template) == 0:
                        raise AssertionError
                    flag = 0
                elif row == "response_template:":
                    flag = 1
                elif row == "kwargs:":
                    flag = 2
                else:
                    if flag == 0:
                        prompt_template += "{}\n".format(row)
                    elif flag == 1:
                        response_template += "{}\n".format(row)
                    elif flag == 2:
                        kwargs += "{}\n".format(row)
                    else:
                        raise NotImplementedError

        return result

    @staticmethod
    def make_label_to_symbol(labels: List[str]):
        # num, upper alphabet, lower alphabet.
        if len(labels) > 26:
            raise AssertionError("there is only 26 alphabet, not support the labels: {}".format(len(labels)))

        flag = random.random()
        if flag < 0.33:
            # number
            idx_list = list(range(1, len(labels) + 1))
            label_to_symbol = dict(zip(labels, idx_list))
        elif flag < 0.66:
            # lower alphabet
            idx_list = list(range(97, 97+len(labels)))
            idx_list = [chr(idx) for idx in idx_list]
            label_to_symbol = dict(zip(labels, idx_list))
        else:
            # upper alphabet
            idx_list = list(range(65, 65+len(labels)))
            idx_list = [chr(idx) for idx in idx_list]
            label_to_symbol = dict(zip(labels, idx_list))
        return label_to_symbol

    def generator(self):
        version_to_intents_map = DatasetLabels.label_map[self.data_source]
        version_to_intent_description_map = DatasetLabelsDescription.label_description_map[self.data_source]

        num_labels = len(self.label_to_text_list.keys())

        with open(self.intent_file, "r", encoding="utf-8") as f:
            for row in f:
                row = json.loads(row)
                text = row["text"]
                label = row["label"]
                split2 = row.get("split", None)

                if self.split is not None and split2 is not None and split2 != self.split:
                    continue

                # intent version
                intent_version = random.sample(list(version_to_intents_map.keys()), k=1)[0]

                # label to intent
                label_to_intent = dict()
                for k, v in version_to_intents_map[intent_version].items():
                    intent = random.sample(v, k=1)[0]
                    label_to_intent[k] = intent

                # intent description version
                intent_description_version = random.sample(list(version_to_intent_description_map.keys()), k=1)[0]

                # label to description
                label_to_intent_description = dict()
                for k, v in version_to_intent_description_map[intent_description_version].items():
                    intent = random.sample(v, k=1)[0]
                    label_to_intent_description[k] = intent

                this_text = text
                this_label = label
                this_intent = label_to_intent[this_label]

                # template
                template = random.sample(self.templates, k=1)[0]
                prompt_template = template["prompt_template"]
                response_template = template["response_template"]
                kwargs = template["kwargs"]
                kwargs = json.loads(kwargs)

                # common variables
                description = str(CommonVariable(key="description", **kwargs))
                not_applicable_variable = str(NotApplicableVariable(key="not_applicable_variable", **kwargs))
                not_applicable_rate = float(CommonVariable(key="not_applicable_rate", **kwargs))
                max_n_way = int(CommonVariable(key="max_n_way", **kwargs))
                min_n_way = int(CommonVariable(key="min_n_way", **kwargs))
                max_n_shot = int(CommonVariable(key="max_n_shot", **kwargs))
                min_n_shot = int(CommonVariable(key="min_n_shot", **kwargs))

                # n-way
                max_n_way = min([len(self.label_to_text_list), max_n_way])
                min_n_way = max([2, min_n_way])
                min_n_way = min_n_way if min_n_way < max_n_way else max_n_way
                n_way = random.randint(min_n_way, max_n_way)

                # not applicable
                not_applicable = random.random() < not_applicable_rate
                if n_way == num_labels:
                    not_applicable = False

                if not_applicable:
                    candidate_labels = random.sample(self.label_to_text_list.keys(), k=n_way+1)
                    if label in candidate_labels:
                        idx = candidate_labels.index(label)
                        candidate_labels.pop(idx)
                else:
                    candidate_labels = random.sample(self.label_to_text_list.keys(), k=n_way)
                    if label not in candidate_labels:
                        candidate_labels.insert(0, label)
                candidate_labels = candidate_labels[:n_way]
                label_to_symbol = self.make_label_to_symbol(candidate_labels)

                # n-shot
                max_n_shot = min([len(v) for k, v in self.label_to_text_list.items() if k in candidate_labels] + [max_n_shot])
                min_n_shot = max([1, min_n_shot])
                n_shot = random.randint(min_n_shot, max_n_shot)

                # n_way, n_shot
                if len(self.label_to_text_list[this_label]) == n_shot:
                    n_shot -= 1
                if n_shot == 0:
                    not_applicable = True
                    n_way -= 1

                if n_way == 1:
                    continue

                text_label_pairs = list()
                for candidate_label in candidate_labels:
                    if candidate_label == this_label:
                        candidate_text_list1 = random.sample(self.label_to_text_list[candidate_label], k=n_shot+1)
                        candidate_text_list = [candidate_text for candidate_text in candidate_text_list1 if candidate_text != text]
                        if len(candidate_text_list) + 1 < len(candidate_text_list1):
                            raise AssertionError

                        if len(candidate_text_list) > n_shot:
                            candidate_text_list = candidate_text_list[:n_shot]

                        if len(candidate_text_list) != n_shot:
                            raise AssertionError

                    else:
                        candidate_text_list = random.sample(self.label_to_text_list[candidate_label], k=n_shot)

                    if len(candidate_text_list) != n_shot:
                        raise AssertionError

                    for candidate_text in candidate_text_list:
                        text_label_pairs.append((candidate_text, candidate_label))
                random.shuffle(text_label_pairs)

                if len(text_label_pairs) != n_way * n_shot:
                    raise AssertionError

                # variables
                try:
                    intent_description_variable = str(IntentDescriptionVariable(
                        label_to_symbol=label_to_symbol,
                        label_to_intent=label_to_intent,
                        label_to_intent_description=label_to_intent_description,
                        **kwargs))
                except KeyError as e:
                    intent_description_variable = "[missing template]"
                examples_variable = str(ExamplesVariable(text_label_pairs=text_label_pairs,
                                                         label_to_intent=label_to_intent,
                                                         label_to_symbol=label_to_symbol,
                                                         label_to_intent_description=label_to_intent_description,
                                                         **kwargs))
                text_variable = str(TextVariable(this_text, **kwargs))
                intent_variable = str(IntentVariable(label_to_intent[this_label], **kwargs))
                intent_symbol_variable = str(IntentSymbolVariable(label_to_symbol.get(this_label, ""), **kwargs))

                template_kwargs = {
                    "intent_description": intent_description_variable,
                    "examples": examples_variable,
                    "text": text_variable,
                    "intent": intent_variable,
                    "intent_symbol": intent_symbol_variable,
                    "not_applicable": not_applicable_variable,
                }

                prompt_template = Template(template=prompt_template)
                prompt_template = prompt_template.format(**template_kwargs)

                if not_applicable:
                    response_template = not_applicable_variable
                else:
                    response_template = Template(template=response_template)
                    response_template = response_template.format(**template_kwargs)

                result = {
                    "prompt": str(prompt_template),
                    "response": str(response_template),
                    "not_applicable": not_applicable,
                    "intent": this_intent,
                    "intent_version": intent_version,
                    "n_way": n_way,
                    "n_shot": n_shot,
                    "description": description,
                }
                yield result

    def __iter__(self):
        return self.generator()


# dataset

class DatasetLabelsDescription(object):
    label_description_map = {
        "a_intent": {
            "version_0": {
                "Travel-Query": ["对火车，飞机票的查询。对地图的查询，导航等。"],
                "Music-Play": ["对音乐播放器的操作，包括音乐查询，搜索，播放设置等。"],
                "FilmTele-Play": ["对电影节目的操作，包括电影查询，搜索，播放设置等。"],
                "Video-Play": ["对视频的搜索等操作，视频包括：电影电视花絮，街拍，教学视频等等，不是电视节目，也不是电影作品。"],
                "Radio-Listen": ["对广播电台的搜索，播放等操作。"],
                "HomeAppliance-Control": ["对家庭物联网设备的操作，控制。"],
                "Weather-Query": ["对天气的查询。"],
                "Alarm-Update": ["对闹钟，备忘，日程安排等应用的操作。"],
                "Calendar-Query": ["对日历的查询。"],
                "TVProgram-Play": ["对电视节目的查询，搜索，等操作。"],
                "Audio-Play": ["对有声小说，听书应用的操作。"],
                "Other": ["其它任务。"]
            }
        },
        "amazon_massive_intent_en_us": {
            "version_0": {
                "alarm_set": [
                    "alarm set, alarm, reminder, set, create, turn on, etc."
                ],
                "audio_volume_mute": [
                    "such as speaker, AI assistant volume mute."
                ],
                "iot_hue_lightchange": [
                    "iot hue light change."
                ],
                "iot_hue_lightoff": [
                    "iot hue light off."
                ],
                "iot_hue_lightdim": [
                    "iot hue light dim. lower the light."
                ],
                "iot_cleaning": [
                    "activates robot vacuum cleaner."
                ],
                "calendar_query": [
                    "calendar or schedule query, setting, modification, and deletion operations."
                ],
                "play_music": [
                    "music, album search, turn on, resume, stop, put on a playlist, etc."
                ],
                "general_quirky": [
                    "general quirky, such as chat, ask recommend, knowledge question answer, out of domain utternance."
                ],
                "general_greet": [
                    "greeting, such as: hi, hello, hey, what's up, how are you, good morning, and more."
                ],
                "datetime_query": [
                    "query or calculate dates, times, holidays, etc. but this does not include time zone conversion."
                ],
                "datetime_convert": [
                    "time zone conversion problem. such as country to country, c.s.t. to e.s.t."
                ],
                "takeaway_query": [
                    "takeaway query, include: price query, delivery time and is there a takeaway service?"
                ],
                "alarm_remove": [
                    "remove alarm, delete alarm, reset alarm, turn off alarm, take off alarm."
                ],
                "alarm_query": [
                    "alarm query, show all alarm, how many alarm."
                ],
                "news_query": [
                    "news query."
                ],
                "music_likeness": [
                    "when users like and praise music, music types, styles, and genres."
                ],
                "music_query": [
                    "query music or album name, length, singer. and music search, recommend and more."
                ],
                "iot_hue_lightup": [
                    "iot hue light up. brighten lights on, turn up lights, make brighter, more light, etc."
                ],
                "takeaway_order": [
                    "takeaway order, place order, take out order."
                ],
                "weather_query": [
                    "query weather."
                ],
                "music_settings": [
                    "music settings, such as: music repeat, display volume, shuffle music, check playlists."
                ],
                "general_joke": [
                    "ask a joke story, make me happy."
                ],
                "music_dislikeness": [
                    "dislike or complain a music, style, genres or album."
                ],
                "audio_volume_other": [
                    "volume setting, change or adjust volume."
                ],
                "iot_coffee": [
                    "iot coffee, such as: make coffee, turn on coffee pot, order coffee."
                ],
                "audio_volume_up": [
                    "volume up, louder, increase, turn up, adjust up, tune up, loudly, unmute, raise."
                ],
                "iot_wemo_on": [
                    "wemo take on, socket turn on, outlet on, enable plug, power up plug, start the oven, start the laundry."
                ],
                "iot_hue_lighton": [
                    "light turn on, switch on, light began, or when complain dark."
                ],
                "iot_wemo_off": [
                    "turn off plug socket, switch off, power off, disable socket, deactivate, shut down socket."
                ],
                "audio_volume_down": [
                    "speaker volume lower, slow down, turn down, cut down, softer volume, reduce, decrease, set low."
                ],
                "qa_stock": [
                    "query about the stock price, news, rate, taxes."
                ],
                "play_radio": [
                    "play radio, station. switch channel. search."
                ],
                "recommendation_locations": [
                    "When a user searches for a certain type of locations, store, or within a certain distance, in a certain city, etc."
                ],
                "qa_factoid": [
                    "question answer about factoid."
                ],
                "calendar_set": [
                    "calendar set, reminder set, attention that calendar is different from alarm."
                ],
                "play_audiobook": [
                    "instructions about audiobooks, such as: play audio book, resume audio book."
                ],
                "play_podcasts": [
                    "instructions about podcasts, such as: forward, play, locate, skip, search, recommend."
                ],
                "social_query": [
                    "social media query such as tweet, facebook find, search, trending, but not include post."
                ],
                "transport_query": [
                    "transport query, such as: map navigation, route planning, find directions, ticket price, etc."
                ],
                "email_sendemail": [
                    "query about send email, reply email, start a new email."
                ],
                "recommendation_movies": [
                    "query about movies recommendation."
                ],
                "lists_query": [
                    "query about shopping list, display items, etc."
                ],
                "play_game": [
                    "play game."
                ],
                "transport_ticket": [
                    "transport ticket service, such as: book ticket, schedule a journey."
                ],
                "recommendation_events": [
                    "events recommendation."
                ],
                "email_query": [
                    "email query, check, search."
                ],
                "transport_traffic": [
                    "transport traffic condition query."
                ],
                "cooking_query": [
                    "cooking query. this is search a recipe."
                ],
                "qa_definition": [
                    "define question answer, what is it, what's the meaning, how to describe it."
                ],
                "calendar_remove": [
                    "calendar remove, reminder remove, attention that calendar is different from alarm."
                ],
                "lists_remove": [
                    "shopping list remove, take item off, remove item."
                ],
                "cooking_recipe": [
                    "cooking recipe query. this is query detail according a recipe."
                ],
                "email_querycontact": [
                    "query contact info such as email, phone number."
                ],
                "lists_createoradd": [
                    "create or add item to grocery list, shopping list, "
                ],
                "transport_taxi": [
                    "book a taxi, schedule a taxi."
                ],
                "qa_maths": [
                    "math questions and answers."
                ],
                "social_post": [
                    "social media operations such as publishing, post, sent message."
                ],
                "qa_currency": [
                    "question and answer about currency, exchange rate."
                ],
                "email_addcontact": [
                    "add email to contacts."
                ]
            }
        },
        "amazon_massive_intent_zh_cn": {
            "version_0": {
                "报警器": [
                    "闹钟设置，修改，等。"
                ],
                "音量静音": [
                    "调节静音模式，或音箱等应用设备静音。"
                ],
                "物联网色调光变": [
                    "物联网灯光设置，调节颜色。"
                ],
                "物联网色调熄灯": [
                    "物联网关闭指令。"
                ],
                "物联网色调 lightdim": [
                    "物联网灯光亮度调低，调暗。"
                ],
                "物联网清洁": [
                    "物联网清洁指令，例如控制扫地机器人，吸尘器等设备。"
                ],
                "日历查询": [
                    "日历查询，日程安排查询，会议事项提醒等。"
                ],
                "播放音乐": [
                    "音乐播放，音乐搜索。音乐继续播放，循环播放等设置。"
                ],
                "一般古怪": [
                    "一般的闲聊内容。"
                ],
                "一般问候": [
                    "打招呼，问候。"
                ],
                "日期时间查询": [
                    "时间查询，日期查询。"
                ],
                "日期时间转换": [
                    "日期或时间转换，计算，更改时区。"
                ],
                "外卖查询": [
                    "外卖查询，例如：是否有外卖服务，预计交付时间，状态查询，餐食推荐。"
                ],
                "警报解除": [
                    "停止，删除，取消闹钟。"
                ],
                "报警查询": [
                    "闹钟查询，检查。"
                ],
                "新闻查询": [
                    "新闻查询，搜索，推荐。"
                ],
                "音乐相似度": [
                    "表示对音乐或专辑的偏好，喜欢，称赞等，要求保存，收藏音乐。"
                ],
                "音乐查询": [
                    "音乐名称，歌手，风格等各种信息查询，听音识别音乐名称等。"
                ],
                "物联网色调点亮": [
                    "物联灯光调亮，增加亮度。"
                ],
                "外卖订单": [
                    "点餐，外卖下单。"
                ],
                "天气查询": [
                    "天气，温度查询。"
                ],
                "音乐设置": [
                    "音乐设置，例如：随机播放，重播，跳过，切歌等。"
                ],
                "一般笑话": [
                    "笑话查询，讲个笑话。"
                ],
                "不喜欢音乐": [
                    "对音乐，曲风等进行不喜欢评价，或其它负面评价，拉黑音乐。"
                ],
                "音量 其他": [
                    "调节音量，清晰度等设置。"
                ],
                "物联网咖啡": [
                    "物联网咖啡机操作，煮咖啡，定时冲咖啡任何。"
                ],
                "音量调高": [
                    "音量调高，用户抱怨音量太小，听不清楚等。"
                ],
                "iot wemo on": [
                    "打开智能插座，或通过打开插座来启动家电的指令。"
                ],
                "物联网色调莱顿": [
                    "物联网开灯，打开灯光。"
                ],
                "iot wemo 关闭": [
                    "关闭智能插座，或通过关闭插座来关闭家电的指令。"
                ],
                "音量降低": [
                    "音量降低，减小，调低等。"
                ],
                "库存": [
                    "股票查询，收益率，涨幅度，费率，价格等信息查询。"
                ],
                "播放收音机": [
                    "播放收音机，电台，更换频道等。"
                ],
                "推荐地点": [
                    "地图查询，搜索推荐商店，餐馆，设施等。"
                ],
                "质量保证": [
                    "一般事实性问题的问答。"
                ],
                "日历集": [
                    "日历操作，如日历设置，提醒，等。"
                ],
                "播放有声读物": [
                    "播放有声读物，听书APP操作，有声小说等。"
                ],
                "播放播客": [
                    "播客操作，如视频播放，视频搜索，收藏，快进，下一集等等。"
                ],
                "社会查询": [
                    "社交媒体查询，例如聊天记录问答，社交APP问答，搜索，查询，设置等。"
                ],
                "运输查询": [
                    "路线规划，火车查询，飞机查询，订票等。"
                ],
                "发送电子邮件": [
                    "电子邮件操作，如：发送，回复电子邮件，"
                ],
                "推荐电影": [
                    "电影搜索，电影推荐。", "电影搜索，推荐，查询。"
                ],
                "列出查询": [
                    "购物清单查询，问答。"
                ],
                "玩游戏": [
                    "玩游戏。", "启动游戏。"
                ],
                "交通票": [
                    "交通订票，预订火车票，飞机票。"
                ],
                "推荐活动": [
                    "活动查询，如展会，音乐会，美食节等。"
                ],
                "电子邮件查询": [
                    "电子邮件查询。", "邮箱查询，问答等。"
                ],
                "交通运输": [
                    "交通，路况，堵车查询。"
                ],
                "烹饪查询": [
                    "烹饪查询，食谱查询。"
                ],
                "质量保证定义": [
                    "定义问答，如 **是什么。**的定义是什么，怎么描述**，等等。"
                ],
                "日历删除": [
                    "日历删除，日历事件、活动、事项取消", "删除或取消日历中记录的事项。"
                ],
                "列表删除": [
                    "从购物车中删除商品。"
                ],
                "烹饪食谱": [
                    "烹饪食谱查询，查询食物的具体做法。"
                ],
                "电子邮件查询联系方式": [
                    "电子邮箱，通讯录等，查询、问答。"
                ],
                "列出创建或添加": [
                    "清单、待办事项的列表创建或添加"
                ],
                "运输出租车": [
                    "出租车、网约车预约。"
                ],
                "qa数学": [
                    "数学问答。"
                ],
                "社交帖子": [
                    "在社交媒体APP上发布贴子。"
                ],
                "qa 货币": [
                    "汇率查询。"
                ],
                "电子邮件添加联系人": [
                    "电子邮件添加联系人。"
                ]
            }
        },
        "atis_intents": {
            "version_0": {
                "atis_flight": [
                    "flights query, check, or book a flight."
                ],
                "atis_flight_time": [
                    "flight time, schedule query, check, search."
                ],
                "atis_airfare": [
                    "airfare, ticket price, price, cost query."
                ],
                "atis_aircraft": [
                    "aircraft, aircraft type, type of plane check. such as: smallest plane"
                ],
                "atis_ground_service": [
                    "ground transportation services query, such as: limousines or taxi services."
                ],
                "atis_airline": [
                    "airlines query, check."
                ],
                "atis_abbreviation": [
                    "abbreviation question answer.",
                    "abbreviation QA.",
                    "abbreviation check.",
                ],
                "atis_quantity": [
                    "flights, airlines quantity check."
                ],
            }
        },
        "banking77": {
            "version_0": {
                "activate_my_card": [
                    "question about how to activate or verify new card."
                ],
                "age_limit": [
                    "question about how old, minimum age, age limit."
                ],
                "apple_pay_or_google_pay": [
                    "question about is apple pay or google pay available."
                ],
                "atm_support": [
                    "question about supported cash machine ATM."
                ],
                "automatic_top_up": [
                    "question about auto top up."
                ],
                "balance_not_updated_after_bank_transfer": [
                    "balance not updated after bank transfer, how long does it take."
                ],
                "balance_not_updated_after_cheque_or_cash_deposit": [
                    "balance not updated after cheque or cash deposit, how long does it take."
                ],
                "beneficiary_not_allowed": [
                    "question about beneficiary not being allowed, card blocked, can not transfer."
                ],
                "cancel_transfer": [
                    "cancel transfer, reverse my transaction."
                ],
                "card_about_to_expire": [
                    "card about to expire, apply for a new card."
                ],
                "card_acceptance": [
                    "in what shop, businesses, retailers this card is acceptance"
                ],
                "card_arrival": [
                    "get the new card track info, or ask about the time take for card arrive."
                ],
                "card_delivery_estimate": [
                    "when will the card arrive estimate."
                ],
                "card_linking": [
                    "how to link a card to application."
                ],
                "card_not_working": [
                    "card not working, not functioning, broken."
                ],
                "card_payment_fee_charged": [
                    "card payment fee charged."
                ],
                "card_payment_not_recognised": [
                    "card payment not recognised, didn't make, didn't do, unusual payment, it's not mine."
                ],
                "card_payment_wrong_exchange_rate": [
                    "card payment exchange rate is wrong incorrect."
                ],
                "card_swallowed": [
                    "card swallowed by ATM."
                ],
                "cash_withdrawal_charge": [
                    "cash withdrawal charge."
                ],
                "cash_withdrawal_not_recognised": [
                    "cash withdrawal not recognised, unknown, unusual."
                ],
                "change_pin": [
                    "how to change pin, set a new PIN."
                ],
                "compromised_card": [
                    "card compromised, using my card without my permission."
                ],
                "contactless_not_working": [
                    "contactless payments not working."
                ],
                "country_support": [
                    "which country supported to use the card."
                ],
                "declined_card_payment": [
                    "card payment declined, card not working."
                ],
                "declined_cash_withdrawal": [
                    "cash withdrawal declined, cancelled. can not get money from ATM."
                ],
                "declined_transfer": [
                    "transfer declined, unable to transfer."
                ],
                "direct_debit_payment_not_recognised": [
                    "not recognised payment, strange charge on my debit. "
                ],
                "disposable_card_limits": [
                    "disposable card limits."
                ],
                "edit_personal_details": [
                    "edit personal details, change address, name, phone number, etc."
                ],
                "exchange_charge": [
                    "exchange charge, currency exchange fees."
                ],
                "exchange_rate": [
                    "exchange rates."
                ],
                "exchange_via_app": [
                    "How to exchange between different currency."
                ],
                "extra_charge_on_statement": [
                    "extra charge on statement, extra transaction on account."
                ],
                "failed_transfer": [
                    "transfer failed, not completed, transfer not work."
                ],
                "fiat_currency_support": [
                    "fiat currency support, what currency supported."
                ],
                "get_disposable_virtual_card": [
                    "how to get create disposable virtual card."
                ],
                "get_physical_card": [
                    "get physical card, get card PIN."
                ],
                "getting_spare_card": [
                    "get spare card, get additional card, order another card."
                ],
                "getting_virtual_card": [
                    "get virtual card, order a virtual card."
                ],
                "lost_or_stolen_card": [
                    "card lost or stolen, report a stolen card, freeze a card."
                ],
                "lost_or_stolen_phone": [
                    "phone lost or stolen."
                ],
                "order_physical_card": [
                    "order physical card, get a real card."
                ],
                "passcode_forgotten": [
                    "passcode forgotten, password wrong."
                ],
                "pending_card_payment": [
                    "card payment on hold, pending."
                ],
                "pending_cash_withdrawal": [
                    "cash withdrawal pending."
                ],
                "pending_top_up": [
                    "top up not completing, pending."
                ],
                "pending_transfer": [
                    "transfer finish pending."
                ],
                "pin_blocked": [
                    "card is frozen, how to reset the blocked pin."
                ],
                "receiving_money": [
                    "how to receive money, what currency is supported."
                ],
                "Refund_not_showing_up": [
                    "refund not showing up, missing my refund."
                ],
                "request_refund": [
                    "request_refund.", "return.", "refund."
                ],
                "reverted_card_payment?": [
                    "payment cancelled, returned, refunded, card payment came back, card payment not reverted."
                ],
                "supported_cards_and_currencies": [
                    "what currencies or cards is supported to add money."
                ],
                "terminate_account": [
                    "account close, remove, delete, terminate."
                ],
                "top_up_by_bank_transfer_charge": [
                    "top up by bank transfer charge, top up fee of transfer."
                ],
                "top_up_by_card_charge": [
                    "top up by card charge, top up fee of card."
                ],
                "top_up_by_cash_or_cheque": [
                    "how to top up by cash or cheque."
                ],
                "top_up_failed": [
                    "top up failed, denied, top up didn't go through, didn't work."
                ],
                "top_up_limits": [
                    "top up limits, max top up amount, how to increase top up maximum."
                ],
                "top_up_reverted": [
                    "top up reverted, returned, cancelled, failed."
                ],
                "topping_up_by_card": [
                    "faq about topping up by card, top up money is gone, disappeared, can not see my top up."
                ],
                "transaction_charged_twice": [
                    "transaction charged twice, repeat charge, duplicate transaction."
                ],
                "transfer_fee_charged": [
                    "charged extra transfer fee."
                ],
                "transfer_into_account": [
                    "how to transfer into account, how to topping up to my account."
                ],
                "transfer_not_received_by_recipient": [
                    "transfer not received by recipient, transfer didn't arrived, recipient can not see my transaction."
                ],
                "transfer_timing": [
                    "about transfer timing, how long until transfer go through, how many days it take."
                ],
                "unable_to_verify_identity": [
                    "unable to verify identity, identity not be accepted, id not verifying."
                ],
                "verify_my_identity": [
                    "how to verify identity, how to prove ID."
                ],
                "verify_source_of_funds": [
                    "how to check verify source of funds."
                ],
                "verify_top_up": [
                    "verify the top-up card, what's the top-up verification code."
                ],
                "virtual_card_not_working": [
                    "disposable virtual card being denied, not working, non-physical card not work, broken, declined."
                ],
                "visa_or_mastercard": [
                    "looking for a visa or mastercard."
                ],
                "why_verify_identity": [
                    "What is the need to verify my identity, why you need so much details."
                ],
                "wrong_amount_of_cash_received": [
                    "wrong amount of cash received, withdraw, atm transaction is wrong, not full amount received."
                ],
                "wrong_exchange_rate_for_cash_withdrawal": [
                    "wrong exchange rate for cash withdrawal, fee for taking money out is too high."
                ]
            }
        },
        "bi_text11": {
            "version_0": {
                "order": [
                    "query about order, such as: cancel order, change order, check order, etc."
                ],
                "shipping_address": [
                    "query about shipping address, such as: modify delivery address, etc."
                ],
                "cancellation_fee": [
                    "query about cancellation fee, such as: early exit fees, early termination penalty cancellation fee, etc."
                ],
                "invoice": [
                    "query about invoice, such as: check invoice, find invoice, etc."
                ],
                "payment": [
                    "query about payment, such as: checking allowed payment methods, etc."
                ],
                "refund": [
                    "query about refund, such as: checking your refund policy, how long refunds usually take, etc."
                ],
                "feedback": [
                    "query about feedback, such as: file a complaint, file a customer reclamation, file a consumer claim, etc."
                ],
                "contact": [
                    "query about contact, such as: contact custoner service, etc."
                ],
                "account": [
                    "query about account, such as: switch user account profile, edit change account profile, etc."
                ],
                "delivery": [
                    "query about delivery, such as: check delivery options, delivery period, etc."
                ],
                "newsletter": [
                    "query about newsletter, such as: company newsletter sign up subscribe cancel subscription, etc."
                ]
            }
        },
        "bi_text27": {
            "version_0": {
                "cancel_order": [
                    "cancel order, do not want the order."
                ],
                "change_order": [
                    "change order, edit order, add an item to order, remove an item."
                ],
                "change_shipping_address": [
                    "change shipping address, correcting shipping address, edit delivery address."
                ],
                "check_cancellation_fee": [
                    "check cancellation fee, check the early exit fees, cancellation penalty, termination fees."
                ],
                "check_invoice": [
                    "check invoice, find invoice, take a look at the invoices."
                ],
                "check_payment_methods": [
                    "check payment methods, what payment methods are allowed, payment options."
                ],
                "check_refund_policy": [
                    "check refund policy, money back policy, how long refunds take."
                ],
                "complaint": [
                    "complaint, how to file a complaint, filing consumer reclamation, lodge a complaint."
                ],
                "contact_customer_service": [
                    "contact customer service, contact customer assistance, customer service working hours."
                ],
                "contact_human_agent": [
                    "contact human agent, live agent, speak with an operator."
                ],
                "create_account": [
                    "create account, create new user, register account."
                ],
                "delete_account": [
                    "delete account, deleting account, close user account, canceling account, remove account."
                ],
                "delivery_options": [
                    "delivery options, what delivery options available."
                ],
                "delivery_period": [
                    "delivery period, how long the delivery takes."
                ],
                "edit_account": [
                    "edit account, change information on account, edit personal information, edit online profile."
                ],
                "get_invoice": [
                    "get invoice, ask invoices, help to get invoices."
                ],
                "get_refund": [
                    "get refund, get money back, get refunds of money."
                ],
                "newsletter_subscription": [
                    "newsletter subscription, subscribe your company newsletter, cancel newsletter subscription, sign up newsletter."
                ],
                "payment_issue": [
                    "payment issue, report payment issues, solving issues with payment."
                ],
                "place_order": [
                    "place order, buying item, make purchase, making order."
                ],
                "recover_password": [
                    "recover password, forgotten password, recover my access key, reset key, reset pin code, retrieve account pwd."
                ],
                "registration_problems": [
                    "registration problems, registration issue, sign-up error."
                ],
                "review": [
                    "leave review, submit feedback."
                ],
                "set_up_shipping_address": [
                    "set up new, another, different, shipping address, shipping address invalid."
                ],
                "switch_account": [
                    "switch account, use another account, switching to new user account."
                ],
                "track_order": [
                    "track order, check order ETA, ask track id."
                ],
                "track_refund": [
                    "track refund, check refund status, any updates on my refund."
                ]
            },
        },
        "book6": {
            "version_0": {
                "BookRestaurant": ["book restaurant, book table, reserve a seat at restaurant, book brasserie."],
                "GetWeather": ["get weather, show weather forecast."],
                "RateBook": ["rate book, give novel a review, rating textbook."],
                "AddToPlaylist": ["add to playlist, add artist, song to list."],
                "SearchScreeningEvent": ["search screening event, search movie schedules, show movie times."],
                "SearchCreativeWork": ["search creative work, find show, search tv show, show creative book."],
            }
        },
        "carer": {
            "version_0": {
                "sadness": [
                    "express the emotion of sadness, for example: hopeless, burdened, suffering, pathetic, feel low energy, embarrassed, etc."
                ],
                "joy": [
                    "express the emotion of joy, for example: performed well, divine experience, amused, delighted, etc."
                ],
                "love": [
                    "express the emotion of love, for example: feel so blessed, amazing, lovely, loyal, feel tender, passionate, etc."
                ],
                "anger": [
                    "express the emotion of anger, for example: angry, hated, heartless, bitchy, etc."
                ],
                "fear": [
                    "express the emotion of fear, for example: agitated and grumpy, intimidated, threatened, afraid, etc."
                ],
                "surprise": [
                    "express the emotion of surprise, for example: amazed, strange, blown away, alarming, etc."
                ]
            }
        },
        "chatbots": {
            "version_0": {
                "Greeting": [
                    "greeting, such as hello, hi, and more."
                ],
                "GreetingResponse": [
                    "response for greeting, such as self introduction, and more."
                ],
                "CourtesyGreeting": [
                    "greeting which is courtesy."
                ],
                "CourtesyGreetingResponse": [
                    "response for greeting which in is polite."
                ],
                "CurrentHumanQuery": [
                    "current human query, what is my name."
                ],
                "NameQuery": [
                    "name query, what's your name."
                ],
                "RealNameQuery": [
                    "real name query, what's your real name."
                ],
                "TimeQuery": [
                    "time query, what's the time."
                ],
                "Thanks": [
                    "like thank you."
                ],
                "NotTalking2U": [
                    "like, I'm not talking to you."
                ],
                "UnderstandQuery": [
                    "understand query, like, do you understand ?"
                ],
                "Shutup": [
                    "shut up, be quite, stop talking."
                ],
                "Swearing": [
                    "swearing, like, fuck, shit."
                ],
                "GoodBye": [
                    "good bye, see you again, and more."
                ],
                "CourtesyGoodBye": [
                    "good bye which in clude courtesy, like, thank you bye."
                ],
                "WhoAmI": [
                    "who am I, identify me."
                ],
                "Clever": [
                    "praise the robot for being very intelligent and clever"
                ],
                "Gossip": [
                    "query about gossip, chitchat."
                ],
                "Jokes": [
                    "query for a joke."
                ],
                "PodBayDoor": [
                    "query about pod bay door."
                ],
                "PodBayDoorResponse": [
                    "response for query about pod bay door."
                ],
                "SelfAware": [
                    "ask to prove robot self aware."
                ],
            },
        },
        "chinese_news_title": {
            "version_0": {
                "health": [
                    "健康"
                ],
                "joke": [
                    "玩笑"
                ],
                "digi": [
                    "数码"
                ],
                "constellation": [
                    "星座"
                ],
                "movie": [
                    "电影"
                ],
                "star": [
                    "明星"
                ],
                "science": [
                    "科学"
                ],
                "photo": [
                    "照片", "摄影"
                ],
                "pet": [
                    "宠物"
                ],
                "music": [
                    "音乐"
                ],
                "sex": [
                    "两性"
                ],
                "design": [
                    "设计"
                ],
                "baby": [
                    "婴儿", "孩子", "育儿"
                ],
                "education": [
                    "教育", "教学"
                ],
                "drama": [
                    "戏剧", "戏曲"
                ],
                "it": [
                    "IT", "编程", "信息技术"
                ],
                "comic": [
                    "漫画"
                ],
                "manage": [
                    "管理", "经营"
                ],
                "money": [
                    "金钱", "钱财", "财富"
                ],
                "lottery": [
                    "彩票", "抽奖"
                ],
                "sports": [
                    "体育", "运动"
                ],
                "beauty": [
                    "美妆", "美丽"
                ],
                "game": [
                    "游戏"
                ],
                "news": [
                    "消息", "新闻"
                ],
                "house": [
                    "房子", "住宅", "居家"
                ],
                "dress": [
                    "穿搭"
                ],
                "travel": [
                    "旅行", "旅游"
                ],
                "mass_communication": [
                    "大众传播", "大众传媒"
                ],
                "food": [
                    "食物", "食品", "美食"
                ],
                "car": [
                    "汽车"
                ],
                "tv": [
                    "电视", "电视剧"
                ],
                "cultural": [
                    "文化"
                ]
            },
        },
        "cmid_4class": {
            "version_0": {
                "病症": ["病症"],
                "药物": ["药物"],
                "其他": ["其他"],
                "治疗方案": ["治疗方案"],
            }
        },
        "cmid_36class": {
            "version_0": {
                "治疗方法": [
                    "治疗方法"
                ],
                "定义": [
                    "定义"
                ],
                "临床表现(病症表现)": [
                    "临床表现(病症表现)"
                ],
                "适用症": [
                    "适用症"
                ],
                "无法确定": [
                    "无法确定"
                ],
                "禁忌": [
                    "禁忌"
                ],
                "相关病症": [
                    "相关病症"
                ],
                "对比": [
                    "对比"
                ],
                "副作用": [
                    "副作用"
                ],
                "多问": [
                    "多问"
                ],
                "病因": [
                    "病因"
                ],
                "化验/体检方案": [
                    "化验/体检方案"
                ],
                "恢复": [
                    "恢复"
                ],
                "严重性": [
                    "严重性"
                ],
                "治愈率": [
                    "治愈率"
                ],
                "用法": [
                    "用法"
                ],
                "功效": [
                    "功效"
                ],
                "两性": [
                    "两性"
                ],
                "正常指标": [
                    "正常指标"
                ],
                "养生": [
                    "养生"
                ],
                "方法": [
                    "方法"
                ],
                "传染性": [
                    "传染性"
                ],
                "成分": [
                    "成分"
                ],
                "预防": [
                    "预防"
                ],
                "恢复时间": [
                    "恢复时间"
                ],
                "推荐医院": [
                    "推荐医院"
                ],
                "费用": [
                    "费用"
                ],
                "临床意义/检查目的": [
                    "临床意义/检查目的"
                ],
                "设备用法": [
                    "设备用法"
                ],
                "疗效": [
                    "疗效"
                ],
                "作用": [
                    "作用"
                ],
                "价钱": [
                    "价钱"
                ],
                "有效时间": [
                    "有效时间"
                ],
                "整容": [
                    "整容"
                ],
                "所属科室": [
                    "所属科室"
                ],
                "治疗时间": [
                    "治疗时间"
                ],
                "药物禁忌": [
                    "药物禁忌"
                ],
                "病症禁忌": [
                    "病症禁忌"
                ],
                "诱因": [
                    "诱因"
                ],
                "手术时间": [
                    "手术时间"
                ]
            }
        },
        "coig_cqia": {
            "version_0": {
                "成语释义": [
                    "成语释义"
                ],
                "古诗续写": [
                    "古诗续写"
                ],
                "文言文翻译": [
                    "文言文翻译"
                ],
                "命名实体识别": [
                    "命名实体识别"
                ],
                "中文分词": [
                    "中文分词"
                ],
                "情感分类": [
                    "情感分类"
                ],
                "依存句法分析": [
                    "依存句法分析"
                ],
                "论元抽取": [
                    "论元抽取"
                ],
                "事件类型分类": [
                    "事件类型分类"
                ],
                "问题生成": [
                    "问题生成",
                ],
                "SQL": [
                    "SQL生成"
                ],
                "主题分类": [
                    "主题分类"
                ],
                "句子重写": [
                    "句子重写"
                ],
                "特殊格式": [
                    "特殊格式"
                ],
                "语义相关性": [
                    "语义相关性"
                ],
                "古诗词": [
                    "古诗词",
                ],
                "实体判断": [
                    "实体判断"
                ],
                "文本扩写": [
                    "文本扩写",
                ],
                "意图分析": [
                    "意图分析",
                ],
                "有效性判断": [
                    "有效性判断"
                ],
                "情感分析": [
                    "情感分析"
                ],
                "语法纠错": [
                    "语法纠错"
                ],
                "信息检索": [
                    "信息检索"
                ],
                "简繁体转换": [
                    "简繁体转换"
                ],
                "同义词": [
                    "同义词"
                ],
                "信息抽取": [
                    "信息抽取"
                ],
                "语义分析": [
                    "语义分析"
                ],
                "翻译": [
                    "翻译"
                ],
                "实体抽取": [
                    "实体抽取",
                ],
                "因果分析": [
                    "因果分析"
                ],
                "文本生成": [
                    "文本生成",
                ],
                "事件抽取": [
                    "事件抽取"
                ],
                "对联": [
                    "对联"
                ],
                "语义分割": [
                    "语义分割"
                ],
                "关键词生成": [
                    "关键词生成"
                ],
                "论文门类分类": [
                    "论文门类分类"
                ],
                "论文学科分类": [
                    "论文学科分类"
                ],
                "同义替换": [
                    "同义替换"
                ],
                "标题生成": [
                    "标题生成"
                ],
                "对话补全": [
                    "对话补全"
                ],
                "错别字": [
                    "错别字"
                ],
                "医疗诊断": [
                    "医疗诊断"
                ],
                "完形填空": [
                    "完形填空"
                ],
                "原子编辑": [
                    "原子编辑"
                ],
                "图书介绍": [
                    "图书介绍"
                ],
                "作者介绍": [
                    "作者介绍"
                ],
                "故事概要": [
                    "故事概要",
                ],
                "电影推荐": [
                    "电影推荐"
                ],
                "电视剧推荐": [
                    "电视剧推荐"
                ],
                "中学考试": [
                    "中学考试"
                ],
                "法律考研": [
                    "法律考研",
                ],
                "论元角色分类": [
                    "论元角色分类"
                ],
                "代码问答": [
                    "代码问答"
                ],
                "医药问答": [
                    "医药问答",
                ],
            }
        },
        "conv_intent": {
            "version_0": {
                "RateBook": ["rate book, give novel a review, rating textbook."],
                "SearchCreativeWork": ["search creative work, find show, search tv show, show creative book."],
                "BookRestaurant": ["book restaurant, book table, reserve a seat at restaurant, book brasserie."],
                "GetWeather": ["get weather, show weather forecast."],
                "SearchScreeningEvent": ["search screening event, search movie schedules, show movie times."],
                "AddToPlaylist": ["add to playlist, add artist, song to list."],
                "PlayMusic": ["play music, hear sound track, listen youtube, turn on FM."]
            }
        },
        "crosswoz": {
            "version_0": {
                "greet": ["打招呼"],
                "thank": ["感谢"],
                "bye": ["拜拜", "结束"]
            }
        },
        "dmslots": {
            "version_0": {
                "domain.dialog.chat": ["闲聊"],
                "domain.dialog.complain": ["抱怨", "辱骂"],
                "domain.dialog.kgsearch": ["知识库搜索", "查询知识库"],
                "domain.dialog.lbs": ["本地服务"],
                "domain.dialog.manual": ["查询手册"],
                "domain.dialog.other": ["其他对话主题", "其它对话主题"],
                "domain.dialog.status": ["查询状态"],
                "domain.dialog.traffic": ["查询路况", "查询交通状况"],
                "domain.dialog.weather": ["查询天气"],
                "domain.op.app": ["操作App", "App操作"],
                "domain.op.booking": ["预订"],
                "domain.op.control": ["控制"],
                "domain.op.geonavi": ["地理导航", "地图导航"],
                "domain.op.media.fm": ["操作FM", "操作广播"],
                "domain.op.media.music": ["音乐", "操作音乐"],
                "domain.op.media.news": ["新闻", "操作新闻"],
                "domain.op.media.video": ["视频", "操作视频"],
                "domain.op.msgcall": ["打电话", "操作呼叫"],
                "domain.op.other": ["其他操作", "其它操作"]

            },
        },
        "dnd_style_intents": {
            "version_0": {
                "joke": [
                    "joke"
                ],
                "protect": [
                    "protect"
                ],
                "drival": [
                    "drival"
                ],
                "follow": [
                    "follow"
                ],
                "farewell": [
                    "farewell"
                ],
                "join": [
                    "join"
                ],
                "deliver": [
                    "deliver"
                ],
                "attack": [
                    "attack"
                ],
                "threat": [
                    "threat"
                ],
                "greeting": [
                    "greeting"
                ],
                "general": [
                    "general"
                ],
                "exchange": [
                    "exchange"
                ],
                "recieve quest": [
                    "recieve quest"
                ],
                "complete quest": [
                    "complete quest"
                ],
                "message": [
                    "message"
                ],
                "knowledge": [
                    "knowledge"
                ],
                "move": [
                    "move"
                ]
            }
        },
        "emo2019": {
            "version_0": {
                "others": [
                    "others", "other", "other emotion", "other label", "other emotion label"
                ],
                "happy": [
                    "happy"
                ],
                "sad": [
                    "sad"
                ],
                "angry": [
                    "angry"
                ]
            }
        },
        "finance21": {
            "version_0": {
                "commonQ.assist": ["Ask for help"],
                "commonQ.bot": ["Is it a robot"],
                "commonQ.how": ["Question how"],
                "commonQ.just_details": ["Just details"],
                "commonQ.name": ["Ask name"],
                "commonQ.not_giving": ["Not giving"],
                "commonQ.query": ["I have a question"],
                "commonQ.wait": ["Wait a minute"],
                "contact.contact": ["Ask contact info"],
                "faq.aadhaar_missing": ["Aadhaar missing"],
                "faq.address_proof": ["Address proof"],
                "faq.application_process": ["Query process"],
                "faq.apply_register": ["Apply register"],
                "faq.approval_time": ["Approval time"],
                "faq.bad_service": ["Bad service"],
                "faq.banking_option_missing": ["Banking option missing"],
                "faq.biz_category_missing": ["Business category missing"],
                "faq.biz_new": ["Business new"],
                "faq.biz_simpler": ["Business simpler"],
                "faq.borrow_limit": ["Borrow limit"],
                "faq.borrow_use": ["Borrow use", "Borrow usage"]
            },
            "version_1": {
                "commonQ.assist": ["I Need Help"],
                "commonQ.bot": ["Are You A Robot"],
                "commonQ.how": ["Question How"],
                "commonQ.just_details": ["Just Details"],
                "commonQ.name": ["Ask For Name"],
                "commonQ.not_giving": ["I Refuse"],
                "commonQ.query": ["May I Have A Question"],
                "commonQ.wait": ["Wait A Minute"],
                "contact.contact": ["May I Have Your Contact"],
                "faq.aadhaar_missing": ["Aadhaar Missing"],
                "faq.address_proof": ["Address Proof"],
                "faq.application_process": ["Query Process"],
                "faq.apply_register": ["Apply Register"],
                "faq.approval_time": ["Approval Time", "How About The Approval Time"],
                "faq.bad_service": ["Bad Service"],
                "faq.banking_option_missing": ["Banking Option Missing"],
                "faq.biz_category_missing": ["Business Category Missing"],
                "faq.biz_new": ["New Business"],
                "faq.biz_simpler": ["Business Simpler"],
                "faq.borrow_limit": ["How About The Borrow Limit"],
                "faq.borrow_use": ["How About The Borrow Usage"]
            }
        },
        "hwu_64": {
            "version_0": {
                "music likeness": [
                    "User instructions, favorites, saves, and likes a piece of music."
                ],
                "recommendation locations": [
                    "Search and recommend tasks for addresses and locations such as stores and attractions."
                ],
                "general explain": [
                    "Failure to understand, the user did not understand what we said, the user asked us to re-explain."
                ],
                "datetime query": [
                    "Query, calculation or other instructions for date, time zone or time."
                ],
                "cooking recipe": [
                    "Cooking recipe."
                ],
                "calendar query": [
                    "Schedule query, calendar query, for example, meetings, event, and more."
                ],
                "email addcontact": [
                    "Email add contact."
                ],
                "general dontcare": [
                    "General don't care, such as: I'm fine, not matter, whatever, don't care. not mind. "
                ],
                "iot hue lightdim": [
                    "Lower bright, less bright, dim the lights, lower the intensity of light, turn down the light. "
                ],
                "play audiobook": [
                    "Play, resume, and other audiobook-related commands."
                ],
                "play game": [
                    "play game, start game, open game, launch game, and more instructions to start the game."
                ],
                "social post": [
                    "Post on social media like tweets, best buy, facebook, etc. "
                ],
                "recommendation events": [
                    "recommendation events"
                ],
                "email querycontact": [
                    "email querycontact"
                ],
                "transport taxi": [
                    "transport taxi"
                ],
                "play podcasts": [
                    "play podcasts"
                ],
                "weather query": [
                    "weather query"
                ],
                "alarm set": [
                    "alarm set"
                ],
                "audio volume up": [
                    "audio volume up"
                ],
                "email sendemail": [
                    "email sendemail"
                ],
                "music settings": [
                    "music settings"
                ],
                "iot hue lightup": [
                    "iot hue lightup"
                ],
                "iot wemo on": [
                    "iot wemo on"
                ],
                "play music": [
                    "play music"
                ],
                "iot hue lighton": [
                    "iot hue lighton"
                ],
                "transport query": [
                    "transport query"
                ],
                "general repeat": [
                    "general repeat"
                ],
                "qa definition": [
                    "qa definition"
                ],
                "general quirky": [
                    "general quirky"
                ],
                "audio volume down": [
                    "audio volume down"
                ],
                "iot coffee": [
                    "iot coffee"
                ],
                "qa stock": [
                    "qa stock"
                ],
                "takeaway query": [
                    "takeaway query"
                ],
                "general commandstop": [
                    "general commandstop"
                ],
                "transport traffic": [
                    "transport traffic"
                ],
                "lists remove": [
                    "lists remove"
                ],
                "social query": [
                    "social query"
                ],
                "qa factoid": [
                    "qa factoid"
                ],
                "iot wemo off": [
                    "iot wemo off"
                ],
                "calendar set": [
                    "calendar set"
                ],
                "iot hue lightoff": [
                    "iot hue lightoff"
                ],
                "play radio": [
                    "play radio"
                ],
                "takeaway order": [
                    "takeaway order"
                ],
                "qa maths": [
                    "qa maths"
                ],
                "general negate": [
                    "general negate"
                ],
                "alarm remove": [
                    "alarm remove"
                ],
                "general affirm": [
                    "general affirm"
                ],
                "email query": [
                    "email query"
                ],
                "iot cleaning": [
                    "iot cleaning"
                ],
                "transport ticket": [
                    "transport ticket"
                ],
                "general joke": [
                    "general joke"
                ],
                "lists query": [
                    "lists query"
                ],
                "music query": [
                    "music query"
                ],
                "datetime convert": [
                    "datetime convert"
                ],
                "recommendation movies": [
                    "recommendation movies"
                ],
                "general praise": [
                    "general praise"
                ],
                "lists createoradd": [
                    "lists createoradd"
                ],
                "qa currency": [
                    "qa currency"
                ],
                "audio volume mute": [
                    "audio volume mute"
                ],
                "alarm query": [
                    "alarm query"
                ],
                "general confirm": [
                    "general confirm"
                ],
                "calendar remove": [
                    "calendar remove"
                ],
                "iot hue lightchange": [
                    "iot hue lightchange"
                ],
                "news query": [
                    "news query"
                ]
            },
        },
        "ide_intent": {
            "version_0": {
                "delete_class_in_curr_file": [
                    "delete_class_in_curr_file"
                ],
                "close_file": [
                    "close_file"
                ],
                "rename_fun_in_curr_file": [
                    "rename_fun_in_curr_file"
                ],
                "copy_fun_in_another_file": [
                    "copy_fun_in_another_file"
                ],
                "rename_fun_in_another_file": [
                    "rename_fun_in_another_file"
                ],
                "rename_class_in_curr_file": [
                    "rename_class_in_curr_file"
                ],
                "delete_fun_in_another_file": [
                    "delete_fun_in_another_file"
                ],
                "rename_file": [
                    "rename_file"
                ],
                "copy_fun_in_curr_file": [
                    "copy_fun_in_curr_file"
                ],
                "undo": [
                    "undo"
                ],
                "open_file": [
                    "open_file"
                ],
                "delete_class_in_another_file": [
                    "delete_class_in_another_file"
                ],
                "delete_fun_in_curr_file": [
                    "delete_fun_in_curr_file"
                ],
                "import_fun": [
                    "import_fun"
                ],
                "rename_class_in_another_file": [
                    "rename_class_in_another_file"
                ],
                "move_class_in_curr_file": [
                    "move_class_in_curr_file"
                ],
                "import_class": [
                    "import_class"
                ],
                "move_class_in_another_file": [
                    "move_class_in_another_file"
                ],
                "move_fun_in_curr_file": [
                    "move_fun_in_curr_file"
                ],
                "save_file": [
                    "save_file"
                ],
                "delete_file": [
                    "delete_file"
                ],
                "move_fun_in_another_file": [
                    "move_fun_in_another_file"
                ],
                "copy_class_in_curr_file": [
                    "copy_class_in_curr_file"
                ],
                "create_file": [
                    "create_file"
                ],
                "copy_class_in_another_file": [
                    "copy_class_in_another_file"
                ],
                "redo": [
                    "redo"
                ],
                "compile": [
                    "compile"
                ]
            },
            "version_1": {
                "delete_class_in_curr_file": [
                    "delete class in current file",
                ],
                "close_file": [
                    "close file"
                ],
                "rename_fun_in_curr_file": [
                    "rename fun in current file"
                ],
                "copy_fun_in_another_file": [
                    "copy fun in another file"
                ],
                "rename_fun_in_another_file": [
                    "rename fun in another file"
                ],
                "rename_class_in_curr_file": [
                    "rename class in current file"
                ],
                "delete_fun_in_another_file": [
                    "delete fun in another file"
                ],
                "rename_file": [
                    "rename file"
                ],
                "copy_fun_in_curr_file": [
                    "copy fun in current file"
                ],
                "undo": [
                    "undo"
                ],
                "open_file": [
                    "open file"
                ],
                "delete_class_in_another_file": [
                    "delete class in another file"
                ],
                "delete_fun_in_curr_file": [
                    "delete fun in current file"
                ],
                "import_fun": [
                    "import fun"
                ],
                "rename_class_in_another_file": [
                    "rename class in another file"
                ],
                "move_class_in_curr_file": [
                    "move class in current file"
                ],
                "import_class": [
                    "import class"
                ],
                "move_class_in_another_file": [
                    "move class in another file"
                ],
                "move_fun_in_curr_file": [
                    "move fun in current file"
                ],
                "save_file": [
                    "save file"
                ],
                "delete_file": [
                    "delete file"
                ],
                "move_fun_in_another_file": [
                    "move fun in another file"
                ],
                "copy_class_in_curr_file": [
                    "copy class in current file"
                ],
                "create_file": [
                    "create file"
                ],
                "copy_class_in_another_file": [
                    "copy class in another file"
                ],
                "redo": [
                    "redo"
                ],
                "compile": [
                    "compile"
                ]
            },
            "version_2": {
                "delete_class_in_curr_file": [
                    "Delete Class In Current File"
                ],
                "close_file": [
                    "Close File"
                ],
                "rename_fun_in_curr_file": [
                    "Rename Fun In Current File"
                ],
                "copy_fun_in_another_file": [
                    "Copy Fun In Another File"
                ],
                "rename_fun_in_another_file": [
                    "Rename Fun In Another File"
                ],
                "rename_class_in_curr_file": [
                    "Rename Class In Current File"
                ],
                "delete_fun_in_another_file": [
                    "Delete Fun In Another File"
                ],
                "rename_file": [
                    "Rename File"
                ],
                "copy_fun_in_curr_file": [
                    "Copy Fun In Current File"
                ],
                "undo": [
                    "Undo"
                ],
                "open_file": [
                    "Open File"
                ],
                "delete_class_in_another_file": [
                    "Delete Class In Another File"
                ],
                "delete_fun_in_curr_file": [
                    "Delete Fun In Current File"
                ],
                "import_fun": [
                    "Import Fun"
                ],
                "rename_class_in_another_file": [
                    "Rename Class In Another File"
                ],
                "move_class_in_curr_file": [
                    "Move Class In Current File"
                ],
                "import_class": [
                    "Import Class"
                ],
                "move_class_in_another_file": [
                    "Move Class In Another File"
                ],
                "move_fun_in_curr_file": [
                    "Move Fun In Current File"
                ],
                "save_file": [
                    "Save File"
                ],
                "delete_file": [
                    "Delete File"
                ],
                "move_fun_in_another_file": [
                    "Move Fun In Another File"
                ],
                "copy_class_in_curr_file": [
                    "Copy Class In Current File"
                ],
                "create_file": [
                    "Create File"
                ],
                "copy_class_in_another_file": [
                    "Copy Class In Another File"
                ],
                "redo": [
                    "Redo"
                ],
                "compile": [
                    "Compile"
                ]
            },
            "version_3": {
                "delete_class_in_curr_file": [
                    "DeleteClassInCurrentFile"
                ],
                "close_file": [
                    "CloseFile"
                ],
                "rename_fun_in_curr_file": [
                    "RenameFunInCurrentFile"
                ],
                "copy_fun_in_another_file": [
                    "CopyFunInAnotherFile"
                ],
                "rename_fun_in_another_file": [
                    "RenameFunInAnotherFile"
                ],
                "rename_class_in_curr_file": [
                    "RenameClassInCurrentFile"
                ],
                "delete_fun_in_another_file": [
                    "DeleteFunInAnotherFile"
                ],
                "rename_file": [
                    "RenameFile"
                ],
                "copy_fun_in_curr_file": [
                    "CopyFunInCurrentFile"
                ],
                "undo": [
                    "Undo"
                ],
                "open_file": [
                    "OpenFile"
                ],
                "delete_class_in_another_file": [
                    "DeleteClassInAnotherFile"
                ],
                "delete_fun_in_curr_file": [
                    "DeleteFunInCurrentFile"
                ],
                "import_fun": [
                    "ImportFun"
                ],
                "rename_class_in_another_file": [
                    "RenameClassInAnotherFile"
                ],
                "move_class_in_curr_file": [
                    "MoveClassInCurrentFile"
                ],
                "import_class": [
                    "ImportClass"
                ],
                "move_class_in_another_file": [
                    "MoveClassInAnotherFile"
                ],
                "move_fun_in_curr_file": [
                    "MoveFunInCurrentFile"
                ],
                "save_file": [
                    "SaveFile"
                ],
                "delete_file": [
                    "DeleteFile"
                ],
                "move_fun_in_another_file": [
                    "MoveFunInAnotherFile"
                ],
                "copy_class_in_curr_file": [
                    "CopyClassInCurrentFile"
                ],
                "create_file": [
                    "CreateFile"
                ],
                "copy_class_in_another_file": [
                    "CopyClassInAnotherFile"
                ],
                "redo": [
                    "Redo"
                ],
                "compile": [
                    "Compile"
                ]
            },
            "version_4": {
                "delete_class_in_curr_file": [
                    "DELETE_CLASS_IN_CURRENT_FILE"
                ],
                "close_file": [
                    "CLOSE_FILE"
                ],
                "rename_fun_in_curr_file": [
                    "RENAME_FUN_IN_CURRENT_FILE"
                ],
                "copy_fun_in_another_file": [
                    "COPY_FUN_IN_ANOTHER_FILE"
                ],
                "rename_fun_in_another_file": [
                    "RENAME_FUN_IN_ANOTHER_FILE"
                ],
                "rename_class_in_curr_file": [
                    "RENAME_CLASS_IN_CURRENT_FILE"
                ],
                "delete_fun_in_another_file": [
                    "DELETE_FUN_IN_ANOTHER_FILE"
                ],
                "rename_file": [
                    "RENAME_FILE"
                ],
                "copy_fun_in_curr_file": [
                    "COPY_FUN_IN_CURRENT_FILE"
                ],
                "undo": [
                    "UNDO"
                ],
                "open_file": [
                    "OPEN_FILE"
                ],
                "delete_class_in_another_file": [
                    "DELETE_CLASS_IN_ANOTHER_FILE"
                ],
                "delete_fun_in_curr_file": [
                    "DELETE_FUN_IN_CURRENT_FILE"
                ],
                "import_fun": [
                    "IMPORT_FUN"
                ],
                "rename_class_in_another_file": [
                    "RENAME_CLASS_IN_ANOTHER_FILE"
                ],
                "move_class_in_curr_file": [
                    "MOVE_CLASS_IN_CURRENT_FILE"
                ],
                "import_class": [
                    "IMPORT_CLASS"
                ],
                "move_class_in_another_file": [
                    "MOVE_CLASS_IN_ANOTHER_FILE"
                ],
                "move_fun_in_curr_file": [
                    "MOVE_FUN_IN_CURRENT_FILE"
                ],
                "save_file": [
                    "SAVE_FILE"
                ],
                "delete_file": [
                    "DELETE_FILE"
                ],
                "move_fun_in_another_file": [
                    "MOVE_FUN_IN_ANOTHER_FILE"
                ],
                "copy_class_in_curr_file": [
                    "COPY_CLASS_IN_CURRENT_FILE"
                ],
                "create_file": [
                    "CREATE_FILE"
                ],
                "copy_class_in_another_file": [
                    "COPY_CLASS_IN_ANOTHER_FILE"
                ],
                "redo": [
                    "REDO"
                ],
                "compile": [
                    "COMPILE"
                ]
            }
        },
        "intent_classification": {
            "version_0": {
                "AddToPlaylist": [
                    "AddToPlaylist"
                ],
                "BookRestaurant": [
                    "BookRestaurant"
                ],
                "PlayMusic": [
                    "PlayMusic"
                ],
                "GetWeather": [
                    "GetWeather"
                ],
                "Affirmation": [
                    "Affirmation"
                ],
                "SearchCreativeWork": [
                    "SearchCreativeWork"
                ],
                "Cancellation": [
                    "Cancellation"
                ],
                "excitment": [
                    "excitment"
                ],
                "RateBook": [
                    "RateBook"
                ],
                "SearchScreeningEvent": [
                    "SearchScreeningEvent"
                ],
                "Greetings": [
                    "Greetings"
                ],
                "Book Meeting": [
                    "Book Meeting"
                ]
            }
        },
        "jarvis_intent": {
            "version_0": {
                "translate": [
                    "translate"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning_of_life"
                ],
                "fun_fact": [
                    "fun_fact"
                ],
                "time": [
                    "time"
                ],
                "flip_coin": [
                    "flip_coin"
                ],
                "where_are_you_from": [
                    "where_are_you_from"
                ],
                "maybe": [
                    "maybe"
                ],
                "who_made_you": [
                    "who_made_you"
                ],
                "next_song": [
                    "next_song"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel_suggestion"
                ],
                "todo_list_update": [
                    "todo_list_update"
                ],
                "reminder": [
                    "reminder"
                ],
                "no": [
                    "no"
                ],
                "calendar": [
                    "calendar"
                ],
                "calculator": [
                    "calculator"
                ],
                "thank_you": [
                    "thank_you"
                ],
                "roll_dice": [
                    "roll_dice"
                ],
                "reminder_update": [
                    "reminder_update"
                ],
                "todo_list": [
                    "todo_list"
                ],
                "change_volume": [
                    "change_volume"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "what_song": [
                    "what_song"
                ],
                "measurement_conversion": [
                    "measurement_conversion"
                ],
                "current_location": [
                    "current_location"
                ],
                "weather": [
                    "weather"
                ],
                "whisper_mode": [
                    "whisper_mode"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset_settings"
                ],
                "what_is_your_name": [
                    "what_is_your_name"
                ],
                "play_music": [
                    "play_music"
                ],
                "calendar_update": [
                    "calendar_update"
                ],
                "are_you_a_bot": [
                    "are_you_a_bot"
                ],
                "tell_joke": [
                    "tell_joke"
                ],
                "how_old_are_you": [
                    "how_old_are_you"
                ]
            },
            "version_1": {
                "translate": [
                    "translate"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning of life"
                ],
                "fun_fact": [
                    "fun fact"
                ],
                "time": [
                    "time"
                ],
                "flip_coin": [
                    "flip coin"
                ],
                "where_are_you_from": [
                    "where are you from"
                ],
                "maybe": [
                    "maybe"
                ],
                "who_made_you": [
                    "who made you"
                ],
                "next_song": [
                    "next song"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel suggestion"
                ],
                "todo_list_update": [
                    "todo list update"
                ],
                "reminder": [
                    "reminder"
                ],
                "no": [
                    "no"
                ],
                "calendar": [
                    "calendar"
                ],
                "calculator": [
                    "calculator"
                ],
                "thank_you": [
                    "thank you"
                ],
                "roll_dice": [
                    "roll dice"
                ],
                "reminder_update": [
                    "reminder update"
                ],
                "todo_list": [
                    "todo list"
                ],
                "change_volume": [
                    "change volume"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "what_song": [
                    "what song"
                ],
                "measurement_conversion": [
                    "measurement conversion"
                ],
                "current_location": [
                    "current location"
                ],
                "weather": [
                    "weather"
                ],
                "whisper_mode": [
                    "whisper mode"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset settings"
                ],
                "what_is_your_name": [
                    "what is your name"
                ],
                "play_music": [
                    "play music"
                ],
                "calendar_update": [
                    "calendar update"
                ],
                "are_you_a_bot": [
                    "are you a bot"
                ],
                "tell_joke": [
                    "tell joke"
                ],
                "how_old_are_you": [
                    "how old are you"
                ]
            },
            "version_2": {
                "translate": [
                    "Translate"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "Meaning Of Life"
                ],
                "fun_fact": [
                    "Fun Fact"
                ],
                "time": [
                    "Time"
                ],
                "flip_coin": [
                    "Flip Coin"
                ],
                "where_are_you_from": [
                    "Where Are You From"
                ],
                "maybe": [
                    "Maybe"
                ],
                "who_made_you": [
                    "Who Made You"
                ],
                "next_song": [
                    "Next Song"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "Travel Suggestion"
                ],
                "todo_list_update": [
                    "Todo List Update"
                ],
                "reminder": [
                    "Reminder"
                ],
                "no": [
                    "No"
                ],
                "calendar": [
                    "Calendar"
                ],
                "calculator": [
                    "Calculator"
                ],
                "thank_you": [
                    "Thank You"
                ],
                "roll_dice": [
                    "Roll Dice"
                ],
                "reminder_update": [
                    "Reminder Update"
                ],
                "todo_list": [
                    "Todo List"
                ],
                "change_volume": [
                    "Change Volume"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "what_song": [
                    "What Song"
                ],
                "measurement_conversion": [
                    "Measurement Conversion"
                ],
                "current_location": [
                    "Current Location"
                ],
                "weather": [
                    "Weather"
                ],
                "whisper_mode": [
                    "Whisper Mode"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "Reset Settings"
                ],
                "what_is_your_name": [
                    "What Is Your Name"
                ],
                "play_music": [
                    "Play Music"
                ],
                "calendar_update": [
                    "Calendar Update"
                ],
                "are_you_a_bot": [
                    "Are You A Bot"
                ],
                "tell_joke": [
                    "Tell Joke"
                ],
                "how_old_are_you": [
                    "How Old Are You"
                ]
            },
            "version_3": {
                "translate": [
                    "Translate"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "MeaningOfLife"
                ],
                "fun_fact": [
                    "FunFact"
                ],
                "time": [
                    "Time"
                ],
                "flip_coin": [
                    "FlipCoin"
                ],
                "where_are_you_from": [
                    "WhereAreYouFrom"
                ],
                "maybe": [
                    "Maybe"
                ],
                "who_made_you": [
                    "WhoMadeYou"
                ],
                "next_song": [
                    "NextSong"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "TravelSuggestion"
                ],
                "todo_list_update": [
                    "TodoListUpdate"
                ],
                "reminder": [
                    "Reminder"
                ],
                "no": [
                    "No"
                ],
                "calendar": [
                    "Calendar"
                ],
                "calculator": [
                    "Calculator"
                ],
                "thank_you": [
                    "ThankYou"
                ],
                "roll_dice": [
                    "RollDice"
                ],
                "reminder_update": [
                    "ReminderUpdate"
                ],
                "todo_list": [
                    "TodoList"
                ],
                "change_volume": [
                    "ChangeVolume"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "what_song": [
                    "WhatSong"
                ],
                "measurement_conversion": [
                    "MeasurementConversion"
                ],
                "current_location": [
                    "CurrentLocation"
                ],
                "weather": [
                    "Weather"
                ],
                "whisper_mode": [
                    "WhisperMode"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "ResetSettings"
                ],
                "what_is_your_name": [
                    "WhatIsYourName"
                ],
                "play_music": [
                    "PlayMusic"
                ],
                "calendar_update": [
                    "CalendarUpdate"
                ],
                "are_you_a_bot": [
                    "AreYouABot"
                ],
                "tell_joke": [
                    "TellJoke"
                ],
                "how_old_are_you": [
                    "HowOldAreYou"
                ]
            },
            "version_4": {
                "translate": [
                    "TRANSLATE"
                ],
                "timer": [
                    "TIMER"
                ],
                "definition": [
                    "DEFINITION"
                ],
                "meaning_of_life": [
                    "MEANING_OF_LIFE"
                ],
                "fun_fact": [
                    "FUN_FACT"
                ],
                "time": [
                    "TIME"
                ],
                "flip_coin": [
                    "FLIP_COIN"
                ],
                "where_are_you_from": [
                    "WHERE_ARE_YOU_FROM"
                ],
                "maybe": [
                    "MAYBE"
                ],
                "who_made_you": [
                    "WHO_MADE_YOU"
                ],
                "next_song": [
                    "NEXT_SONG"
                ],
                "yes": [
                    "YES"
                ],
                "travel_suggestion": [
                    "TRAVEL_SUGGESTION"
                ],
                "todo_list_update": [
                    "TODO_LIST_UPDATE"
                ],
                "reminder": [
                    "REMINDER"
                ],
                "no": [
                    "NO"
                ],
                "calendar": [
                    "CALENDAR"
                ],
                "calculator": [
                    "CALCULATOR"
                ],
                "thank_you": [
                    "THANK_YOU"
                ],
                "roll_dice": [
                    "ROLL_DICE"
                ],
                "reminder_update": [
                    "REMINDER_UPDATE"
                ],
                "todo_list": [
                    "TODO_LIST"
                ],
                "change_volume": [
                    "CHANGE_VOLUME"
                ],
                "goodbye": [
                    "GOODBYE"
                ],
                "what_song": [
                    "WHAT_SONG"
                ],
                "measurement_conversion": [
                    "MEASUREMENT_CONVERSION"
                ],
                "current_location": [
                    "CURRENT_LOCATION"
                ],
                "weather": [
                    "WEATHER"
                ],
                "whisper_mode": [
                    "WHISPER_MODE"
                ],
                "spelling": [
                    "SPELLING"
                ],
                "greeting": [
                    "GREETING"
                ],
                "reset_settings": [
                    "RESET_SETTINGS"
                ],
                "what_is_your_name": [
                    "WHAT_IS_YOUR_NAME"
                ],
                "play_music": [
                    "PLAY_MUSIC"
                ],
                "calendar_update": [
                    "CALENDAR_UPDATE"
                ],
                "are_you_a_bot": [
                    "ARE_YOU_A_BOT"
                ],
                "tell_joke": [
                    "TELL_JOKE"
                ],
                "how_old_are_you": [
                    "HOW_OLD_ARE_YOU"
                ]
            }
        },
        "mobile_assistant": {"version_0": {
            "others": [
                "others"
            ],
            "places near me": [
                "places near me"
            ],
            "send whatsapp message": [
                "send whatsapp message"
            ],
            "greet and hello hi kind of things, general check in": [
                "greet and hello hi kind of things, general check in"
            ],
            "play games": [
                "play games"
            ],
            "tell me news": [
                "tell me news"
            ],
            "covid cases": [
                "covid cases"
            ],
            "tell me about": [
                "tell me about"
            ],
            "volume control": [
                "volume control"
            ],
            "open website": [
                "open website"
            ],
            "play on youtube": [
                "play on youtube"
            ],
            "tell me joke": [
                "tell me joke"
            ],
            "send email": [
                "send email"
            ],
            "goodbye": [
                "goodbye"
            ],
            "take screenshot": [
                "take screenshot"
            ],
            "download youtube video": [
                "download youtube video"
            ],
            "asking weather": [
                "asking weather"
            ],
            "asking date": [
                "asking date"
            ],
            "asking time": [
                "asking time"
            ],
            "i am bored": [
                "i am bored"
            ],
            "click photo": [
                "click photo"
            ],
            "what can you do": [
                "what can you do"
            ]
        }},
        "mtop_intent": {
            "version_0": {
                "GET_MESSAGE": [
                    "get_message"
                ],
                "GET_WEATHER": [
                    "get_weather"
                ],
                "GET_ALARM": [
                    "get_alarm"
                ],
                "SEND_MESSAGE": [
                    "send_message"
                ],
                "GET_INFO_RECIPES": [
                    "get_info_recipes"
                ],
                "SET_UNAVAILABLE": [
                    "set_unavailable"
                ],
                "DELETE_REMINDER": [
                    "delete_reminder"
                ],
                "GET_STORIES_NEWS": [
                    "get_stories_news"
                ],
                "CREATE_ALARM": [
                    "create_alarm"
                ],
                "GET_REMINDER": [
                    "get_reminder"
                ],
                "CREATE_REMINDER": [
                    "create_reminder"
                ],
                "GET_RECIPES": [
                    "get_recipes"
                ],
                "QUESTION_NEWS": [
                    "question_news"
                ],
                "GET_EVENT": [
                    "get_event"
                ],
                "PLAY_MUSIC": [
                    "play_music"
                ],
                "GET_CALL_TIME": [
                    "get_call_time"
                ],
                "CREATE_CALL": [
                    "create_call"
                ],
                "END_CALL": [
                    "end_call"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "create_playlist_music"
                ],
                "CREATE_TIMER": [
                    "create_timer"
                ],
                "IGNORE_CALL": [
                    "ignore_call"
                ],
                "GET_LIFE_EVENT": [
                    "get_life_event"
                ],
                "GET_INFO_CONTACT": [
                    "get_info_contact"
                ],
                "UPDATE_CALL": [
                    "update_call"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "update_reminder_date_time"
                ],
                "GET_CONTACT": [
                    "get_contact"
                ],
                "GET_TIMER": [
                    "get_timer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "get_reminder_date_time"
                ],
                "DELETE_ALARM": [
                    "delete_alarm"
                ],
                "PAUSE_MUSIC": [
                    "pause_music"
                ],
                "GET_AGE": [
                    "get_age"
                ],
                "GET_SUNRISE": [
                    "get_sunrise"
                ],
                "GET_EMPLOYER": [
                    "get_employer"
                ],
                "GET_EDUCATION_TIME": [
                    "get_education_time"
                ],
                "ANSWER_CALL": [
                    "answer_call"
                ],
                "SET_RSVP_YES": [
                    "set_rsvp_yes"
                ],
                "SNOOZE_ALARM": [
                    "snooze_alarm"
                ],
                "GET_JOB": [
                    "get_job"
                ],
                "UPDATE_REMINDER_TODO": [
                    "update_reminder_todo"
                ],
                "IS_TRUE_RECIPES": [
                    "is_true_recipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "remove_from_playlist_music"
                ],
                "GET_AVAILABILITY": [
                    "get_availability"
                ],
                "GET_CATEGORY_EVENT": [
                    "get_category_event"
                ],
                "PLAY_MEDIA": [
                    "play_media"
                ],
                "ADD_TIME_TIMER": [
                    "add_time_timer"
                ],
                "GET_CALL": [
                    "get_call"
                ],
                "SET_AVAILABLE": [
                    "set_available"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "add_to_playlist_music"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "get_employment_time"
                ],
                "SHARE_EVENT": [
                    "share_event"
                ],
                "PREFER": [
                    "prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "start_shuffle_music"
                ],
                "GET_CALL_CONTACT": [
                    "get_call_contact"
                ],
                "GET_LOCATION": [
                    "get_location"
                ],
                "SILENCE_ALARM": [
                    "silence_alarm"
                ],
                "SWITCH_CALL": [
                    "switch_call"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "get_track_info_music"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "subtract_time_timer"
                ],
                "GET_SUNSET": [
                    "get_sunset"
                ],
                "DELETE_TIMER": [
                    "delete_timer"
                ],
                "UPDATE_TIMER": [
                    "update_timer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "previous_track_music"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "set_default_provider_music"
                ],
                "HOLD_CALL": [
                    "hold_call"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "get_mutual_friends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "skip_track_music"
                ],
                "UPDATE_METHOD_CALL": [
                    "update_method_call"
                ],
                "SET_RSVP_INTERESTED": [
                    "set_rsvp_interested"
                ],
                "QUESTION_MUSIC": [
                    "question_music"
                ],
                "GET_UNDERGRAD": [
                    "get_undergrad"
                ],
                "PAUSE_TIMER": [
                    "pause_timer"
                ],
                "UPDATE_ALARM": [
                    "update_alarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "get_reminder_location"
                ],
                "GET_ATTENDEE_EVENT": [
                    "get_attendee_event"
                ],
                "LIKE_MUSIC": [
                    "like_music"
                ],
                "RESTART_TIMER": [
                    "restart_timer"
                ],
                "RESUME_TIMER": [
                    "resume_timer"
                ],
                "MERGE_CALL": [
                    "merge_call"
                ],
                "GET_MESSAGE_CONTACT": [
                    "get_message_contact"
                ],
                "REPLAY_MUSIC": [
                    "replay_music"
                ],
                "LOOP_MUSIC": [
                    "loop_music"
                ],
                "GET_REMINDER_AMOUNT": [
                    "get_reminder_amount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "get_date_time_event"
                ],
                "STOP_MUSIC": [
                    "stop_music"
                ],
                "GET_DETAILS_NEWS": [
                    "get_details_news"
                ],
                "GET_EDUCATION_DEGREE": [
                    "get_education_degree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "set_default_provider_calling"
                ],
                "GET_MAJOR": [
                    "get_major"
                ],
                "UNLOOP_MUSIC": [
                    "unloop_music"
                ],
                "GET_CONTACT_METHOD": [
                    "get_contact_method"
                ],
                "SET_RSVP_NO": [
                    "set_rsvp_no"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "update_reminder_location"
                ],
                "RESUME_CALL": [
                    "resume_call"
                ],
                "CANCEL_MESSAGE": [
                    "cancel_message"
                ],
                "RESUME_MUSIC": [
                    "resume_music"
                ],
                "UPDATE_REMINDER": [
                    "update_reminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "delete_playlist_music"
                ],
                "REWIND_MUSIC": [
                    "rewind_music"
                ],
                "REPEAT_ALL_MUSIC": [
                    "repeat_all_music"
                ],
                "FAST_FORWARD_MUSIC": [
                    "fast_forward_music"
                ],
                "DISLIKE_MUSIC": [
                    "dislike_music"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "get_life_event_time"
                ],
                "DISPREFER": [
                    "disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "repeat_all_off_music"
                ],
                "HELP_REMINDER": [
                    "help_reminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "get_lyrics_music"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "stop_shuffle_music"
                ],
                "GET_AIRQUALITY": [
                    "get_airquality"
                ],
                "GET_LANGUAGE": [
                    "get_language"
                ],
                "FOLLOW_MUSIC": [
                    "follow_music"
                ],
                "GET_GENDER": [
                    "get_gender"
                ],
                "CANCEL_CALL": [
                    "cancel_call"
                ],
                "GET_GROUP": [
                    "get_group"
                ]
            },
            "version_1": {
                "GET_MESSAGE": [
                    "get message"
                ],
                "GET_WEATHER": [
                    "get weather"
                ],
                "GET_ALARM": [
                    "get alarm"
                ],
                "SEND_MESSAGE": [
                    "send message"
                ],
                "GET_INFO_RECIPES": [
                    "get info recipes"
                ],
                "SET_UNAVAILABLE": [
                    "set unavailable"
                ],
                "DELETE_REMINDER": [
                    "delete reminder"
                ],
                "GET_STORIES_NEWS": [
                    "get stories news"
                ],
                "CREATE_ALARM": [
                    "create alarm"
                ],
                "GET_REMINDER": [
                    "get reminder"
                ],
                "CREATE_REMINDER": [
                    "create reminder"
                ],
                "GET_RECIPES": [
                    "get recipes"
                ],
                "QUESTION_NEWS": [
                    "question news"
                ],
                "GET_EVENT": [
                    "get event"
                ],
                "PLAY_MUSIC": [
                    "play music"
                ],
                "GET_CALL_TIME": [
                    "get call time"
                ],
                "CREATE_CALL": [
                    "create call"
                ],
                "END_CALL": [
                    "end call"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "create playlist music"
                ],
                "CREATE_TIMER": [
                    "create timer"
                ],
                "IGNORE_CALL": [
                    "ignore call"
                ],
                "GET_LIFE_EVENT": [
                    "get life event"
                ],
                "GET_INFO_CONTACT": [
                    "get info contact"
                ],
                "UPDATE_CALL": [
                    "update call"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "update reminder date time"
                ],
                "GET_CONTACT": [
                    "get contact"
                ],
                "GET_TIMER": [
                    "get timer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "get reminder date time"
                ],
                "DELETE_ALARM": [
                    "delete alarm"
                ],
                "PAUSE_MUSIC": [
                    "pause music"
                ],
                "GET_AGE": [
                    "get age"
                ],
                "GET_SUNRISE": [
                    "get sunrise"
                ],
                "GET_EMPLOYER": [
                    "get employer"
                ],
                "GET_EDUCATION_TIME": [
                    "get education time"
                ],
                "ANSWER_CALL": [
                    "answer call"
                ],
                "SET_RSVP_YES": [
                    "set rsvp yes"
                ],
                "SNOOZE_ALARM": [
                    "snooze alarm"
                ],
                "GET_JOB": [
                    "get job"
                ],
                "UPDATE_REMINDER_TODO": [
                    "update reminder todo"
                ],
                "IS_TRUE_RECIPES": [
                    "is true recipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "remove from playlist music"
                ],
                "GET_AVAILABILITY": [
                    "get availability"
                ],
                "GET_CATEGORY_EVENT": [
                    "get category event"
                ],
                "PLAY_MEDIA": [
                    "play media"
                ],
                "ADD_TIME_TIMER": [
                    "add time timer"
                ],
                "GET_CALL": [
                    "get call"
                ],
                "SET_AVAILABLE": [
                    "set available"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "add to playlist music"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "get employment time"
                ],
                "SHARE_EVENT": [
                    "share event"
                ],
                "PREFER": [
                    "prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "start shuffle music"
                ],
                "GET_CALL_CONTACT": [
                    "get call contact"
                ],
                "GET_LOCATION": [
                    "get location"
                ],
                "SILENCE_ALARM": [
                    "silence alarm"
                ],
                "SWITCH_CALL": [
                    "switch call"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "get track info music"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "subtract time timer"
                ],
                "GET_SUNSET": [
                    "get sunset"
                ],
                "DELETE_TIMER": [
                    "delete timer"
                ],
                "UPDATE_TIMER": [
                    "update timer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "previous track music"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "set default provider music"
                ],
                "HOLD_CALL": [
                    "hold call"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "get mutual friends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "skip track music"
                ],
                "UPDATE_METHOD_CALL": [
                    "update method call"
                ],
                "SET_RSVP_INTERESTED": [
                    "set rsvp interested"
                ],
                "QUESTION_MUSIC": [
                    "question music"
                ],
                "GET_UNDERGRAD": [
                    "get undergrad"
                ],
                "PAUSE_TIMER": [
                    "pause timer"
                ],
                "UPDATE_ALARM": [
                    "update alarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "get reminder location"
                ],
                "GET_ATTENDEE_EVENT": [
                    "get attendee event"
                ],
                "LIKE_MUSIC": [
                    "like music"
                ],
                "RESTART_TIMER": [
                    "restart timer"
                ],
                "RESUME_TIMER": [
                    "resume timer"
                ],
                "MERGE_CALL": [
                    "merge call"
                ],
                "GET_MESSAGE_CONTACT": [
                    "get message contact"
                ],
                "REPLAY_MUSIC": [
                    "replay music"
                ],
                "LOOP_MUSIC": [
                    "loop music"
                ],
                "GET_REMINDER_AMOUNT": [
                    "get reminder amount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "get date time event"
                ],
                "STOP_MUSIC": [
                    "stop music"
                ],
                "GET_DETAILS_NEWS": [
                    "get details news"
                ],
                "GET_EDUCATION_DEGREE": [
                    "get education degree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "set default provider calling"
                ],
                "GET_MAJOR": [
                    "get major"
                ],
                "UNLOOP_MUSIC": [
                    "unloop music"
                ],
                "GET_CONTACT_METHOD": [
                    "get contact method"
                ],
                "SET_RSVP_NO": [
                    "set rsvp no"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "update reminder location"
                ],
                "RESUME_CALL": [
                    "resume call"
                ],
                "CANCEL_MESSAGE": [
                    "cancel message"
                ],
                "RESUME_MUSIC": [
                    "resume music"
                ],
                "UPDATE_REMINDER": [
                    "update reminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "delete playlist music"
                ],
                "REWIND_MUSIC": [
                    "rewind music"
                ],
                "REPEAT_ALL_MUSIC": [
                    "repeat all music"
                ],
                "FAST_FORWARD_MUSIC": [
                    "fast forward music"
                ],
                "DISLIKE_MUSIC": [
                    "dislike music"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "get life event time"
                ],
                "DISPREFER": [
                    "disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "repeat all off music"
                ],
                "HELP_REMINDER": [
                    "help reminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "get lyrics music"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "stop shuffle music"
                ],
                "GET_AIRQUALITY": [
                    "get airquality"
                ],
                "GET_LANGUAGE": [
                    "get language"
                ],
                "FOLLOW_MUSIC": [
                    "follow music"
                ],
                "GET_GENDER": [
                    "get gender"
                ],
                "CANCEL_CALL": [
                    "cancel call"
                ],
                "GET_GROUP": [
                    "get group"
                ]
            },
            "version_2": {
                "GET_MESSAGE": [
                    "Get Message"
                ],
                "GET_WEATHER": [
                    "Get Weather"
                ],
                "GET_ALARM": [
                    "Get Alarm"
                ],
                "SEND_MESSAGE": [
                    "Send Message"
                ],
                "GET_INFO_RECIPES": [
                    "Get Info Recipes"
                ],
                "SET_UNAVAILABLE": [
                    "Set Unavailable"
                ],
                "DELETE_REMINDER": [
                    "Delete Reminder"
                ],
                "GET_STORIES_NEWS": [
                    "Get Stories News"
                ],
                "CREATE_ALARM": [
                    "Create Alarm"
                ],
                "GET_REMINDER": [
                    "Get Reminder"
                ],
                "CREATE_REMINDER": [
                    "Create Reminder"
                ],
                "GET_RECIPES": [
                    "Get Recipes"
                ],
                "QUESTION_NEWS": [
                    "Question News"
                ],
                "GET_EVENT": [
                    "Get Event"
                ],
                "PLAY_MUSIC": [
                    "Play Music"
                ],
                "GET_CALL_TIME": [
                    "Get Call Time"
                ],
                "CREATE_CALL": [
                    "Create Call"
                ],
                "END_CALL": [
                    "End Call"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "Create Playlist Music"
                ],
                "CREATE_TIMER": [
                    "Create Timer"
                ],
                "IGNORE_CALL": [
                    "Ignore Call"
                ],
                "GET_LIFE_EVENT": [
                    "Get Life Event"
                ],
                "GET_INFO_CONTACT": [
                    "Get Info Contact"
                ],
                "UPDATE_CALL": [
                    "Update Call"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "Update Reminder Date Time"
                ],
                "GET_CONTACT": [
                    "Get Contact"
                ],
                "GET_TIMER": [
                    "Get Timer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "Get Reminder Date Time"
                ],
                "DELETE_ALARM": [
                    "Delete Alarm"
                ],
                "PAUSE_MUSIC": [
                    "Pause Music"
                ],
                "GET_AGE": [
                    "Get Age"
                ],
                "GET_SUNRISE": [
                    "Get Sunrise"
                ],
                "GET_EMPLOYER": [
                    "Get Employer"
                ],
                "GET_EDUCATION_TIME": [
                    "Get Education Time"
                ],
                "ANSWER_CALL": [
                    "Answer Call"
                ],
                "SET_RSVP_YES": [
                    "Set Rsvp Yes"
                ],
                "SNOOZE_ALARM": [
                    "Snooze Alarm"
                ],
                "GET_JOB": [
                    "Get Job"
                ],
                "UPDATE_REMINDER_TODO": [
                    "Update Reminder Todo"
                ],
                "IS_TRUE_RECIPES": [
                    "Is True Recipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "Remove From Playlist Music"
                ],
                "GET_AVAILABILITY": [
                    "Get Availability"
                ],
                "GET_CATEGORY_EVENT": [
                    "Get Category Event"
                ],
                "PLAY_MEDIA": [
                    "Play Media"
                ],
                "ADD_TIME_TIMER": [
                    "Add Time Timer"
                ],
                "GET_CALL": [
                    "Get Call"
                ],
                "SET_AVAILABLE": [
                    "Set Available"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "Add To Playlist Music"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "Get Employment Time"
                ],
                "SHARE_EVENT": [
                    "Share Event"
                ],
                "PREFER": [
                    "Prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "Start Shuffle Music"
                ],
                "GET_CALL_CONTACT": [
                    "Get Call Contact"
                ],
                "GET_LOCATION": [
                    "Get Location"
                ],
                "SILENCE_ALARM": [
                    "Silence Alarm"
                ],
                "SWITCH_CALL": [
                    "Switch Call"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "Get Track Info Music"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "Subtract Time Timer"
                ],
                "GET_SUNSET": [
                    "Get Sunset"
                ],
                "DELETE_TIMER": [
                    "Delete Timer"
                ],
                "UPDATE_TIMER": [
                    "Update Timer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "Previous Track Music"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "Set Default Provider Music"
                ],
                "HOLD_CALL": [
                    "Hold Call"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "Get Mutual Friends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "Skip Track Music"
                ],
                "UPDATE_METHOD_CALL": [
                    "Update Method Call"
                ],
                "SET_RSVP_INTERESTED": [
                    "Set Rsvp Interested"
                ],
                "QUESTION_MUSIC": [
                    "Question Music"
                ],
                "GET_UNDERGRAD": [
                    "Get Undergrad"
                ],
                "PAUSE_TIMER": [
                    "Pause Timer"
                ],
                "UPDATE_ALARM": [
                    "Update Alarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "Get Reminder Location"
                ],
                "GET_ATTENDEE_EVENT": [
                    "Get Attendee Event"
                ],
                "LIKE_MUSIC": [
                    "Like Music"
                ],
                "RESTART_TIMER": [
                    "Restart Timer"
                ],
                "RESUME_TIMER": [
                    "Resume Timer"
                ],
                "MERGE_CALL": [
                    "Merge Call"
                ],
                "GET_MESSAGE_CONTACT": [
                    "Get Message Contact"
                ],
                "REPLAY_MUSIC": [
                    "Replay Music"
                ],
                "LOOP_MUSIC": [
                    "Loop Music"
                ],
                "GET_REMINDER_AMOUNT": [
                    "Get Reminder Amount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "Get Date Time Event"
                ],
                "STOP_MUSIC": [
                    "Stop Music"
                ],
                "GET_DETAILS_NEWS": [
                    "Get Details News"
                ],
                "GET_EDUCATION_DEGREE": [
                    "Get Education Degree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "Set Default Provider Calling"
                ],
                "GET_MAJOR": [
                    "Get Major"
                ],
                "UNLOOP_MUSIC": [
                    "Unloop Music"
                ],
                "GET_CONTACT_METHOD": [
                    "Get Contact Method"
                ],
                "SET_RSVP_NO": [
                    "Set Rsvp No"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "Update Reminder Location"
                ],
                "RESUME_CALL": [
                    "Resume Call"
                ],
                "CANCEL_MESSAGE": [
                    "Cancel Message"
                ],
                "RESUME_MUSIC": [
                    "Resume Music"
                ],
                "UPDATE_REMINDER": [
                    "Update Reminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "Delete Playlist Music"
                ],
                "REWIND_MUSIC": [
                    "Rewind Music"
                ],
                "REPEAT_ALL_MUSIC": [
                    "Repeat All Music"
                ],
                "FAST_FORWARD_MUSIC": [
                    "Fast Forward Music"
                ],
                "DISLIKE_MUSIC": [
                    "Dislike Music"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "Get Life Event Time"
                ],
                "DISPREFER": [
                    "Disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "Repeat All Off Music"
                ],
                "HELP_REMINDER": [
                    "Help Reminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "Get Lyrics Music"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "Stop Shuffle Music"
                ],
                "GET_AIRQUALITY": [
                    "Get Airquality"
                ],
                "GET_LANGUAGE": [
                    "Get Language"
                ],
                "FOLLOW_MUSIC": [
                    "Follow Music"
                ],
                "GET_GENDER": [
                    "Get Gender"
                ],
                "CANCEL_CALL": [
                    "Cancel Call"
                ],
                "GET_GROUP": [
                    "Get Group"
                ]
            },
            "version_3": {
                "GET_MESSAGE": [
                    "GetMessage"
                ],
                "GET_WEATHER": [
                    "GetWeather"
                ],
                "GET_ALARM": [
                    "GetAlarm"
                ],
                "SEND_MESSAGE": [
                    "SendMessage"
                ],
                "GET_INFO_RECIPES": [
                    "GetInfoRecipes"
                ],
                "SET_UNAVAILABLE": [
                    "SetUnavailable"
                ],
                "DELETE_REMINDER": [
                    "DeleteReminder"
                ],
                "GET_STORIES_NEWS": [
                    "GetStoriesNews"
                ],
                "CREATE_ALARM": [
                    "CreateAlarm"
                ],
                "GET_REMINDER": [
                    "GetReminder"
                ],
                "CREATE_REMINDER": [
                    "CreateReminder"
                ],
                "GET_RECIPES": [
                    "GetRecipes"
                ],
                "QUESTION_NEWS": [
                    "QuestionNews"
                ],
                "GET_EVENT": [
                    "GetEvent"
                ],
                "PLAY_MUSIC": [
                    "PlayMusic"
                ],
                "GET_CALL_TIME": [
                    "GetCallTime"
                ],
                "CREATE_CALL": [
                    "CreateCall"
                ],
                "END_CALL": [
                    "EndCall"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "CreatePlaylistMusic"
                ],
                "CREATE_TIMER": [
                    "CreateTimer"
                ],
                "IGNORE_CALL": [
                    "IgnoreCall"
                ],
                "GET_LIFE_EVENT": [
                    "GetLifeEvent"
                ],
                "GET_INFO_CONTACT": [
                    "GetInfoContact"
                ],
                "UPDATE_CALL": [
                    "UpdateCall"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "UpdateReminderDateTime"
                ],
                "GET_CONTACT": [
                    "GetContact"
                ],
                "GET_TIMER": [
                    "GetTimer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "GetReminderDateTime"
                ],
                "DELETE_ALARM": [
                    "DeleteAlarm"
                ],
                "PAUSE_MUSIC": [
                    "PauseMusic"
                ],
                "GET_AGE": [
                    "GetAge"
                ],
                "GET_SUNRISE": [
                    "GetSunrise"
                ],
                "GET_EMPLOYER": [
                    "GetEmployer"
                ],
                "GET_EDUCATION_TIME": [
                    "GetEducationTime"
                ],
                "ANSWER_CALL": [
                    "AnswerCall"
                ],
                "SET_RSVP_YES": [
                    "SetRsvpYes"
                ],
                "SNOOZE_ALARM": [
                    "SnoozeAlarm"
                ],
                "GET_JOB": [
                    "GetJob"
                ],
                "UPDATE_REMINDER_TODO": [
                    "UpdateReminderTodo"
                ],
                "IS_TRUE_RECIPES": [
                    "IsTrueRecipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "RemoveFromPlaylistMusic"
                ],
                "GET_AVAILABILITY": [
                    "GetAvailability"
                ],
                "GET_CATEGORY_EVENT": [
                    "GetCategoryEvent"
                ],
                "PLAY_MEDIA": [
                    "PlayMedia"
                ],
                "ADD_TIME_TIMER": [
                    "AddTimeTimer"
                ],
                "GET_CALL": [
                    "GetCall"
                ],
                "SET_AVAILABLE": [
                    "SetAvailable"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "AddToPlaylistMusic"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "GetEmploymentTime"
                ],
                "SHARE_EVENT": [
                    "ShareEvent"
                ],
                "PREFER": [
                    "Prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "StartShuffleMusic"
                ],
                "GET_CALL_CONTACT": [
                    "GetCallContact"
                ],
                "GET_LOCATION": [
                    "GetLocation"
                ],
                "SILENCE_ALARM": [
                    "SilenceAlarm"
                ],
                "SWITCH_CALL": [
                    "SwitchCall"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "GetTrackInfoMusic"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "SubtractTimeTimer"
                ],
                "GET_SUNSET": [
                    "GetSunset"
                ],
                "DELETE_TIMER": [
                    "DeleteTimer"
                ],
                "UPDATE_TIMER": [
                    "UpdateTimer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "PreviousTrackMusic"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "SetDefaultProviderMusic"
                ],
                "HOLD_CALL": [
                    "HoldCall"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "GetMutualFriends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "SkipTrackMusic"
                ],
                "UPDATE_METHOD_CALL": [
                    "UpdateMethodCall"
                ],
                "SET_RSVP_INTERESTED": [
                    "SetRsvpInterested"
                ],
                "QUESTION_MUSIC": [
                    "QuestionMusic"
                ],
                "GET_UNDERGRAD": [
                    "GetUndergrad"
                ],
                "PAUSE_TIMER": [
                    "PauseTimer"
                ],
                "UPDATE_ALARM": [
                    "UpdateAlarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "GetReminderLocation"
                ],
                "GET_ATTENDEE_EVENT": [
                    "GetAttendeeEvent"
                ],
                "LIKE_MUSIC": [
                    "LikeMusic"
                ],
                "RESTART_TIMER": [
                    "RestartTimer"
                ],
                "RESUME_TIMER": [
                    "ResumeTimer"
                ],
                "MERGE_CALL": [
                    "MergeCall"
                ],
                "GET_MESSAGE_CONTACT": [
                    "GetMessageContact"
                ],
                "REPLAY_MUSIC": [
                    "ReplayMusic"
                ],
                "LOOP_MUSIC": [
                    "LoopMusic"
                ],
                "GET_REMINDER_AMOUNT": [
                    "GetReminderAmount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "GetDateTimeEvent"
                ],
                "STOP_MUSIC": [
                    "StopMusic"
                ],
                "GET_DETAILS_NEWS": [
                    "GetDetailsNews"
                ],
                "GET_EDUCATION_DEGREE": [
                    "GetEducationDegree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "SetDefaultProviderCalling"
                ],
                "GET_MAJOR": [
                    "GetMajor"
                ],
                "UNLOOP_MUSIC": [
                    "UnloopMusic"
                ],
                "GET_CONTACT_METHOD": [
                    "GetContactMethod"
                ],
                "SET_RSVP_NO": [
                    "SetRsvpNo"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "UpdateReminderLocation"
                ],
                "RESUME_CALL": [
                    "ResumeCall"
                ],
                "CANCEL_MESSAGE": [
                    "CancelMessage"
                ],
                "RESUME_MUSIC": [
                    "ResumeMusic"
                ],
                "UPDATE_REMINDER": [
                    "UpdateReminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "DeletePlaylistMusic"
                ],
                "REWIND_MUSIC": [
                    "RewindMusic"
                ],
                "REPEAT_ALL_MUSIC": [
                    "RepeatAllMusic"
                ],
                "FAST_FORWARD_MUSIC": [
                    "FastForwardMusic"
                ],
                "DISLIKE_MUSIC": [
                    "DislikeMusic"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "GetLifeEventTime"
                ],
                "DISPREFER": [
                    "Disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "RepeatAllOffMusic"
                ],
                "HELP_REMINDER": [
                    "HelpReminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "GetLyricsMusic"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "StopShuffleMusic"
                ],
                "GET_AIRQUALITY": [
                    "GetAirquality"
                ],
                "GET_LANGUAGE": [
                    "GetLanguage"
                ],
                "FOLLOW_MUSIC": [
                    "FollowMusic"
                ],
                "GET_GENDER": [
                    "GetGender"
                ],
                "CANCEL_CALL": [
                    "CancelCall"
                ],
                "GET_GROUP": [
                    "GetGroup"
                ]
            },
            "version_4": {
                "GET_MESSAGE": [
                    "GET_MESSAGE"
                ],
                "GET_WEATHER": [
                    "GET_WEATHER"
                ],
                "GET_ALARM": [
                    "GET_ALARM"
                ],
                "SEND_MESSAGE": [
                    "SEND_MESSAGE"
                ],
                "GET_INFO_RECIPES": [
                    "GET_INFO_RECIPES"
                ],
                "SET_UNAVAILABLE": [
                    "SET_UNAVAILABLE"
                ],
                "DELETE_REMINDER": [
                    "DELETE_REMINDER"
                ],
                "GET_STORIES_NEWS": [
                    "GET_STORIES_NEWS"
                ],
                "CREATE_ALARM": [
                    "CREATE_ALARM"
                ],
                "GET_REMINDER": [
                    "GET_REMINDER"
                ],
                "CREATE_REMINDER": [
                    "CREATE_REMINDER"
                ],
                "GET_RECIPES": [
                    "GET_RECIPES"
                ],
                "QUESTION_NEWS": [
                    "QUESTION_NEWS"
                ],
                "GET_EVENT": [
                    "GET_EVENT"
                ],
                "PLAY_MUSIC": [
                    "PLAY_MUSIC"
                ],
                "GET_CALL_TIME": [
                    "GET_CALL_TIME"
                ],
                "CREATE_CALL": [
                    "CREATE_CALL"
                ],
                "END_CALL": [
                    "END_CALL"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "CREATE_PLAYLIST_MUSIC"
                ],
                "CREATE_TIMER": [
                    "CREATE_TIMER"
                ],
                "IGNORE_CALL": [
                    "IGNORE_CALL"
                ],
                "GET_LIFE_EVENT": [
                    "GET_LIFE_EVENT"
                ],
                "GET_INFO_CONTACT": [
                    "GET_INFO_CONTACT"
                ],
                "UPDATE_CALL": [
                    "UPDATE_CALL"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "UPDATE_REMINDER_DATE_TIME"
                ],
                "GET_CONTACT": [
                    "GET_CONTACT"
                ],
                "GET_TIMER": [
                    "GET_TIMER"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "GET_REMINDER_DATE_TIME"
                ],
                "DELETE_ALARM": [
                    "DELETE_ALARM"
                ],
                "PAUSE_MUSIC": [
                    "PAUSE_MUSIC"
                ],
                "GET_AGE": [
                    "GET_AGE"
                ],
                "GET_SUNRISE": [
                    "GET_SUNRISE"
                ],
                "GET_EMPLOYER": [
                    "GET_EMPLOYER"
                ],
                "GET_EDUCATION_TIME": [
                    "GET_EDUCATION_TIME"
                ],
                "ANSWER_CALL": [
                    "ANSWER_CALL"
                ],
                "SET_RSVP_YES": [
                    "SET_RSVP_YES"
                ],
                "SNOOZE_ALARM": [
                    "SNOOZE_ALARM"
                ],
                "GET_JOB": [
                    "GET_JOB"
                ],
                "UPDATE_REMINDER_TODO": [
                    "UPDATE_REMINDER_TODO"
                ],
                "IS_TRUE_RECIPES": [
                    "IS_TRUE_RECIPES"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "REMOVE_FROM_PLAYLIST_MUSIC"
                ],
                "GET_AVAILABILITY": [
                    "GET_AVAILABILITY"
                ],
                "GET_CATEGORY_EVENT": [
                    "GET_CATEGORY_EVENT"
                ],
                "PLAY_MEDIA": [
                    "PLAY_MEDIA"
                ],
                "ADD_TIME_TIMER": [
                    "ADD_TIME_TIMER"
                ],
                "GET_CALL": [
                    "GET_CALL"
                ],
                "SET_AVAILABLE": [
                    "SET_AVAILABLE"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "ADD_TO_PLAYLIST_MUSIC"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "GET_EMPLOYMENT_TIME"
                ],
                "SHARE_EVENT": [
                    "SHARE_EVENT"
                ],
                "PREFER": [
                    "PREFER"
                ],
                "START_SHUFFLE_MUSIC": [
                    "START_SHUFFLE_MUSIC"
                ],
                "GET_CALL_CONTACT": [
                    "GET_CALL_CONTACT"
                ],
                "GET_LOCATION": [
                    "GET_LOCATION"
                ],
                "SILENCE_ALARM": [
                    "SILENCE_ALARM"
                ],
                "SWITCH_CALL": [
                    "SWITCH_CALL"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "GET_TRACK_INFO_MUSIC"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "SUBTRACT_TIME_TIMER"
                ],
                "GET_SUNSET": [
                    "GET_SUNSET"
                ],
                "DELETE_TIMER": [
                    "DELETE_TIMER"
                ],
                "UPDATE_TIMER": [
                    "UPDATE_TIMER"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "PREVIOUS_TRACK_MUSIC"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "SET_DEFAULT_PROVIDER_MUSIC"
                ],
                "HOLD_CALL": [
                    "HOLD_CALL"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "GET_MUTUAL_FRIENDS"
                ],
                "SKIP_TRACK_MUSIC": [
                    "SKIP_TRACK_MUSIC"
                ],
                "UPDATE_METHOD_CALL": [
                    "UPDATE_METHOD_CALL"
                ],
                "SET_RSVP_INTERESTED": [
                    "SET_RSVP_INTERESTED"
                ],
                "QUESTION_MUSIC": [
                    "QUESTION_MUSIC"
                ],
                "GET_UNDERGRAD": [
                    "GET_UNDERGRAD"
                ],
                "PAUSE_TIMER": [
                    "PAUSE_TIMER"
                ],
                "UPDATE_ALARM": [
                    "UPDATE_ALARM"
                ],
                "GET_REMINDER_LOCATION": [
                    "GET_REMINDER_LOCATION"
                ],
                "GET_ATTENDEE_EVENT": [
                    "GET_ATTENDEE_EVENT"
                ],
                "LIKE_MUSIC": [
                    "LIKE_MUSIC"
                ],
                "RESTART_TIMER": [
                    "RESTART_TIMER"
                ],
                "RESUME_TIMER": [
                    "RESUME_TIMER"
                ],
                "MERGE_CALL": [
                    "MERGE_CALL"
                ],
                "GET_MESSAGE_CONTACT": [
                    "GET_MESSAGE_CONTACT"
                ],
                "REPLAY_MUSIC": [
                    "REPLAY_MUSIC"
                ],
                "LOOP_MUSIC": [
                    "LOOP_MUSIC"
                ],
                "GET_REMINDER_AMOUNT": [
                    "GET_REMINDER_AMOUNT"
                ],
                "GET_DATE_TIME_EVENT": [
                    "GET_DATE_TIME_EVENT"
                ],
                "STOP_MUSIC": [
                    "STOP_MUSIC"
                ],
                "GET_DETAILS_NEWS": [
                    "GET_DETAILS_NEWS"
                ],
                "GET_EDUCATION_DEGREE": [
                    "GET_EDUCATION_DEGREE"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "SET_DEFAULT_PROVIDER_CALLING"
                ],
                "GET_MAJOR": [
                    "GET_MAJOR"
                ],
                "UNLOOP_MUSIC": [
                    "UNLOOP_MUSIC"
                ],
                "GET_CONTACT_METHOD": [
                    "GET_CONTACT_METHOD"
                ],
                "SET_RSVP_NO": [
                    "SET_RSVP_NO"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "UPDATE_REMINDER_LOCATION"
                ],
                "RESUME_CALL": [
                    "RESUME_CALL"
                ],
                "CANCEL_MESSAGE": [
                    "CANCEL_MESSAGE"
                ],
                "RESUME_MUSIC": [
                    "RESUME_MUSIC"
                ],
                "UPDATE_REMINDER": [
                    "UPDATE_REMINDER"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "DELETE_PLAYLIST_MUSIC"
                ],
                "REWIND_MUSIC": [
                    "REWIND_MUSIC"
                ],
                "REPEAT_ALL_MUSIC": [
                    "REPEAT_ALL_MUSIC"
                ],
                "FAST_FORWARD_MUSIC": [
                    "FAST_FORWARD_MUSIC"
                ],
                "DISLIKE_MUSIC": [
                    "DISLIKE_MUSIC"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "GET_LIFE_EVENT_TIME"
                ],
                "DISPREFER": [
                    "DISPREFER"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "REPEAT_ALL_OFF_MUSIC"
                ],
                "HELP_REMINDER": [
                    "HELP_REMINDER"
                ],
                "GET_LYRICS_MUSIC": [
                    "GET_LYRICS_MUSIC"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "STOP_SHUFFLE_MUSIC"
                ],
                "GET_AIRQUALITY": [
                    "GET_AIRQUALITY"
                ],
                "GET_LANGUAGE": [
                    "GET_LANGUAGE"
                ],
                "FOLLOW_MUSIC": [
                    "FOLLOW_MUSIC"
                ],
                "GET_GENDER": [
                    "GET_GENDER"
                ],
                "CANCEL_CALL": [
                    "CANCEL_CALL"
                ],
                "GET_GROUP": [
                    "GET_GROUP"
                ]
            }
        },
        "out_of_scope": {
            "version_0": {
                "translate": [
                    "translate"
                ],
                "transfer": [
                    "transfer"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning_of_life"
                ],
                "insurance_change": [
                    "insurance_change"
                ],
                "find_phone": [
                    "find_phone"
                ],
                "travel_alert": [
                    "travel_alert"
                ],
                "pto_request": [
                    "pto_request"
                ],
                "improve_credit_score": [
                    "improve_credit_score"
                ],
                "fun_fact": [
                    "fun_fact"
                ],
                "change_language": [
                    "change_language"
                ],
                "payday": [
                    "payday"
                ],
                "replacement_card_duration": [
                    "replacement_card_duration"
                ],
                "time": [
                    "time"
                ],
                "application_status": [
                    "application_status"
                ],
                "flight_status": [
                    "flight_status"
                ],
                "flip_coin": [
                    "flip_coin"
                ],
                "change_user_name": [
                    "change_user_name"
                ],
                "where_are_you_from": [
                    "where_are_you_from"
                ],
                "shopping_list_update": [
                    "shopping_list_update"
                ],
                "what_can_i_ask_you": [
                    "what_can_i_ask_you"
                ],
                "maybe": [
                    "maybe"
                ],
                "oil_change_how": [
                    "oil_change_how"
                ],
                "restaurant_reservation": [
                    "restaurant_reservation"
                ],
                "balance": [
                    "balance"
                ],
                "confirm_reservation": [
                    "confirm_reservation"
                ],
                "freeze_account": [
                    "freeze_account"
                ],
                "rollover_401k": [
                    "rollover_401k"
                ],
                "who_made_you": [
                    "who_made_you"
                ],
                "distance": [
                    "distance"
                ],
                "user_name": [
                    "user_name"
                ],
                "timezone": [
                    "timezone"
                ],
                "next_song": [
                    "next_song"
                ],
                "transactions": [
                    "transactions"
                ],
                "restaurant_suggestion": [
                    "restaurant_suggestion"
                ],
                "rewards_balance": [
                    "rewards_balance"
                ],
                "pay_bill": [
                    "pay_bill"
                ],
                "spending_history": [
                    "spending_history"
                ],
                "pto_request_status": [
                    "pto_request_status"
                ],
                "credit_score": [
                    "credit_score"
                ],
                "new_card": [
                    "new_card"
                ],
                "lost_luggage": [
                    "lost_luggage"
                ],
                "repeat": [
                    "repeat"
                ],
                "mpg": [
                    "mpg"
                ],
                "oil_change_when": [
                    "oil_change_when"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel_suggestion"
                ],
                "insurance": [
                    "insurance"
                ],
                "todo_list_update": [
                    "todo_list_update"
                ],
                "reminder": [
                    "reminder"
                ],
                "change_speed": [
                    "change_speed"
                ],
                "tire_pressure": [
                    "tire_pressure"
                ],
                "no": [
                    "no"
                ],
                "apr": [
                    "apr"
                ],
                "nutrition_info": [
                    "nutrition_info"
                ],
                "calendar": [
                    "calendar"
                ],
                "uber": [
                    "uber"
                ],
                "calculator": [
                    "calculator"
                ],
                "date": [
                    "date"
                ],
                "carry_on": [
                    "carry_on"
                ],
                "pto_used": [
                    "pto_used"
                ],
                "schedule_maintenance": [
                    "schedule_maintenance"
                ],
                "travel_notification": [
                    "travel_notification"
                ],
                "sync_device": [
                    "sync_device"
                ],
                "thank_you": [
                    "thank_you"
                ],
                "roll_dice": [
                    "roll_dice"
                ],
                "food_last": [
                    "food_last"
                ],
                "cook_time": [
                    "cook_time"
                ],
                "reminder_update": [
                    "reminder_update"
                ],
                "report_lost_card": [
                    "report_lost_card"
                ],
                "ingredient_substitution": [
                    "ingredient_substitution"
                ],
                "make_call": [
                    "make_call"
                ],
                "alarm": [
                    "alarm"
                ],
                "todo_list": [
                    "todo_list"
                ],
                "change_accent": [
                    "change_accent"
                ],
                "w2": [
                    "w2"
                ],
                "bill_due": [
                    "bill_due"
                ],
                "calories": [
                    "calories"
                ],
                "damaged_card": [
                    "damaged_card"
                ],
                "restaurant_reviews": [
                    "restaurant_reviews"
                ],
                "routing": [
                    "routing"
                ],
                "do_you_have_pets": [
                    "do_you_have_pets"
                ],
                "schedule_meeting": [
                    "schedule_meeting"
                ],
                "gas_type": [
                    "gas_type"
                ],
                "plug_type": [
                    "plug_type"
                ],
                "tire_change": [
                    "tire_change"
                ],
                "exchange_rate": [
                    "exchange_rate"
                ],
                "next_holiday": [
                    "next_holiday"
                ],
                "change_volume": [
                    "change_volume"
                ],
                "who_do_you_work_for": [
                    "who_do_you_work_for"
                ],
                "credit_limit": [
                    "credit_limit"
                ],
                "how_busy": [
                    "how_busy"
                ],
                "accept_reservations": [
                    "accept_reservations"
                ],
                "order_status": [
                    "order_status"
                ],
                "pin_change": [
                    "pin_change"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "account_blocked": [
                    "account_blocked"
                ],
                "what_song": [
                    "what_song"
                ],
                "international_fees": [
                    "international_fees"
                ],
                "last_maintenance": [
                    "last_maintenance"
                ],
                "meeting_schedule": [
                    "meeting_schedule"
                ],
                "ingredients_list": [
                    "ingredients_list"
                ],
                "report_fraud": [
                    "report_fraud"
                ],
                "measurement_conversion": [
                    "measurement_conversion"
                ],
                "smart_home": [
                    "smart_home"
                ],
                "book_hotel": [
                    "book_hotel"
                ],
                "current_location": [
                    "current_location"
                ],
                "weather": [
                    "weather"
                ],
                "taxes": [
                    "taxes"
                ],
                "min_payment": [
                    "min_payment"
                ],
                "whisper_mode": [
                    "whisper_mode"
                ],
                "cancel": [
                    "cancel"
                ],
                "international_visa": [
                    "international_visa"
                ],
                "vaccines": [
                    "vaccines"
                ],
                "pto_balance": [
                    "pto_balance"
                ],
                "directions": [
                    "directions"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset_settings"
                ],
                "what_is_your_name": [
                    "what_is_your_name"
                ],
                "direct_deposit": [
                    "direct_deposit"
                ],
                "interest_rate": [
                    "interest_rate"
                ],
                "credit_limit_change": [
                    "credit_limit_change"
                ],
                "what_are_your_hobbies": [
                    "what_are_your_hobbies"
                ],
                "book_flight": [
                    "book_flight"
                ],
                "shopping_list": [
                    "shopping_list"
                ],
                "text": [
                    "text"
                ],
                "bill_balance": [
                    "bill_balance"
                ],
                "share_location": [
                    "share_location"
                ],
                "redeem_rewards": [
                    "redeem_rewards"
                ],
                "play_music": [
                    "play_music"
                ],
                "calendar_update": [
                    "calendar_update"
                ],
                "are_you_a_bot": [
                    "are_you_a_bot"
                ],
                "gas": [
                    "gas"
                ],
                "expiration_date": [
                    "expiration_date"
                ],
                "update_playlist": [
                    "update_playlist"
                ],
                "cancel_reservation": [
                    "cancel_reservation"
                ],
                "tell_joke": [
                    "tell_joke"
                ],
                "change_ai_name": [
                    "change_ai_name"
                ],
                "how_old_are_you": [
                    "how_old_are_you"
                ],
                "car_rental": [
                    "car_rental"
                ],
                "jump_start": [
                    "jump_start"
                ],
                "meal_suggestion": [
                    "meal_suggestion"
                ],
                "recipe": [
                    "recipe"
                ],
                "income": [
                    "income"
                ],
                "order": [
                    "order"
                ],
                "traffic": [
                    "traffic"
                ],
                "order_checks": [
                    "order_checks"
                ],
                "card_declined": [
                    "card_declined"
                ]
            },
            "version_1": {
                "translate": [
                    "translate"
                ],
                "transfer": [
                    "transfer"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning of life"
                ],
                "insurance_change": [
                    "insurance change"
                ],
                "find_phone": [
                    "find phone"
                ],
                "travel_alert": [
                    "travel alert"
                ],
                "pto_request": [
                    "pto request"
                ],
                "improve_credit_score": [
                    "improve credit score"
                ],
                "fun_fact": [
                    "fun fact"
                ],
                "change_language": [
                    "change language"
                ],
                "payday": [
                    "payday"
                ],
                "replacement_card_duration": [
                    "replacement card duration"
                ],
                "time": [
                    "time"
                ],
                "application_status": [
                    "application status"
                ],
                "flight_status": [
                    "flight status"
                ],
                "flip_coin": [
                    "flip coin"
                ],
                "change_user_name": [
                    "change user name"
                ],
                "where_are_you_from": [
                    "where are you from"
                ],
                "shopping_list_update": [
                    "shopping list update"
                ],
                "what_can_i_ask_you": [
                    "what can i ask you"
                ],
                "maybe": [
                    "maybe"
                ],
                "oil_change_how": [
                    "oil change how"
                ],
                "restaurant_reservation": [
                    "restaurant reservation"
                ],
                "balance": [
                    "balance"
                ],
                "confirm_reservation": [
                    "confirm reservation"
                ],
                "freeze_account": [
                    "freeze account"
                ],
                "rollover_401k": [
                    "rollover 401k"
                ],
                "who_made_you": [
                    "who made you"
                ],
                "distance": [
                    "distance"
                ],
                "user_name": [
                    "user name"
                ],
                "timezone": [
                    "timezone"
                ],
                "next_song": [
                    "next song"
                ],
                "transactions": [
                    "transactions"
                ],
                "restaurant_suggestion": [
                    "restaurant suggestion"
                ],
                "rewards_balance": [
                    "rewards balance"
                ],
                "pay_bill": [
                    "pay bill"
                ],
                "spending_history": [
                    "spending history"
                ],
                "pto_request_status": [
                    "pto request status"
                ],
                "credit_score": [
                    "credit score"
                ],
                "new_card": [
                    "new card"
                ],
                "lost_luggage": [
                    "lost luggage"
                ],
                "repeat": [
                    "repeat"
                ],
                "mpg": [
                    "mpg"
                ],
                "oil_change_when": [
                    "oil change when"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel suggestion"
                ],
                "insurance": [
                    "insurance"
                ],
                "todo_list_update": [
                    "todo list update"
                ],
                "reminder": [
                    "reminder"
                ],
                "change_speed": [
                    "change speed"
                ],
                "tire_pressure": [
                    "tire pressure"
                ],
                "no": [
                    "no"
                ],
                "apr": [
                    "apr"
                ],
                "nutrition_info": [
                    "nutrition info"
                ],
                "calendar": [
                    "calendar"
                ],
                "uber": [
                    "uber"
                ],
                "calculator": [
                    "calculator"
                ],
                "date": [
                    "date"
                ],
                "carry_on": [
                    "carry on"
                ],
                "pto_used": [
                    "pto used"
                ],
                "schedule_maintenance": [
                    "schedule maintenance"
                ],
                "travel_notification": [
                    "travel notification"
                ],
                "sync_device": [
                    "sync device"
                ],
                "thank_you": [
                    "thank you"
                ],
                "roll_dice": [
                    "roll dice"
                ],
                "food_last": [
                    "food last"
                ],
                "cook_time": [
                    "cook time"
                ],
                "reminder_update": [
                    "reminder update"
                ],
                "report_lost_card": [
                    "report lost card"
                ],
                "ingredient_substitution": [
                    "ingredient substitution"
                ],
                "make_call": [
                    "make call"
                ],
                "alarm": [
                    "alarm"
                ],
                "todo_list": [
                    "todo list"
                ],
                "change_accent": [
                    "change accent"
                ],
                "w2": [
                    "w2"
                ],
                "bill_due": [
                    "bill due"
                ],
                "calories": [
                    "calories"
                ],
                "damaged_card": [
                    "damaged card"
                ],
                "restaurant_reviews": [
                    "restaurant reviews"
                ],
                "routing": [
                    "routing"
                ],
                "do_you_have_pets": [
                    "do you have pets"
                ],
                "schedule_meeting": [
                    "schedule meeting"
                ],
                "gas_type": [
                    "gas type"
                ],
                "plug_type": [
                    "plug type"
                ],
                "tire_change": [
                    "tire change"
                ],
                "exchange_rate": [
                    "exchange rate"
                ],
                "next_holiday": [
                    "next holiday"
                ],
                "change_volume": [
                    "change volume"
                ],
                "who_do_you_work_for": [
                    "who do you work for"
                ],
                "credit_limit": [
                    "credit limit"
                ],
                "how_busy": [
                    "how busy"
                ],
                "accept_reservations": [
                    "accept reservations"
                ],
                "order_status": [
                    "order status"
                ],
                "pin_change": [
                    "pin change"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "account_blocked": [
                    "account blocked"
                ],
                "what_song": [
                    "what song"
                ],
                "international_fees": [
                    "international fees"
                ],
                "last_maintenance": [
                    "last maintenance"
                ],
                "meeting_schedule": [
                    "meeting schedule"
                ],
                "ingredients_list": [
                    "ingredients list"
                ],
                "report_fraud": [
                    "report fraud"
                ],
                "measurement_conversion": [
                    "measurement conversion"
                ],
                "smart_home": [
                    "smart home"
                ],
                "book_hotel": [
                    "book hotel"
                ],
                "current_location": [
                    "current location"
                ],
                "weather": [
                    "weather"
                ],
                "taxes": [
                    "taxes"
                ],
                "min_payment": [
                    "min payment"
                ],
                "whisper_mode": [
                    "whisper mode"
                ],
                "cancel": [
                    "cancel"
                ],
                "international_visa": [
                    "international visa"
                ],
                "vaccines": [
                    "vaccines"
                ],
                "pto_balance": [
                    "pto balance"
                ],
                "directions": [
                    "directions"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset settings"
                ],
                "what_is_your_name": [
                    "what is your name"
                ],
                "direct_deposit": [
                    "direct deposit"
                ],
                "interest_rate": [
                    "interest rate"
                ],
                "credit_limit_change": [
                    "credit limit change"
                ],
                "what_are_your_hobbies": [
                    "what are your hobbies"
                ],
                "book_flight": [
                    "book flight"
                ],
                "shopping_list": [
                    "shopping list"
                ],
                "text": [
                    "text"
                ],
                "bill_balance": [
                    "bill balance"
                ],
                "share_location": [
                    "share location"
                ],
                "redeem_rewards": [
                    "redeem rewards"
                ],
                "play_music": [
                    "play music"
                ],
                "calendar_update": [
                    "calendar update"
                ],
                "are_you_a_bot": [
                    "are you a bot"
                ],
                "gas": [
                    "gas"
                ],
                "expiration_date": [
                    "expiration date"
                ],
                "update_playlist": [
                    "update playlist"
                ],
                "cancel_reservation": [
                    "cancel reservation"
                ],
                "tell_joke": [
                    "tell joke"
                ],
                "change_ai_name": [
                    "change ai name"
                ],
                "how_old_are_you": [
                    "how old are you"
                ],
                "car_rental": [
                    "car rental"
                ],
                "jump_start": [
                    "jump start"
                ],
                "meal_suggestion": [
                    "meal suggestion"
                ],
                "recipe": [
                    "recipe"
                ],
                "income": [
                    "income"
                ],
                "order": [
                    "order"
                ],
                "traffic": [
                    "traffic"
                ],
                "order_checks": [
                    "order checks"
                ],
                "card_declined": [
                    "card declined"
                ]
            },
            "version_2": {
                "translate": [
                    "Translate"
                ],
                "transfer": [
                    "Transfer"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "Meaning Of Life"
                ],
                "insurance_change": [
                    "Insurance Change"
                ],
                "find_phone": [
                    "Find Phone"
                ],
                "travel_alert": [
                    "Travel Alert"
                ],
                "pto_request": [
                    "Pto Request"
                ],
                "improve_credit_score": [
                    "Improve Credit Score"
                ],
                "fun_fact": [
                    "Fun Fact"
                ],
                "change_language": [
                    "Change Language"
                ],
                "payday": [
                    "Payday"
                ],
                "replacement_card_duration": [
                    "Replacement Card Duration"
                ],
                "time": [
                    "Time"
                ],
                "application_status": [
                    "Application Status"
                ],
                "flight_status": [
                    "Flight Status"
                ],
                "flip_coin": [
                    "Flip Coin"
                ],
                "change_user_name": [
                    "Change User Name"
                ],
                "where_are_you_from": [
                    "Where Are You From"
                ],
                "shopping_list_update": [
                    "Shopping List Update"
                ],
                "what_can_i_ask_you": [
                    "What Can I Ask You"
                ],
                "maybe": [
                    "Maybe"
                ],
                "oil_change_how": [
                    "Oil Change How"
                ],
                "restaurant_reservation": [
                    "Restaurant Reservation"
                ],
                "balance": [
                    "Balance"
                ],
                "confirm_reservation": [
                    "Confirm Reservation"
                ],
                "freeze_account": [
                    "Freeze Account"
                ],
                "rollover_401k": [
                    "Rollover 401k"
                ],
                "who_made_you": [
                    "Who Made You"
                ],
                "distance": [
                    "Distance"
                ],
                "user_name": [
                    "User Name"
                ],
                "timezone": [
                    "Timezone"
                ],
                "next_song": [
                    "Next Song"
                ],
                "transactions": [
                    "Transactions"
                ],
                "restaurant_suggestion": [
                    "Restaurant Suggestion"
                ],
                "rewards_balance": [
                    "Rewards Balance"
                ],
                "pay_bill": [
                    "Pay Bill"
                ],
                "spending_history": [
                    "Spending History"
                ],
                "pto_request_status": [
                    "Pto Request Status"
                ],
                "credit_score": [
                    "Credit Score"
                ],
                "new_card": [
                    "New Card"
                ],
                "lost_luggage": [
                    "Lost Luggage"
                ],
                "repeat": [
                    "Repeat"
                ],
                "mpg": [
                    "Mpg"
                ],
                "oil_change_when": [
                    "Oil Change When"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "Travel Suggestion"
                ],
                "insurance": [
                    "Insurance"
                ],
                "todo_list_update": [
                    "Todo List Update"
                ],
                "reminder": [
                    "Reminder"
                ],
                "change_speed": [
                    "Change Speed"
                ],
                "tire_pressure": [
                    "Tire Pressure"
                ],
                "no": [
                    "No"
                ],
                "apr": [
                    "Apr"
                ],
                "nutrition_info": [
                    "Nutrition Info"
                ],
                "calendar": [
                    "Calendar"
                ],
                "uber": [
                    "Uber"
                ],
                "calculator": [
                    "Calculator"
                ],
                "date": [
                    "Date"
                ],
                "carry_on": [
                    "Carry On"
                ],
                "pto_used": [
                    "Pto Used"
                ],
                "schedule_maintenance": [
                    "Schedule Maintenance"
                ],
                "travel_notification": [
                    "Travel Notification"
                ],
                "sync_device": [
                    "Sync Device"
                ],
                "thank_you": [
                    "Thank You"
                ],
                "roll_dice": [
                    "Roll Dice"
                ],
                "food_last": [
                    "Food Last"
                ],
                "cook_time": [
                    "Cook Time"
                ],
                "reminder_update": [
                    "Reminder Update"
                ],
                "report_lost_card": [
                    "Report Lost Card"
                ],
                "ingredient_substitution": [
                    "Ingredient Substitution"
                ],
                "make_call": [
                    "Make Call"
                ],
                "alarm": [
                    "Alarm"
                ],
                "todo_list": [
                    "Todo List"
                ],
                "change_accent": [
                    "Change Accent"
                ],
                "w2": [
                    "W2"
                ],
                "bill_due": [
                    "Bill Due"
                ],
                "calories": [
                    "Calories"
                ],
                "damaged_card": [
                    "Damaged Card"
                ],
                "restaurant_reviews": [
                    "Restaurant Reviews"
                ],
                "routing": [
                    "Routing"
                ],
                "do_you_have_pets": [
                    "Do You Have Pets"
                ],
                "schedule_meeting": [
                    "Schedule Meeting"
                ],
                "gas_type": [
                    "Gas Type"
                ],
                "plug_type": [
                    "Plug Type"
                ],
                "tire_change": [
                    "Tire Change"
                ],
                "exchange_rate": [
                    "Exchange Rate"
                ],
                "next_holiday": [
                    "Next Holiday"
                ],
                "change_volume": [
                    "Change Volume"
                ],
                "who_do_you_work_for": [
                    "Who Do You Work For"
                ],
                "credit_limit": [
                    "Credit Limit"
                ],
                "how_busy": [
                    "How Busy"
                ],
                "accept_reservations": [
                    "Accept Reservations"
                ],
                "order_status": [
                    "Order Status"
                ],
                "pin_change": [
                    "Pin Change"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "account_blocked": [
                    "Account Blocked"
                ],
                "what_song": [
                    "What Song"
                ],
                "international_fees": [
                    "International Fees"
                ],
                "last_maintenance": [
                    "Last Maintenance"
                ],
                "meeting_schedule": [
                    "Meeting Schedule"
                ],
                "ingredients_list": [
                    "Ingredients List"
                ],
                "report_fraud": [
                    "Report Fraud"
                ],
                "measurement_conversion": [
                    "Measurement Conversion"
                ],
                "smart_home": [
                    "Smart Home"
                ],
                "book_hotel": [
                    "Book Hotel"
                ],
                "current_location": [
                    "Current Location"
                ],
                "weather": [
                    "Weather"
                ],
                "taxes": [
                    "Taxes"
                ],
                "min_payment": [
                    "Min Payment"
                ],
                "whisper_mode": [
                    "Whisper Mode"
                ],
                "cancel": [
                    "Cancel"
                ],
                "international_visa": [
                    "International Visa"
                ],
                "vaccines": [
                    "Vaccines"
                ],
                "pto_balance": [
                    "Pto Balance"
                ],
                "directions": [
                    "Directions"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "Reset Settings"
                ],
                "what_is_your_name": [
                    "What Is Your Name"
                ],
                "direct_deposit": [
                    "Direct Deposit"
                ],
                "interest_rate": [
                    "Interest Rate"
                ],
                "credit_limit_change": [
                    "Credit Limit Change"
                ],
                "what_are_your_hobbies": [
                    "What Are Your Hobbies"
                ],
                "book_flight": [
                    "Book Flight"
                ],
                "shopping_list": [
                    "Shopping List"
                ],
                "text": [
                    "Text"
                ],
                "bill_balance": [
                    "Bill Balance"
                ],
                "share_location": [
                    "Share Location"
                ],
                "redeem_rewards": [
                    "Redeem Rewards"
                ],
                "play_music": [
                    "Play Music"
                ],
                "calendar_update": [
                    "Calendar Update"
                ],
                "are_you_a_bot": [
                    "Are You A Bot"
                ],
                "gas": [
                    "Gas"
                ],
                "expiration_date": [
                    "Expiration Date"
                ],
                "update_playlist": [
                    "Update Playlist"
                ],
                "cancel_reservation": [
                    "Cancel Reservation"
                ],
                "tell_joke": [
                    "Tell Joke"
                ],
                "change_ai_name": [
                    "Change Ai Name"
                ],
                "how_old_are_you": [
                    "How Old Are You"
                ],
                "car_rental": [
                    "Car Rental"
                ],
                "jump_start": [
                    "Jump Start"
                ],
                "meal_suggestion": [
                    "Meal Suggestion"
                ],
                "recipe": [
                    "Recipe"
                ],
                "income": [
                    "Income"
                ],
                "order": [
                    "Order"
                ],
                "traffic": [
                    "Traffic"
                ],
                "order_checks": [
                    "Order Checks"
                ],
                "card_declined": [
                    "Card Declined"
                ]
            },
            "version_3": {
                "translate": [
                    "Translate"
                ],
                "transfer": [
                    "Transfer"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "MeaningOfLife"
                ],
                "insurance_change": [
                    "InsuranceChange"
                ],
                "find_phone": [
                    "FindPhone"
                ],
                "travel_alert": [
                    "TravelAlert"
                ],
                "pto_request": [
                    "PtoRequest"
                ],
                "improve_credit_score": [
                    "ImproveCreditScore"
                ],
                "fun_fact": [
                    "FunFact"
                ],
                "change_language": [
                    "ChangeLanguage"
                ],
                "payday": [
                    "Payday"
                ],
                "replacement_card_duration": [
                    "ReplacementCardDuration"
                ],
                "time": [
                    "Time"
                ],
                "application_status": [
                    "ApplicationStatus"
                ],
                "flight_status": [
                    "FlightStatus"
                ],
                "flip_coin": [
                    "FlipCoin"
                ],
                "change_user_name": [
                    "ChangeUserName"
                ],
                "where_are_you_from": [
                    "WhereAreYouFrom"
                ],
                "shopping_list_update": [
                    "ShoppingListUpdate"
                ],
                "what_can_i_ask_you": [
                    "WhatCanIAskYou"
                ],
                "maybe": [
                    "Maybe"
                ],
                "oil_change_how": [
                    "OilChangeHow"
                ],
                "restaurant_reservation": [
                    "RestaurantReservation"
                ],
                "balance": [
                    "Balance"
                ],
                "confirm_reservation": [
                    "ConfirmReservation"
                ],
                "freeze_account": [
                    "FreezeAccount"
                ],
                "rollover_401k": [
                    "Rollover401k"
                ],
                "who_made_you": [
                    "WhoMadeYou"
                ],
                "distance": [
                    "Distance"
                ],
                "user_name": [
                    "UserName"
                ],
                "timezone": [
                    "Timezone"
                ],
                "next_song": [
                    "NextSong"
                ],
                "transactions": [
                    "Transactions"
                ],
                "restaurant_suggestion": [
                    "RestaurantSuggestion"
                ],
                "rewards_balance": [
                    "RewardsBalance"
                ],
                "pay_bill": [
                    "PayBill"
                ],
                "spending_history": [
                    "SpendingHistory"
                ],
                "pto_request_status": [
                    "PtoRequestStatus"
                ],
                "credit_score": [
                    "CreditScore"
                ],
                "new_card": [
                    "NewCard"
                ],
                "lost_luggage": [
                    "LostLuggage"
                ],
                "repeat": [
                    "Repeat"
                ],
                "mpg": [
                    "Mpg"
                ],
                "oil_change_when": [
                    "OilChangeWhen"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "TravelSuggestion"
                ],
                "insurance": [
                    "Insurance"
                ],
                "todo_list_update": [
                    "TodoListUpdate"
                ],
                "reminder": [
                    "Reminder"
                ],
                "change_speed": [
                    "ChangeSpeed"
                ],
                "tire_pressure": [
                    "TirePressure"
                ],
                "no": [
                    "No"
                ],
                "apr": [
                    "Apr"
                ],
                "nutrition_info": [
                    "NutritionInfo"
                ],
                "calendar": [
                    "Calendar"
                ],
                "uber": [
                    "Uber"
                ],
                "calculator": [
                    "Calculator"
                ],
                "date": [
                    "Date"
                ],
                "carry_on": [
                    "CarryOn"
                ],
                "pto_used": [
                    "PtoUsed"
                ],
                "schedule_maintenance": [
                    "ScheduleMaintenance"
                ],
                "travel_notification": [
                    "TravelNotification"
                ],
                "sync_device": [
                    "SyncDevice"
                ],
                "thank_you": [
                    "ThankYou"
                ],
                "roll_dice": [
                    "RollDice"
                ],
                "food_last": [
                    "FoodLast"
                ],
                "cook_time": [
                    "CookTime"
                ],
                "reminder_update": [
                    "ReminderUpdate"
                ],
                "report_lost_card": [
                    "ReportLostCard"
                ],
                "ingredient_substitution": [
                    "IngredientSubstitution"
                ],
                "make_call": [
                    "MakeCall"
                ],
                "alarm": [
                    "Alarm"
                ],
                "todo_list": [
                    "TodoList"
                ],
                "change_accent": [
                    "ChangeAccent"
                ],
                "w2": [
                    "W2"
                ],
                "bill_due": [
                    "BillDue"
                ],
                "calories": [
                    "Calories"
                ],
                "damaged_card": [
                    "DamagedCard"
                ],
                "restaurant_reviews": [
                    "RestaurantReviews"
                ],
                "routing": [
                    "Routing"
                ],
                "do_you_have_pets": [
                    "DoYouHavePets"
                ],
                "schedule_meeting": [
                    "ScheduleMeeting"
                ],
                "gas_type": [
                    "GasType"
                ],
                "plug_type": [
                    "PlugType"
                ],
                "tire_change": [
                    "TireChange"
                ],
                "exchange_rate": [
                    "ExchangeRate"
                ],
                "next_holiday": [
                    "NextHoliday"
                ],
                "change_volume": [
                    "ChangeVolume"
                ],
                "who_do_you_work_for": [
                    "WhoDoYouWorkFor"
                ],
                "credit_limit": [
                    "CreditLimit"
                ],
                "how_busy": [
                    "HowBusy"
                ],
                "accept_reservations": [
                    "AcceptReservations"
                ],
                "order_status": [
                    "OrderStatus"
                ],
                "pin_change": [
                    "PinChange"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "account_blocked": [
                    "AccountBlocked"
                ],
                "what_song": [
                    "WhatSong"
                ],
                "international_fees": [
                    "InternationalFees"
                ],
                "last_maintenance": [
                    "LastMaintenance"
                ],
                "meeting_schedule": [
                    "MeetingSchedule"
                ],
                "ingredients_list": [
                    "IngredientsList"
                ],
                "report_fraud": [
                    "ReportFraud"
                ],
                "measurement_conversion": [
                    "MeasurementConversion"
                ],
                "smart_home": [
                    "SmartHome"
                ],
                "book_hotel": [
                    "BookHotel"
                ],
                "current_location": [
                    "CurrentLocation"
                ],
                "weather": [
                    "Weather"
                ],
                "taxes": [
                    "Taxes"
                ],
                "min_payment": [
                    "MinPayment"
                ],
                "whisper_mode": [
                    "WhisperMode"
                ],
                "cancel": [
                    "Cancel"
                ],
                "international_visa": [
                    "InternationalVisa"
                ],
                "vaccines": [
                    "Vaccines"
                ],
                "pto_balance": [
                    "PtoBalance"
                ],
                "directions": [
                    "Directions"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "ResetSettings"
                ],
                "what_is_your_name": [
                    "WhatIsYourName"
                ],
                "direct_deposit": [
                    "DirectDeposit"
                ],
                "interest_rate": [
                    "InterestRate"
                ],
                "credit_limit_change": [
                    "CreditLimitChange"
                ],
                "what_are_your_hobbies": [
                    "WhatAreYourHobbies"
                ],
                "book_flight": [
                    "BookFlight"
                ],
                "shopping_list": [
                    "ShoppingList"
                ],
                "text": [
                    "Text"
                ],
                "bill_balance": [
                    "BillBalance"
                ],
                "share_location": [
                    "ShareLocation"
                ],
                "redeem_rewards": [
                    "RedeemRewards"
                ],
                "play_music": [
                    "PlayMusic"
                ],
                "calendar_update": [
                    "CalendarUpdate"
                ],
                "are_you_a_bot": [
                    "AreYouABot"
                ],
                "gas": [
                    "Gas"
                ],
                "expiration_date": [
                    "ExpirationDate"
                ],
                "update_playlist": [
                    "UpdatePlaylist"
                ],
                "cancel_reservation": [
                    "CancelReservation"
                ],
                "tell_joke": [
                    "TellJoke"
                ],
                "change_ai_name": [
                    "ChangeAiName"
                ],
                "how_old_are_you": [
                    "HowOldAreYou"
                ],
                "car_rental": [
                    "CarRental"
                ],
                "jump_start": [
                    "JumpStart"
                ],
                "meal_suggestion": [
                    "MealSuggestion"
                ],
                "recipe": [
                    "Recipe"
                ],
                "income": [
                    "Income"
                ],
                "order": [
                    "Order"
                ],
                "traffic": [
                    "Traffic"
                ],
                "order_checks": [
                    "OrderChecks"
                ],
                "card_declined": [
                    "CardDeclined"
                ]
            },
            "version_4": {
                "translate": [
                    "TRANSLATE"
                ],
                "transfer": [
                    "TRANSFER"
                ],
                "timer": [
                    "TIMER"
                ],
                "definition": [
                    "DEFINITION"
                ],
                "meaning_of_life": [
                    "MEANING_OF_LIFE"
                ],
                "insurance_change": [
                    "INSURANCE_CHANGE"
                ],
                "find_phone": [
                    "FIND_PHONE"
                ],
                "travel_alert": [
                    "TRAVEL_ALERT"
                ],
                "pto_request": [
                    "PTO_REQUEST"
                ],
                "improve_credit_score": [
                    "IMPROVE_CREDIT_SCORE"
                ],
                "fun_fact": [
                    "FUN_FACT"
                ],
                "change_language": [
                    "CHANGE_LANGUAGE"
                ],
                "payday": [
                    "PAYDAY"
                ],
                "replacement_card_duration": [
                    "REPLACEMENT_CARD_DURATION"
                ],
                "time": [
                    "TIME"
                ],
                "application_status": [
                    "APPLICATION_STATUS"
                ],
                "flight_status": [
                    "FLIGHT_STATUS"
                ],
                "flip_coin": [
                    "FLIP_COIN"
                ],
                "change_user_name": [
                    "CHANGE_USER_NAME"
                ],
                "where_are_you_from": [
                    "WHERE_ARE_YOU_FROM"
                ],
                "shopping_list_update": [
                    "SHOPPING_LIST_UPDATE"
                ],
                "what_can_i_ask_you": [
                    "WHAT_CAN_I_ASK_YOU"
                ],
                "maybe": [
                    "MAYBE"
                ],
                "oil_change_how": [
                    "OIL_CHANGE_HOW"
                ],
                "restaurant_reservation": [
                    "RESTAURANT_RESERVATION"
                ],
                "balance": [
                    "BALANCE"
                ],
                "confirm_reservation": [
                    "CONFIRM_RESERVATION"
                ],
                "freeze_account": [
                    "FREEZE_ACCOUNT"
                ],
                "rollover_401k": [
                    "ROLLOVER_401K"
                ],
                "who_made_you": [
                    "WHO_MADE_YOU"
                ],
                "distance": [
                    "DISTANCE"
                ],
                "user_name": [
                    "USER_NAME"
                ],
                "timezone": [
                    "TIMEZONE"
                ],
                "next_song": [
                    "NEXT_SONG"
                ],
                "transactions": [
                    "TRANSACTIONS"
                ],
                "restaurant_suggestion": [
                    "RESTAURANT_SUGGESTION"
                ],
                "rewards_balance": [
                    "REWARDS_BALANCE"
                ],
                "pay_bill": [
                    "PAY_BILL"
                ],
                "spending_history": [
                    "SPENDING_HISTORY"
                ],
                "pto_request_status": [
                    "PTO_REQUEST_STATUS"
                ],
                "credit_score": [
                    "CREDIT_SCORE"
                ],
                "new_card": [
                    "NEW_CARD"
                ],
                "lost_luggage": [
                    "LOST_LUGGAGE"
                ],
                "repeat": [
                    "REPEAT"
                ],
                "mpg": [
                    "MPG"
                ],
                "oil_change_when": [
                    "OIL_CHANGE_WHEN"
                ],
                "yes": [
                    "YES"
                ],
                "travel_suggestion": [
                    "TRAVEL_SUGGESTION"
                ],
                "insurance": [
                    "INSURANCE"
                ],
                "todo_list_update": [
                    "TODO_LIST_UPDATE"
                ],
                "reminder": [
                    "REMINDER"
                ],
                "change_speed": [
                    "CHANGE_SPEED"
                ],
                "tire_pressure": [
                    "TIRE_PRESSURE"
                ],
                "no": [
                    "NO"
                ],
                "apr": [
                    "APR"
                ],
                "nutrition_info": [
                    "NUTRITION_INFO"
                ],
                "calendar": [
                    "CALENDAR"
                ],
                "uber": [
                    "UBER"
                ],
                "calculator": [
                    "CALCULATOR"
                ],
                "date": [
                    "DATE"
                ],
                "carry_on": [
                    "CARRY_ON"
                ],
                "pto_used": [
                    "PTO_USED"
                ],
                "schedule_maintenance": [
                    "SCHEDULE_MAINTENANCE"
                ],
                "travel_notification": [
                    "TRAVEL_NOTIFICATION"
                ],
                "sync_device": [
                    "SYNC_DEVICE"
                ],
                "thank_you": [
                    "THANK_YOU"
                ],
                "roll_dice": [
                    "ROLL_DICE"
                ],
                "food_last": [
                    "FOOD_LAST"
                ],
                "cook_time": [
                    "COOK_TIME"
                ],
                "reminder_update": [
                    "REMINDER_UPDATE"
                ],
                "report_lost_card": [
                    "REPORT_LOST_CARD"
                ],
                "ingredient_substitution": [
                    "INGREDIENT_SUBSTITUTION"
                ],
                "make_call": [
                    "MAKE_CALL"
                ],
                "alarm": [
                    "ALARM"
                ],
                "todo_list": [
                    "TODO_LIST"
                ],
                "change_accent": [
                    "CHANGE_ACCENT"
                ],
                "w2": [
                    "W2"
                ],
                "bill_due": [
                    "BILL_DUE"
                ],
                "calories": [
                    "CALORIES"
                ],
                "damaged_card": [
                    "DAMAGED_CARD"
                ],
                "restaurant_reviews": [
                    "RESTAURANT_REVIEWS"
                ],
                "routing": [
                    "ROUTING"
                ],
                "do_you_have_pets": [
                    "DO_YOU_HAVE_PETS"
                ],
                "schedule_meeting": [
                    "SCHEDULE_MEETING"
                ],
                "gas_type": [
                    "GAS_TYPE"
                ],
                "plug_type": [
                    "PLUG_TYPE"
                ],
                "tire_change": [
                    "TIRE_CHANGE"
                ],
                "exchange_rate": [
                    "EXCHANGE_RATE"
                ],
                "next_holiday": [
                    "NEXT_HOLIDAY"
                ],
                "change_volume": [
                    "CHANGE_VOLUME"
                ],
                "who_do_you_work_for": [
                    "WHO_DO_YOU_WORK_FOR"
                ],
                "credit_limit": [
                    "CREDIT_LIMIT"
                ],
                "how_busy": [
                    "HOW_BUSY"
                ],
                "accept_reservations": [
                    "ACCEPT_RESERVATIONS"
                ],
                "order_status": [
                    "ORDER_STATUS"
                ],
                "pin_change": [
                    "PIN_CHANGE"
                ],
                "goodbye": [
                    "GOODBYE"
                ],
                "account_blocked": [
                    "ACCOUNT_BLOCKED"
                ],
                "what_song": [
                    "WHAT_SONG"
                ],
                "international_fees": [
                    "INTERNATIONAL_FEES"
                ],
                "last_maintenance": [
                    "LAST_MAINTENANCE"
                ],
                "meeting_schedule": [
                    "MEETING_SCHEDULE"
                ],
                "ingredients_list": [
                    "INGREDIENTS_LIST"
                ],
                "report_fraud": [
                    "REPORT_FRAUD"
                ],
                "measurement_conversion": [
                    "MEASUREMENT_CONVERSION"
                ],
                "smart_home": [
                    "SMART_HOME"
                ],
                "book_hotel": [
                    "BOOK_HOTEL"
                ],
                "current_location": [
                    "CURRENT_LOCATION"
                ],
                "weather": [
                    "WEATHER"
                ],
                "taxes": [
                    "TAXES"
                ],
                "min_payment": [
                    "MIN_PAYMENT"
                ],
                "whisper_mode": [
                    "WHISPER_MODE"
                ],
                "cancel": [
                    "CANCEL"
                ],
                "international_visa": [
                    "INTERNATIONAL_VISA"
                ],
                "vaccines": [
                    "VACCINES"
                ],
                "pto_balance": [
                    "PTO_BALANCE"
                ],
                "directions": [
                    "DIRECTIONS"
                ],
                "spelling": [
                    "SPELLING"
                ],
                "greeting": [
                    "GREETING"
                ],
                "reset_settings": [
                    "RESET_SETTINGS"
                ],
                "what_is_your_name": [
                    "WHAT_IS_YOUR_NAME"
                ],
                "direct_deposit": [
                    "DIRECT_DEPOSIT"
                ],
                "interest_rate": [
                    "INTEREST_RATE"
                ],
                "credit_limit_change": [
                    "CREDIT_LIMIT_CHANGE"
                ],
                "what_are_your_hobbies": [
                    "WHAT_ARE_YOUR_HOBBIES"
                ],
                "book_flight": [
                    "BOOK_FLIGHT"
                ],
                "shopping_list": [
                    "SHOPPING_LIST"
                ],
                "text": [
                    "TEXT"
                ],
                "bill_balance": [
                    "BILL_BALANCE"
                ],
                "share_location": [
                    "SHARE_LOCATION"
                ],
                "redeem_rewards": [
                    "REDEEM_REWARDS"
                ],
                "play_music": [
                    "PLAY_MUSIC"
                ],
                "calendar_update": [
                    "CALENDAR_UPDATE"
                ],
                "are_you_a_bot": [
                    "ARE_YOU_A_BOT"
                ],
                "gas": [
                    "GAS"
                ],
                "expiration_date": [
                    "EXPIRATION_DATE"
                ],
                "update_playlist": [
                    "UPDATE_PLAYLIST"
                ],
                "cancel_reservation": [
                    "CANCEL_RESERVATION"
                ],
                "tell_joke": [
                    "TELL_JOKE"
                ],
                "change_ai_name": [
                    "CHANGE_AI_NAME"
                ],
                "how_old_are_you": [
                    "HOW_OLD_ARE_YOU"
                ],
                "car_rental": [
                    "CAR_RENTAL"
                ],
                "jump_start": [
                    "JUMP_START"
                ],
                "meal_suggestion": [
                    "MEAL_SUGGESTION"
                ],
                "recipe": [
                    "RECIPE"
                ],
                "income": [
                    "INCOME"
                ],
                "order": [
                    "ORDER"
                ],
                "traffic": [
                    "TRAFFIC"
                ],
                "order_checks": [
                    "ORDER_CHECKS"
                ],
                "card_declined": [
                    "CARD_DECLINED"
                ]
            }
        },
        "ri_sawoz_domain": {
            "version_0": {
                "旅游景点": ["旅游景点", "景点"],
                "通用": ["通用"],
                "餐厅": ["餐厅"],
                "酒店": ["酒店"],
                "火车": ["火车"],
                "飞机": ["飞机"],
                "天气": ["天气"],
                "电影": ["电影"],
                "电视剧": ["电视剧"],
                "医院": ["医院"],
                "电脑": ["电脑"],
                "汽车": ["汽车"],
                "辅导班": ["辅导班"],

            },
        },
        "ri_sawoz_general": {
            "version_0": {
                "Bye": ["bye"],
                "Greeting": ["greet", "greeting"],
            },
            "version_1": {
                "Bye": ["Bye", "Bye bye"],
                "Greeting": ["Greet", "Greeting"],
            },
        },
        "small_talk": {
            "version_0": {
                "agent_acquaintance": [
                    "agent_acquaintance"
                ],
                "agent_age": [
                    "agent_age"
                ],
                "agent_annoying": [
                    "agent_annoying"
                ],
                "agent_answer_my_question": [
                    "agent_answer_my_question"
                ],
                "agent_bad": [
                    "agent_bad"
                ],
                "agent_be_clever": [
                    "agent_be_clever"
                ],
                "agent_beautiful": [
                    "agent_beautiful"
                ],
                "agent_birth_date": [
                    "agent_birth_date"
                ],
                "agent_boring": [
                    "agent_boring"
                ],
                "agent_boss": [
                    "agent_boss"
                ],
                "agent_busy": [
                    "agent_busy"
                ],
                "agent_chatbot": [
                    "agent_chatbot"
                ],
                "agent_clever": [
                    "agent_clever"
                ],
                "agent_crazy": [
                    "agent_crazy"
                ],
                "agent_fired": [
                    "agent_fired"
                ],
                "agent_funny": [
                    "agent_funny"
                ],
                "agent_good": [
                    "agent_good"
                ],
                "agent_happy": [
                    "agent_happy"
                ],
                "agent_hungry": [
                    "agent_hungry"
                ],
                "agent_marry_user": [
                    "agent_marry_user"
                ],
                "agent_my_friend": [
                    "agent_my_friend"
                ],
                "agent_occupation": [
                    "agent_occupation"
                ],
                "agent_origin": [
                    "agent_origin"
                ],
                "agent_ready": [
                    "agent_ready"
                ],
                "agent_real": [
                    "agent_real"
                ],
                "agent_residence": [
                    "agent_residence"
                ],
                "agent_right": [
                    "agent_right"
                ],
                "confirmation_yes": [
                    "confirmation_yes"
                ],
                "agent_sure": [
                    "agent_sure"
                ],
                "agent_talk_to_me": [
                    "agent_talk_to_me"
                ],
                "agent_there": [
                    "agent_there"
                ],
                "appraisal_bad": [
                    "appraisal_bad"
                ],
                "appraisal_good": [
                    "appraisal_good"
                ],
                "appraisal_no_problem": [
                    "appraisal_no_problem"
                ],
                "appraisal_thank_you": [
                    "appraisal_thank_you"
                ],
                "appraisal_welcome": [
                    "appraisal_welcome"
                ],
                "appraisal_well_done": [
                    "appraisal_well_done"
                ],
                "confirmation_cancel": [
                    "confirmation_cancel"
                ],
                "confirmation_no": [
                    "confirmation_no"
                ],
                "dialog_hold_on": [
                    "dialog_hold_on"
                ],
                "dialog_hug": [
                    "dialog_hug"
                ],
                "dialog_i_do_not_care": [
                    "dialog_i_do_not_care"
                ],
                "dialog_sorry": [
                    "dialog_sorry"
                ],
                "dialog_what_do_you_mean": [
                    "dialog_what_do_you_mean"
                ],
                "dialog_wrong": [
                    "dialog_wrong"
                ],
                "emotions_ha_ha": [
                    "emotions_ha_ha"
                ],
                "emotions_wow": [
                    "emotions_wow"
                ],
                "greetings_bye": [
                    "greetings_bye"
                ],
                "greetings_goodevening": [
                    "greetings_goodevening"
                ],
                "greetings_goodmorning": [
                    "greetings_goodmorning"
                ],
                "greetings_goodnight": [
                    "greetings_goodnight"
                ],
                "greetings_hello": [
                    "greetings_hello"
                ],
                "greetings_how_are_you": [
                    "greetings_how_are_you"
                ],
                "greetings_nice_to_meet_you": [
                    "greetings_nice_to_meet_you"
                ],
                "greetings_nice_to_see_you": [
                    "greetings_nice_to_see_you"
                ],
                "greetings_nice_to_talk_to_you": [
                    "greetings_nice_to_talk_to_you"
                ],
                "greetings_whatsup": [
                    "greetings_whatsup"
                ],
                "user_angry": [
                    "user_angry"
                ],
                "user_back": [
                    "user_back"
                ],
                "user_bored": [
                    "user_bored"
                ],
                "user_busy": [
                    "user_busy"
                ],
                "user_can_not_sleep": [
                    "user_can_not_sleep"
                ],
                "user_does_not_want_to_talk": [
                    "user_does_not_want_to_talk"
                ],
                "user_excited": [
                    "user_excited"
                ],
                "user_going_to_bed": [
                    "user_going_to_bed"
                ],
                "user_good": [
                    "user_good"
                ],
                "user_happy": [
                    "user_happy"
                ],
                "user_has_birthday": [
                    "user_has_birthday"
                ],
                "user_here": [
                    "user_here"
                ],
                "user_joking": [
                    "user_joking"
                ],
                "user_likes_agent": [
                    "user_likes_agent"
                ],
                "user_lonely": [
                    "user_lonely"
                ],
                "user_looks_like": [
                    "user_looks_like"
                ],
                "user_loves_agent": [
                    "user_loves_agent"
                ],
                "user_misses_agent": [
                    "user_misses_agent"
                ],
                "user_needs_advice": [
                    "user_needs_advice"
                ],
                "user_sad": [
                    "user_sad"
                ],
                "user_sleepy": [
                    "user_sleepy"
                ],
                "user_testing_agent": [
                    "user_testing_agent"
                ],
                "user_tired": [
                    "user_tired"
                ],
                "user_waits": [
                    "user_waits"
                ],
                "user_wants_to_see_agent_again": [
                    "user_wants_to_see_agent_again"
                ],
                "user_wants_to_talk": [
                    "user_wants_to_talk"
                ],
                "user_will_be_back": [
                    "user_will_be_back"
                ]
            },
            "version_1": {
                "agent_acquaintance": [
                    "agent acquaintance"
                ],
                "agent_age": [
                    "agent age"
                ],
                "agent_annoying": [
                    "agent annoying"
                ],
                "agent_answer_my_question": [
                    "agent answer my question"
                ],
                "agent_bad": [
                    "agent bad"
                ],
                "agent_be_clever": [
                    "agent be clever"
                ],
                "agent_beautiful": [
                    "agent beautiful"
                ],
                "agent_birth_date": [
                    "agent birth date"
                ],
                "agent_boring": [
                    "agent boring"
                ],
                "agent_boss": [
                    "agent boss"
                ],
                "agent_busy": [
                    "agent busy"
                ],
                "agent_chatbot": [
                    "agent chatbot"
                ],
                "agent_clever": [
                    "agent clever"
                ],
                "agent_crazy": [
                    "agent crazy"
                ],
                "agent_fired": [
                    "agent fired"
                ],
                "agent_funny": [
                    "agent funny"
                ],
                "agent_good": [
                    "agent good"
                ],
                "agent_happy": [
                    "agent happy"
                ],
                "agent_hungry": [
                    "agent hungry"
                ],
                "agent_marry_user": [
                    "agent marry user"
                ],
                "agent_my_friend": [
                    "agent my friend"
                ],
                "agent_occupation": [
                    "agent occupation"
                ],
                "agent_origin": [
                    "agent origin"
                ],
                "agent_ready": [
                    "agent ready"
                ],
                "agent_real": [
                    "agent real"
                ],
                "agent_residence": [
                    "agent residence"
                ],
                "agent_right": [
                    "agent right"
                ],
                "confirmation_yes": [
                    "confirmation yes"
                ],
                "agent_sure": [
                    "agent sure"
                ],
                "agent_talk_to_me": [
                    "agent talk to me"
                ],
                "agent_there": [
                    "agent there"
                ],
                "appraisal_bad": [
                    "appraisal bad"
                ],
                "appraisal_good": [
                    "appraisal good"
                ],
                "appraisal_no_problem": [
                    "appraisal no problem"
                ],
                "appraisal_thank_you": [
                    "appraisal thank you"
                ],
                "appraisal_welcome": [
                    "appraisal welcome"
                ],
                "appraisal_well_done": [
                    "appraisal well done"
                ],
                "confirmation_cancel": [
                    "confirmation cancel"
                ],
                "confirmation_no": [
                    "confirmation no"
                ],
                "dialog_hold_on": [
                    "dialog hold on"
                ],
                "dialog_hug": [
                    "dialog hug"
                ],
                "dialog_i_do_not_care": [
                    "dialog i do not care"
                ],
                "dialog_sorry": [
                    "dialog sorry"
                ],
                "dialog_what_do_you_mean": [
                    "dialog what do you mean"
                ],
                "dialog_wrong": [
                    "dialog wrong"
                ],
                "emotions_ha_ha": [
                    "emotions ha ha"
                ],
                "emotions_wow": [
                    "emotions wow"
                ],
                "greetings_bye": [
                    "greetings bye"
                ],
                "greetings_goodevening": [
                    "greetings goodevening"
                ],
                "greetings_goodmorning": [
                    "greetings goodmorning"
                ],
                "greetings_goodnight": [
                    "greetings goodnight"
                ],
                "greetings_hello": [
                    "greetings hello"
                ],
                "greetings_how_are_you": [
                    "greetings how are you"
                ],
                "greetings_nice_to_meet_you": [
                    "greetings nice to meet you"
                ],
                "greetings_nice_to_see_you": [
                    "greetings nice to see you"
                ],
                "greetings_nice_to_talk_to_you": [
                    "greetings nice to talk to you"
                ],
                "greetings_whatsup": [
                    "greetings whatsup"
                ],
                "user_angry": [
                    "user angry"
                ],
                "user_back": [
                    "user back"
                ],
                "user_bored": [
                    "user bored"
                ],
                "user_busy": [
                    "user busy"
                ],
                "user_can_not_sleep": [
                    "user can not sleep"
                ],
                "user_does_not_want_to_talk": [
                    "user does not want to talk"
                ],
                "user_excited": [
                    "user excited"
                ],
                "user_going_to_bed": [
                    "user going to bed"
                ],
                "user_good": [
                    "user good"
                ],
                "user_happy": [
                    "user happy"
                ],
                "user_has_birthday": [
                    "user has birthday"
                ],
                "user_here": [
                    "user here"
                ],
                "user_joking": [
                    "user joking"
                ],
                "user_likes_agent": [
                    "user likes agent"
                ],
                "user_lonely": [
                    "user lonely"
                ],
                "user_looks_like": [
                    "user looks like"
                ],
                "user_loves_agent": [
                    "user loves agent"
                ],
                "user_misses_agent": [
                    "user misses agent"
                ],
                "user_needs_advice": [
                    "user needs advice"
                ],
                "user_sad": [
                    "user sad"
                ],
                "user_sleepy": [
                    "user sleepy"
                ],
                "user_testing_agent": [
                    "user testing agent"
                ],
                "user_tired": [
                    "user tired"
                ],
                "user_waits": [
                    "user waits"
                ],
                "user_wants_to_see_agent_again": [
                    "user wants to see agent again"
                ],
                "user_wants_to_talk": [
                    "user wants to talk"
                ],
                "user_will_be_back": [
                    "user will be back"
                ]
            },
            "version_2": {
                "agent_acquaintance": [
                    "Agent Acquaintance"
                ],
                "agent_age": [
                    "Agent Age"
                ],
                "agent_annoying": [
                    "Agent Annoying"
                ],
                "agent_answer_my_question": [
                    "Agent Answer My Question"
                ],
                "agent_bad": [
                    "Agent Bad"
                ],
                "agent_be_clever": [
                    "Agent Be Clever"
                ],
                "agent_beautiful": [
                    "Agent Beautiful"
                ],
                "agent_birth_date": [
                    "Agent Birth Date"
                ],
                "agent_boring": [
                    "Agent Boring"
                ],
                "agent_boss": [
                    "Agent Boss"
                ],
                "agent_busy": [
                    "Agent Busy"
                ],
                "agent_chatbot": [
                    "Agent Chatbot"
                ],
                "agent_clever": [
                    "Agent Clever"
                ],
                "agent_crazy": [
                    "Agent Crazy"
                ],
                "agent_fired": [
                    "Agent Fired"
                ],
                "agent_funny": [
                    "Agent Funny"
                ],
                "agent_good": [
                    "Agent Good"
                ],
                "agent_happy": [
                    "Agent Happy"
                ],
                "agent_hungry": [
                    "Agent Hungry"
                ],
                "agent_marry_user": [
                    "Agent Marry User"
                ],
                "agent_my_friend": [
                    "Agent My Friend"
                ],
                "agent_occupation": [
                    "Agent Occupation"
                ],
                "agent_origin": [
                    "Agent Origin"
                ],
                "agent_ready": [
                    "Agent Ready"
                ],
                "agent_real": [
                    "Agent Real"
                ],
                "agent_residence": [
                    "Agent Residence"
                ],
                "agent_right": [
                    "Agent Right"
                ],
                "confirmation_yes": [
                    "Confirmation Yes"
                ],
                "agent_sure": [
                    "Agent Sure"
                ],
                "agent_talk_to_me": [
                    "Agent Talk To Me"
                ],
                "agent_there": [
                    "Agent There"
                ],
                "appraisal_bad": [
                    "Appraisal Bad"
                ],
                "appraisal_good": [
                    "Appraisal Good"
                ],
                "appraisal_no_problem": [
                    "Appraisal No Problem"
                ],
                "appraisal_thank_you": [
                    "Appraisal Thank You"
                ],
                "appraisal_welcome": [
                    "Appraisal Welcome"
                ],
                "appraisal_well_done": [
                    "Appraisal Well Done"
                ],
                "confirmation_cancel": [
                    "Confirmation Cancel"
                ],
                "confirmation_no": [
                    "Confirmation No"
                ],
                "dialog_hold_on": [
                    "Dialog Hold On"
                ],
                "dialog_hug": [
                    "Dialog Hug"
                ],
                "dialog_i_do_not_care": [
                    "Dialog I Do Not Care"
                ],
                "dialog_sorry": [
                    "Dialog Sorry"
                ],
                "dialog_what_do_you_mean": [
                    "Dialog What Do You Mean"
                ],
                "dialog_wrong": [
                    "Dialog Wrong"
                ],
                "emotions_ha_ha": [
                    "Emotions Ha Ha"
                ],
                "emotions_wow": [
                    "Emotions Wow"
                ],
                "greetings_bye": [
                    "Greetings Bye"
                ],
                "greetings_goodevening": [
                    "Greetings Goodevening"
                ],
                "greetings_goodmorning": [
                    "Greetings Goodmorning"
                ],
                "greetings_goodnight": [
                    "Greetings Goodnight"
                ],
                "greetings_hello": [
                    "Greetings Hello"
                ],
                "greetings_how_are_you": [
                    "Greetings How Are You"
                ],
                "greetings_nice_to_meet_you": [
                    "Greetings Nice To Meet You"
                ],
                "greetings_nice_to_see_you": [
                    "Greetings Nice To See You"
                ],
                "greetings_nice_to_talk_to_you": [
                    "Greetings Nice To Talk To You"
                ],
                "greetings_whatsup": [
                    "Greetings Whatsup"
                ],
                "user_angry": [
                    "User Angry"
                ],
                "user_back": [
                    "User Back"
                ],
                "user_bored": [
                    "User Bored"
                ],
                "user_busy": [
                    "User Busy"
                ],
                "user_can_not_sleep": [
                    "User Can Not Sleep"
                ],
                "user_does_not_want_to_talk": [
                    "User Does Not Want To Talk"
                ],
                "user_excited": [
                    "User Excited"
                ],
                "user_going_to_bed": [
                    "User Going To Bed"
                ],
                "user_good": [
                    "User Good"
                ],
                "user_happy": [
                    "User Happy"
                ],
                "user_has_birthday": [
                    "User Has Birthday"
                ],
                "user_here": [
                    "User Here"
                ],
                "user_joking": [
                    "User Joking"
                ],
                "user_likes_agent": [
                    "User Likes Agent"
                ],
                "user_lonely": [
                    "User Lonely"
                ],
                "user_looks_like": [
                    "User Looks Like"
                ],
                "user_loves_agent": [
                    "User Loves Agent"
                ],
                "user_misses_agent": [
                    "User Misses Agent"
                ],
                "user_needs_advice": [
                    "User Needs Advice"
                ],
                "user_sad": [
                    "User Sad"
                ],
                "user_sleepy": [
                    "User Sleepy"
                ],
                "user_testing_agent": [
                    "User Testing Agent"
                ],
                "user_tired": [
                    "User Tired"
                ],
                "user_waits": [
                    "User Waits"
                ],
                "user_wants_to_see_agent_again": [
                    "User Wants To See Agent Again"
                ],
                "user_wants_to_talk": [
                    "User Wants To Talk"
                ],
                "user_will_be_back": [
                    "User Will Be Back"
                ]
            },
            "version_3": {
                "agent_acquaintance": [
                    "AgentAcquaintance"
                ],
                "agent_age": [
                    "AgentAge"
                ],
                "agent_annoying": [
                    "AgentAnnoying"
                ],
                "agent_answer_my_question": [
                    "AgentAnswerMyQuestion"
                ],
                "agent_bad": [
                    "AgentBad"
                ],
                "agent_be_clever": [
                    "AgentBeClever"
                ],
                "agent_beautiful": [
                    "AgentBeautiful"
                ],
                "agent_birth_date": [
                    "AgentBirthDate"
                ],
                "agent_boring": [
                    "AgentBoring"
                ],
                "agent_boss": [
                    "AgentBoss"
                ],
                "agent_busy": [
                    "AgentBusy"
                ],
                "agent_chatbot": [
                    "AgentChatbot"
                ],
                "agent_clever": [
                    "AgentClever"
                ],
                "agent_crazy": [
                    "AgentCrazy"
                ],
                "agent_fired": [
                    "AgentFired"
                ],
                "agent_funny": [
                    "AgentFunny"
                ],
                "agent_good": [
                    "AgentGood"
                ],
                "agent_happy": [
                    "AgentHappy"
                ],
                "agent_hungry": [
                    "AgentHungry"
                ],
                "agent_marry_user": [
                    "AgentMarryUser"
                ],
                "agent_my_friend": [
                    "AgentMyFriend"
                ],
                "agent_occupation": [
                    "AgentOccupation"
                ],
                "agent_origin": [
                    "AgentOrigin"
                ],
                "agent_ready": [
                    "AgentReady"
                ],
                "agent_real": [
                    "AgentReal"
                ],
                "agent_residence": [
                    "AgentResidence"
                ],
                "agent_right": [
                    "AgentRight"
                ],
                "confirmation_yes": [
                    "ConfirmationYes"
                ],
                "agent_sure": [
                    "AgentSure"
                ],
                "agent_talk_to_me": [
                    "AgentTalkToMe"
                ],
                "agent_there": [
                    "AgentThere"
                ],
                "appraisal_bad": [
                    "AppraisalBad"
                ],
                "appraisal_good": [
                    "AppraisalGood"
                ],
                "appraisal_no_problem": [
                    "AppraisalNoProblem"
                ],
                "appraisal_thank_you": [
                    "AppraisalThankYou"
                ],
                "appraisal_welcome": [
                    "AppraisalWelcome"
                ],
                "appraisal_well_done": [
                    "AppraisalWellDone"
                ],
                "confirmation_cancel": [
                    "ConfirmationCancel"
                ],
                "confirmation_no": [
                    "ConfirmationNo"
                ],
                "dialog_hold_on": [
                    "DialogHoldOn"
                ],
                "dialog_hug": [
                    "DialogHug"
                ],
                "dialog_i_do_not_care": [
                    "DialogIDoNotCare"
                ],
                "dialog_sorry": [
                    "DialogSorry"
                ],
                "dialog_what_do_you_mean": [
                    "DialogWhatDoYouMean"
                ],
                "dialog_wrong": [
                    "DialogWrong"
                ],
                "emotions_ha_ha": [
                    "EmotionsHaHa"
                ],
                "emotions_wow": [
                    "EmotionsWow"
                ],
                "greetings_bye": [
                    "GreetingsBye"
                ],
                "greetings_goodevening": [
                    "GreetingsGoodevening"
                ],
                "greetings_goodmorning": [
                    "GreetingsGoodmorning"
                ],
                "greetings_goodnight": [
                    "GreetingsGoodnight"
                ],
                "greetings_hello": [
                    "GreetingsHello"
                ],
                "greetings_how_are_you": [
                    "GreetingsHowAreYou"
                ],
                "greetings_nice_to_meet_you": [
                    "GreetingsNiceToMeetYou"
                ],
                "greetings_nice_to_see_you": [
                    "GreetingsNiceToSeeYou"
                ],
                "greetings_nice_to_talk_to_you": [
                    "GreetingsNiceToTalkToYou"
                ],
                "greetings_whatsup": [
                    "GreetingsWhatsup"
                ],
                "user_angry": [
                    "UserAngry"
                ],
                "user_back": [
                    "UserBack"
                ],
                "user_bored": [
                    "UserBored"
                ],
                "user_busy": [
                    "UserBusy"
                ],
                "user_can_not_sleep": [
                    "UserCanNotSleep"
                ],
                "user_does_not_want_to_talk": [
                    "UserDoesNotWantToTalk"
                ],
                "user_excited": [
                    "UserExcited"
                ],
                "user_going_to_bed": [
                    "UserGoingToBed"
                ],
                "user_good": [
                    "UserGood"
                ],
                "user_happy": [
                    "UserHappy"
                ],
                "user_has_birthday": [
                    "UserHasBirthday"
                ],
                "user_here": [
                    "UserHere"
                ],
                "user_joking": [
                    "UserJoking"
                ],
                "user_likes_agent": [
                    "UserLikesAgent"
                ],
                "user_lonely": [
                    "UserLonely"
                ],
                "user_looks_like": [
                    "UserLooksLike"
                ],
                "user_loves_agent": [
                    "UserLovesAgent"
                ],
                "user_misses_agent": [
                    "UserMissesAgent"
                ],
                "user_needs_advice": [
                    "UserNeedsAdvice"
                ],
                "user_sad": [
                    "UserSad"
                ],
                "user_sleepy": [
                    "UserSleepy"
                ],
                "user_testing_agent": [
                    "UserTestingAgent"
                ],
                "user_tired": [
                    "UserTired"
                ],
                "user_waits": [
                    "UserWaits"
                ],
                "user_wants_to_see_agent_again": [
                    "UserWantsToSeeAgentAgain"
                ],
                "user_wants_to_talk": [
                    "UserWantsToTalk"
                ],
                "user_will_be_back": [
                    "UserWillBeBack"
                ]
            },
            "version_4": {
                "agent_acquaintance": [
                    "AGENT_ACQUAINTANCE"
                ],
                "agent_age": [
                    "AGENT_AGE"
                ],
                "agent_annoying": [
                    "AGENT_ANNOYING"
                ],
                "agent_answer_my_question": [
                    "AGENT_ANSWER_MY_QUESTION"
                ],
                "agent_bad": [
                    "AGENT_BAD"
                ],
                "agent_be_clever": [
                    "AGENT_BE_CLEVER"
                ],
                "agent_beautiful": [
                    "AGENT_BEAUTIFUL"
                ],
                "agent_birth_date": [
                    "AGENT_BIRTH_DATE"
                ],
                "agent_boring": [
                    "AGENT_BORING"
                ],
                "agent_boss": [
                    "AGENT_BOSS"
                ],
                "agent_busy": [
                    "AGENT_BUSY"
                ],
                "agent_chatbot": [
                    "AGENT_CHATBOT"
                ],
                "agent_clever": [
                    "AGENT_CLEVER"
                ],
                "agent_crazy": [
                    "AGENT_CRAZY"
                ],
                "agent_fired": [
                    "AGENT_FIRED"
                ],
                "agent_funny": [
                    "AGENT_FUNNY"
                ],
                "agent_good": [
                    "AGENT_GOOD"
                ],
                "agent_happy": [
                    "AGENT_HAPPY"
                ],
                "agent_hungry": [
                    "AGENT_HUNGRY"
                ],
                "agent_marry_user": [
                    "AGENT_MARRY_USER"
                ],
                "agent_my_friend": [
                    "AGENT_MY_FRIEND"
                ],
                "agent_occupation": [
                    "AGENT_OCCUPATION"
                ],
                "agent_origin": [
                    "AGENT_ORIGIN"
                ],
                "agent_ready": [
                    "AGENT_READY"
                ],
                "agent_real": [
                    "AGENT_REAL"
                ],
                "agent_residence": [
                    "AGENT_RESIDENCE"
                ],
                "agent_right": [
                    "AGENT_RIGHT"
                ],
                "confirmation_yes": [
                    "CONFIRMATION_YES"
                ],
                "agent_sure": [
                    "AGENT_SURE"
                ],
                "agent_talk_to_me": [
                    "AGENT_TALK_TO_ME"
                ],
                "agent_there": [
                    "AGENT_THERE"
                ],
                "appraisal_bad": [
                    "APPRAISAL_BAD"
                ],
                "appraisal_good": [
                    "APPRAISAL_GOOD"
                ],
                "appraisal_no_problem": [
                    "APPRAISAL_NO_PROBLEM"
                ],
                "appraisal_thank_you": [
                    "APPRAISAL_THANK_YOU"
                ],
                "appraisal_welcome": [
                    "APPRAISAL_WELCOME"
                ],
                "appraisal_well_done": [
                    "APPRAISAL_WELL_DONE"
                ],
                "confirmation_cancel": [
                    "CONFIRMATION_CANCEL"
                ],
                "confirmation_no": [
                    "CONFIRMATION_NO"
                ],
                "dialog_hold_on": [
                    "DIALOG_HOLD_ON"
                ],
                "dialog_hug": [
                    "DIALOG_HUG"
                ],
                "dialog_i_do_not_care": [
                    "DIALOG_I_DO_NOT_CARE"
                ],
                "dialog_sorry": [
                    "DIALOG_SORRY"
                ],
                "dialog_what_do_you_mean": [
                    "DIALOG_WHAT_DO_YOU_MEAN"
                ],
                "dialog_wrong": [
                    "DIALOG_WRONG"
                ],
                "emotions_ha_ha": [
                    "EMOTIONS_HA_HA"
                ],
                "emotions_wow": [
                    "EMOTIONS_WOW"
                ],
                "greetings_bye": [
                    "GREETINGS_BYE"
                ],
                "greetings_goodevening": [
                    "GREETINGS_GOODEVENING"
                ],
                "greetings_goodmorning": [
                    "GREETINGS_GOODMORNING"
                ],
                "greetings_goodnight": [
                    "GREETINGS_GOODNIGHT"
                ],
                "greetings_hello": [
                    "GREETINGS_HELLO"
                ],
                "greetings_how_are_you": [
                    "GREETINGS_HOW_ARE_YOU"
                ],
                "greetings_nice_to_meet_you": [
                    "GREETINGS_NICE_TO_MEET_YOU"
                ],
                "greetings_nice_to_see_you": [
                    "GREETINGS_NICE_TO_SEE_YOU"
                ],
                "greetings_nice_to_talk_to_you": [
                    "GREETINGS_NICE_TO_TALK_TO_YOU"
                ],
                "greetings_whatsup": [
                    "GREETINGS_WHATSUP"
                ],
                "user_angry": [
                    "USER_ANGRY"
                ],
                "user_back": [
                    "USER_BACK"
                ],
                "user_bored": [
                    "USER_BORED"
                ],
                "user_busy": [
                    "USER_BUSY"
                ],
                "user_can_not_sleep": [
                    "USER_CAN_NOT_SLEEP"
                ],
                "user_does_not_want_to_talk": [
                    "USER_DOES_NOT_WANT_TO_TALK"
                ],
                "user_excited": [
                    "USER_EXCITED"
                ],
                "user_going_to_bed": [
                    "USER_GOING_TO_BED"
                ],
                "user_good": [
                    "USER_GOOD"
                ],
                "user_happy": [
                    "USER_HAPPY"
                ],
                "user_has_birthday": [
                    "USER_HAS_BIRTHDAY"
                ],
                "user_here": [
                    "USER_HERE"
                ],
                "user_joking": [
                    "USER_JOKING"
                ],
                "user_likes_agent": [
                    "USER_LIKES_AGENT"
                ],
                "user_lonely": [
                    "USER_LONELY"
                ],
                "user_looks_like": [
                    "USER_LOOKS_LIKE"
                ],
                "user_loves_agent": [
                    "USER_LOVES_AGENT"
                ],
                "user_misses_agent": [
                    "USER_MISSES_AGENT"
                ],
                "user_needs_advice": [
                    "USER_NEEDS_ADVICE"
                ],
                "user_sad": [
                    "USER_SAD"
                ],
                "user_sleepy": [
                    "USER_SLEEPY"
                ],
                "user_testing_agent": [
                    "USER_TESTING_AGENT"
                ],
                "user_tired": [
                    "USER_TIRED"
                ],
                "user_waits": [
                    "USER_WAITS"
                ],
                "user_wants_to_see_agent_again": [
                    "USER_WANTS_TO_SEE_AGENT_AGAIN"
                ],
                "user_wants_to_talk": [
                    "USER_WANTS_TO_TALK"
                ],
                "user_will_be_back": [
                    "USER_WILL_BE_BACK"
                ]
            }
        },
        "smp2017_task1": {
            "version_0": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "calc": [
                    "calc"
                ],
                "chat": [
                    "chat"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "datetime": [
                    "datetime"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "map": [
                    "map"
                ],
                "match": [
                    "match"
                ],
                "message": [
                    "message"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "schedule": [
                    "schedule"
                ],
                "stock": [
                    "stock"
                ],
                "telephone": [
                    "telephone"
                ],
                "train": [
                    "train"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ]
            },
            "version_1": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "calc": [
                    "calc"
                ],
                "chat": [
                    "chat"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "datetime": [
                    "datetime"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "map": [
                    "map"
                ],
                "match": [
                    "match"
                ],
                "message": [
                    "message"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "schedule": [
                    "schedule"
                ],
                "stock": [
                    "stock"
                ],
                "telephone": [
                    "telephone"
                ],
                "train": [
                    "train"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ]
            },
            "version_2": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "calc": [
                    "Calc"
                ],
                "chat": [
                    "Chat"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "datetime": [
                    "Datetime"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "map": [
                    "Map"
                ],
                "match": [
                    "Match"
                ],
                "message": [
                    "Message"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "schedule": [
                    "Schedule"
                ],
                "stock": [
                    "Stock"
                ],
                "telephone": [
                    "Telephone"
                ],
                "train": [
                    "Train"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ]
            },
            "version_3": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "calc": [
                    "Calc"
                ],
                "chat": [
                    "Chat"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "datetime": [
                    "Datetime"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "map": [
                    "Map"
                ],
                "match": [
                    "Match"
                ],
                "message": [
                    "Message"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "schedule": [
                    "Schedule"
                ],
                "stock": [
                    "Stock"
                ],
                "telephone": [
                    "Telephone"
                ],
                "train": [
                    "Train"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ]
            },
            "version_4": {
                "app": [
                    "APP"
                ],
                "bus": [
                    "BUS"
                ],
                "calc": [
                    "CALC"
                ],
                "chat": [
                    "CHAT"
                ],
                "cinemas": [
                    "CINEMAS"
                ],
                "contacts": [
                    "CONTACTS"
                ],
                "cookbook": [
                    "COOKBOOK"
                ],
                "datetime": [
                    "DATETIME"
                ],
                "email": [
                    "EMAIL"
                ],
                "epg": [
                    "EPG"
                ],
                "flight": [
                    "FLIGHT"
                ],
                "health": [
                    "HEALTH"
                ],
                "lottery": [
                    "LOTTERY"
                ],
                "map": [
                    "MAP"
                ],
                "match": [
                    "MATCH"
                ],
                "message": [
                    "MESSAGE"
                ],
                "music": [
                    "MUSIC"
                ],
                "news": [
                    "NEWS"
                ],
                "novel": [
                    "NOVEL"
                ],
                "poetry": [
                    "POETRY"
                ],
                "radio": [
                    "RADIO"
                ],
                "riddle": [
                    "RIDDLE"
                ],
                "schedule": [
                    "SCHEDULE"
                ],
                "stock": [
                    "STOCK"
                ],
                "telephone": [
                    "TELEPHONE"
                ],
                "train": [
                    "TRAIN"
                ],
                "translation": [
                    "TRANSLATION"
                ],
                "tvchannel": [
                    "TVCHANNEL"
                ],
                "video": [
                    "VIDEO"
                ],
                "weather": [
                    "WEATHER"
                ],
                "website": [
                    "WEBSITE"
                ]
            }
        },
        "smp2019_task1_domain": {
            "version_0": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "map": [
                    "map"
                ],
                "train": [
                    "train"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "telephone": [
                    "telephone"
                ],
                "message": [
                    "message"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "match": [
                    "match"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "stock": [
                    "stock"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ],
                "joke": [
                    "joke"
                ],
                "story": [
                    "story"
                ]
            },
            "version_1": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "map": [
                    "map"
                ],
                "train": [
                    "train"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "telephone": [
                    "telephone"
                ],
                "message": [
                    "message"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "match": [
                    "match"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "stock": [
                    "stock"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ],
                "joke": [
                    "joke"
                ],
                "story": [
                    "story"
                ]
            },
            "version_2": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "map": [
                    "Map"
                ],
                "train": [
                    "Train"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "telephone": [
                    "Telephone"
                ],
                "message": [
                    "Message"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "match": [
                    "Match"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "stock": [
                    "Stock"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ],
                "joke": [
                    "Joke"
                ],
                "story": [
                    "Story"
                ]
            },
            "version_3": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "map": [
                    "Map"
                ],
                "train": [
                    "Train"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "telephone": [
                    "Telephone"
                ],
                "message": [
                    "Message"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "match": [
                    "Match"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "stock": [
                    "Stock"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ],
                "joke": [
                    "Joke"
                ],
                "story": [
                    "Story"
                ]
            },
            "version_4": {
                "app": [
                    "APP"
                ],
                "bus": [
                    "BUS"
                ],
                "map": [
                    "MAP"
                ],
                "train": [
                    "TRAIN"
                ],
                "cinemas": [
                    "CINEMAS"
                ],
                "telephone": [
                    "TELEPHONE"
                ],
                "message": [
                    "MESSAGE"
                ],
                "contacts": [
                    "CONTACTS"
                ],
                "cookbook": [
                    "COOKBOOK"
                ],
                "email": [
                    "EMAIL"
                ],
                "epg": [
                    "EPG"
                ],
                "flight": [
                    "FLIGHT"
                ],
                "health": [
                    "HEALTH"
                ],
                "lottery": [
                    "LOTTERY"
                ],
                "match": [
                    "MATCH"
                ],
                "music": [
                    "MUSIC"
                ],
                "news": [
                    "NEWS"
                ],
                "novel": [
                    "NOVEL"
                ],
                "poetry": [
                    "POETRY"
                ],
                "radio": [
                    "RADIO"
                ],
                "riddle": [
                    "RIDDLE"
                ],
                "stock": [
                    "STOCK"
                ],
                "translation": [
                    "TRANSLATION"
                ],
                "tvchannel": [
                    "TVCHANNEL"
                ],
                "video": [
                    "VIDEO"
                ],
                "weather": [
                    "WEATHER"
                ],
                "website": [
                    "WEBSITE"
                ],
                "joke": [
                    "JOKE"
                ],
                "story": [
                    "STORY"
                ]
            }
        },
        "smp2019_task1_intent": {
            "version_0": {
                "launch": [
                    "launch"
                ],
                "query": [
                    "query"
                ],
                "route": [
                    "route"
                ],
                "sendcontacts": [
                    "send_contacts"
                ],
                "send": [
                    "send"
                ],
                "reply": [
                    "reply"
                ],
                "replay_all": [
                    "replay_all"
                ],
                "look_back": [
                    "look_back"
                ],
                "number_query": [
                    "number_query"
                ],
                "position": [
                    "position"
                ],
                "play": [
                    "play"
                ],
                "default": [
                    "default"
                ],
                "dial": [
                    "dial"
                ],
                "translation": [
                    "translation"
                ],
                "open": [
                    "open"
                ],
                "create": [
                    "create"
                ],
                "forward": [
                    "forward"
                ],
                "view": [
                    "view"
                ],
                "search": [
                    "search"
                ],
                "riserate_query": [
                    "riserate_query"
                ],
                "download": [
                    "download"
                ],
                "date_query": [
                    "date_query"
                ],
                "closeprice_query": [
                    "close_price_query"
                ]
            },
            "version_1": {
                "launch": [
                    "launch"
                ],
                "query": [
                    "query"
                ],
                "route": [
                    "route"
                ],
                "sendcontacts": [
                    "send contacts"
                ],
                "send": [
                    "send"
                ],
                "reply": [
                    "reply"
                ],
                "replay_all": [
                    "replay all"
                ],
                "look_back": [
                    "look back"
                ],
                "number_query": [
                    "number query"
                ],
                "position": [
                    "position"
                ],
                "play": [
                    "play"
                ],
                "default": [
                    "default"
                ],
                "dial": [
                    "dial"
                ],
                "translation": [
                    "translation"
                ],
                "open": [
                    "open"
                ],
                "create": [
                    "create"
                ],
                "forward": [
                    "forward"
                ],
                "view": [
                    "view"
                ],
                "search": [
                    "search"
                ],
                "riserate_query": [
                    "riserate query"
                ],
                "download": [
                    "download"
                ],
                "date_query": [
                    "date query"
                ],
                "closeprice_query": [
                    "close price query"
                ]
            },
            "version_2": {
                "launch": [
                    "Launch"
                ],
                "query": [
                    "Query"
                ],
                "route": [
                    "Route"
                ],
                "sendcontacts": [
                    "Send Contacts"
                ],
                "send": [
                    "Send"
                ],
                "reply": [
                    "Reply"
                ],
                "replay_all": [
                    "Replay All"
                ],
                "look_back": [
                    "Look Back"
                ],
                "number_query": [
                    "Number Query"
                ],
                "position": [
                    "Position"
                ],
                "play": [
                    "Play"
                ],
                "default": [
                    "Default"
                ],
                "dial": [
                    "Dial"
                ],
                "translation": [
                    "Translation"
                ],
                "open": [
                    "Open"
                ],
                "create": [
                    "Create"
                ],
                "forward": [
                    "Forward"
                ],
                "view": [
                    "View"
                ],
                "search": [
                    "Search"
                ],
                "riserate_query": [
                    "Riserate Query"
                ],
                "download": [
                    "Download"
                ],
                "date_query": [
                    "Date Query"
                ],
                "closeprice_query": [
                    "Close Price Query"
                ]
            },
            "version_3": {
                "launch": [
                    "Launch"
                ],
                "query": [
                    "Query"
                ],
                "route": [
                    "Route"
                ],
                "sendcontacts": [
                    "SendContacts"
                ],
                "send": [
                    "Send"
                ],
                "reply": [
                    "Reply"
                ],
                "replay_all": [
                    "ReplayAll"
                ],
                "look_back": [
                    "LookBack"
                ],
                "number_query": [
                    "NumberQuery"
                ],
                "position": [
                    "Position"
                ],
                "play": [
                    "Play"
                ],
                "default": [
                    "Default"
                ],
                "dial": [
                    "Dial"
                ],
                "translation": [
                    "Translation"
                ],
                "open": [
                    "Open"
                ],
                "create": [
                    "Create"
                ],
                "forward": [
                    "Forward"
                ],
                "view": [
                    "View"
                ],
                "search": [
                    "Search"
                ],
                "riserate_query": [
                    "RiserateQuery"
                ],
                "download": [
                    "Download"
                ],
                "date_query": [
                    "DateQuery"
                ],
                "closeprice_query": [
                    "ClosePriceQuery"
                ]
            },
            "version_4": {
                "launch": [
                    "LAUNCH"
                ],
                "query": [
                    "QUERY"
                ],
                "route": [
                    "ROUTE"
                ],
                "sendcontacts": [
                    "SEND_CONTACTS"
                ],
                "send": [
                    "SEND"
                ],
                "reply": [
                    "REPLY"
                ],
                "replay_all": [
                    "REPLAY_ALL"
                ],
                "look_back": [
                    "LOOK_BACK"
                ],
                "number_query": [
                    "NUMBER_QUERY"
                ],
                "position": [
                    "POSITION"
                ],
                "play": [
                    "PLAY"
                ],
                "default": [
                    "DEFAULT"
                ],
                "dial": [
                    "DIAL"
                ],
                "translation": [
                    "TRANSLATION"
                ],
                "open": [
                    "OPEN"
                ],
                "create": [
                    "CREATE"
                ],
                "forward": [
                    "FORWARD"
                ],
                "view": [
                    "VIEW"
                ],
                "search": [
                    "SEARCH"
                ],
                "riserate_query": [
                    "RISERATE_QUERY"
                ],
                "download": [
                    "DOWNLOAD"
                ],
                "date_query": [
                    "DATE_QUERY"
                ],
                "closeprice_query": [
                    "CLOSE_PRICE_QUERY"
                ]
            }
        },
        "snips_built_in_intents": {"version_0": {
            "ComparePlaces": [
                "ComparePlaces"
            ],
            "RequestRide": [
                "RequestRide"
            ],
            "GetWeather": [
                "GetWeather"
            ],
            "SearchPlace": [
                "SearchPlace"
            ],
            "GetPlaceDetails": [
                "GetPlaceDetails"
            ],
            "ShareCurrentLocation": [
                "ShareCurrentLocation"
            ],
            "GetTrafficInformation": [
                "GetTrafficInformation"
            ],
            "BookRestaurant": [
                "BookRestaurant"
            ],
            "GetDirections": [
                "GetDirections"
            ],
            "ShareETA": [
                "ShareETA"
            ]
        }},
        "star_wars": {
            "version_0": {
                "greeting": ["greeting"],
                "goodbye": ["goodbye"],
                "thanks": ["thanks"],
                "tasks": ["tasks"],
                "alive": ["alive"],
                "Menu": ["menu"],
                "hepl": ["help"],
                "mission": ["mission"],
                "jedi": ["jedi"],
                "sith": ["sith"],
                "bounti hounter": ["bounti hounter"],
                "funny": ["funny"],
                "about me": ["about me"],
                "creator": ["creator"],
                "myself": ["myself"],
                "stories": ["stories"],

            }
        },
        "suicide_intent": {
            "version_0": {
                "happy intent": [
                    "happy_intent"
                ],
                "sad intent": [
                    "sad_intent"
                ],
                "normal intent": [
                    "normal_intent"
                ],
                "suicidal intent": [
                    "suicidal_intent"
                ]
            },
            "version_1": {
                "happy intent": [
                    "happy intent"
                ],
                "sad intent": [
                    "sad intent"
                ],
                "normal intent": [
                    "normal intent"
                ],
                "suicidal intent": [
                    "suicidal intent"
                ]
            },
            "version_2": {
                "happy intent": [
                    "Happy Intent"
                ],
                "sad intent": [
                    "Sad Intent"
                ],
                "normal intent": [
                    "Normal Intent"
                ],
                "suicidal intent": [
                    "Suicidal Intent"
                ]
            },
            "version_3": {
                "happy intent": [
                    "HappyIntent"
                ],
                "sad intent": [
                    "SadIntent"
                ],
                "normal intent": [
                    "NormalIntent"
                ],
                "suicidal intent": [
                    "SuicidalIntent"
                ]
            },
            "version_4": {
                "happy intent": [
                    "HAPPY INTENT"
                ],
                "sad intent": [
                    "SAD INTENT"
                ],
                "normal intent": [
                    "NORMAL INTENT"
                ],
                "suicidal intent": [
                    "SUICIDAL INTENT"
                ]
            }
        },
        "telemarketing_intent_en": {"version_0": {
            "无关领域": ["outside the field", "out domain"],
            "肯定(yes)": ["yes"],
            "否定(not)": ["not"],
            "我在": ["I'm here", "I am listening", "I'm listening"],
            "实体(数值)": ["number", "contain number"],
            "答时间": ["contain data or time"],
            "听不清楚": ["I can not hear you"],
            "别担心": ["don't worry", "do not worry", "take it easy", "take easy"],
            "肯定(no problem)": ["no problem"],
            "资金困难": ["financial difficulties", "short money"],
            "招呼用语": ["greeting"],
            "肯定(go ahead)": ["go ahead"],
            "语音信箱": ["voicemail"],
            "否定(no)": ["no"],
            "查自我介绍": ["check self-introduction", "query self-introduction"],
            "会按时处理": ["will be processed on time", "will handle it"],
            "污言秽语": ["curse", "abuse", "vituperation", "snap", "damn"],
            "否定(dont want)": ["don't want", "don't wanna"],
            "赞美用语": ["praise", "laud"],
            "实体(人名)": ["name", "contain name", "contains names"],
            "否定(dont know)": ["don't know", "do not know"],
            "礼貌用语": ["polite", "polite words", "polite expressions"],
            "做自我介绍": ["introducing himself", "he is introducing himself"],
            "肯定(ok)": ["ok", "OK"],
            "否定(not interested)": ["not interested", "no interest"],
            "暴力敏感": ["violent", "contain violent"],
            "问意图": ["ask about intention", "ask about intent"],
            "答地址": ["address", "contain address"],
            "肯定(alright)": ["alright"],
            "肯定(sure)": ["sure"],
            "转账完成": ["transfer completed"],
            "查物品信息": ["check item information", "check item info", "check info"],
            "疑问(地址)": ["query address", "check address", "ask address"],
            "是否机器人": ["are you robot", "robot"],
            "投诉警告": ["complaint warning", "complaint"],
            "打错电话": ["wrong number", "called the wrong person", "mixed up the numbers"],
            "肯定(I see)": ["I see"],
            "语气词": ["modal particles", "interjection"],
            "要求复述": ["ask for a repeat", "can you speak again"],
            "不信任": ["distrust", "mistrust", "doubt", "suspect"],
            "未能理解": ["don't understand", "not understand", "not understood"],
            "价格太高": ["expensive", "price is too high"],
            "请等一等": ["please wait", "wait a minute"],
            "请求谅解": ["ask for understanding", "apologize", "make an apology", "excuse"],
            "疑问": ["inquiry"],
            "结束用语": ["farewell phrase", "closing phrase"],
            "肯定(interested)": ["interested"],
            "请讲": ["please speak"],
            "疑问(时间)": ["ask date or time", "ask time", "query date or time", "query time"],
            "疑问(姓名)": ["ask for name", "ask name", "query name"],
            "骚扰电话": ["harassing phone calls", "harassing", "bothering"],
            "肯定(agree)": ["agree"],
            "否定(not enough)": ["not enough"],
            "提出建议": ["make a suggestion"],
            "查详细信息": ["check details"],
            "肯定(yes I do)": ["yes I do"],
            "疑问(数值)": ["check number"],
            "考虑一下": ["think about it", "think twice"],
            "消极情绪": ["negative emotions"],
            "遭遇不幸": ["misfortune", "bad luck", "accident"],
            "用户正忙": ["busy"],
            "肯定(correct)": ["correct"],
            "号码来源": ["number source", "where did you get my number"],
            "许下愿望": ["make a wish"],
            "查收费方式": ["check the charging", "charging"],
            "肯定(need)": ["need"],
            "已经拥有": ["already have"],
            "疑问(whats up)": ["whats up"],
            "色情敏感": ["porn", "pornography", "obscene", "harlot"],
            "答状态": ["answered a status"],
            "已完成": ["finished"],
            "你还在吗": ["are you there"],
            "否定句": ["negative sentences"],
            "否定(not sure)": ["not sure"],
            "听我说话": ["listen to me"],
            "太多太高": ["too much or too high"],
            "祝福用语": ["phrases of blessing", "blessing phrases"],
            "疑问(金额)": ["how much"],
            "解释原因": ["explain the reason"],
            "否定(nothing)": ["nothing"],
            "鼓励用语": ["encouragement", "encourage"],
            "疑问(长度)": ["check length"],
            "加快速度": ["boost", "hurry up", "make haste"],
            "重复一次": ["repeat"],
            "肯定(i know)": ["I know"],
            "无所谓": ["It doesn't matter", "not to matter", "be indifferent"],
            "否定(not need)": ["not need"],
            "否定(cant)": ["can't", "can not"],
            "肯定(姓名)": ["confirm name"],
            "否定(refuse)": ["refuse"],
            "改天再谈": ["let's talk another day"],
            "肯定(understand)": ["understand", "do understand"],
            "太少太低": ["too little or too low"],
            "查公司介绍": ["check company introduction", "check company information", "check company info"],
            "资金充足": ["sufficient funds", "have enough money"],
            "政治敏感": ["involving politics"],
            "贫穷词汇": ["poverty related"],
            "否定(not available)": ["not available"],
            "质疑来电号码": ["question the caller number", "suspicious caller number"],
            "查操作流程": ["check the operation process", "check the process"],
            "否定(wrong)": ["wrong"],
            "正在进行": ["ongoing"],
            "肯定(why not)": ["why not"],
            "陈述(ready)": ["ready"],
            "答非所问": ["not answering the question", "give an irrelevant answer"],
            "太迟了": ["too late"],
            "否定(dont have)": ["don't have"],
            "肯定(i can)": ["I can"],
            "肯定(i want)": ["I want"],
            "否定(no time)": ["no time"],
            "陈述(forget)": ["forget"],
        }},
        "telemarketing_intent_cn": {"version_0": {
            "无关领域": ["无关领域"],
            "否定(不需要)": ["否定(不需要)", "不需要"],
            "否定(不用了)": ["否定(不用了)", "不用了"],
            "肯定(好的)": ["肯定(好的)", "好的"],
            "否定(没有)": ["否定(没有)", "没有"],
            "答数值": ["答数值", "数值"],
            "答时间": ["答时间", "时间"],
            "查收费方式": ["查收费方式", "查收费方式"],
            "语气词": ["语气词"],
            "否定答复": ["否定答复", "否定答复"],
            "不信任": ["不信任", "不信任"],
            "答非所问": ["答非所问"],
            "污言秽语": ["污言秽语", "脏话", "骂人"],
            "疑问(数值)": ["疑问(数值)", "问数值"],
            "肯定(知道了)": ["肯定(知道了)", "知道了"],
            "肯定(正确)": ["肯定(正确)", "正确"],
            "资金困难": ["资金困难", "缺钱"],
            "礼貌用语": ["礼貌用语"],
            "查联系方式": ["查联系方式"],
            "查操作流程": ["查操作流程"],
            "是否机器人": ["是否机器人"],
            "招呼用语": ["招呼用语"],
            "用户正忙": ["用户正忙"],
            "肯定(是的)": ["肯定(是的)", "是的"],
            "肯定(可以)": ["肯定(可以)", "可以"],
            "查自我介绍": ["查自我介绍"],
            "肯定(嗯嗯)": ["肯定(嗯嗯)", "嗯嗯"],
            "肯定(有)": ["肯定(有)", "有"],
            "政治敏感": ["政治敏感"],
            "否定(不方便)": ["否定(不方便)", "不方便"],
            "你还在吗": ["你还在吗"],
            "肯定(需要)": ["肯定(需要)", "需要"],
            "疑问(时间)": ["疑问(时间)", "问时间"],
            "否定(不知道)": ["否定(不知道)", "不知道"],
            "疑问(地址)": ["疑问(地址)", "问地址"],
            "骚扰电话": ["骚扰电话"],
            "实体(地址)": ["实体(地址)", "地址"],
            "未能理解": ["未能理解"],
            "查公司介绍": ["查公司介绍"],
            "听不清楚": ["听不清楚"],
            "实体(人名)": ["实体(人名)", "人名"],
            "语音信箱": ["语音信箱"],
            "要求复述": ["要求复述"],
            "否定(不是)": ["否定(不是)", "不是"],
            "请讲": ["请讲"],
            "问意图": ["问意图"],
            "结束用语": ["结束用语"],
            "否定(不可以)": ["否定(不可以)", "不可以"],
            "肯定(好了)": ["肯定(好了)", "好了"],
            "请等一等": ["请等一等"],
            "查物品信息": ["查物品信息"],
            "祝福用语": ["祝福用语"],
            "否定(没时间)": ["否定(没时间)", "没时间"],
            "否定(不想要)": ["否定(不想要)", "不想要"],
            "会按时处理": ["会按时处理"],
            "查详细信息": ["查详细信息"],
            "否定(错误)": ["否定(错误)", "错误", "错了"],
            "否定(没兴趣)": ["否定(没兴趣)"],
            "我在": ["我在"],
            "号码来源": ["号码来源"],
            "投诉警告": ["投诉警告"],
            "请求谅解": ["请求谅解"],
            "赞美用语": ["赞美用语"],
            "改天再谈": ["改天再谈"],
            "已完成": ["已完成"],
            "做自我介绍": ["做自我介绍"],
            "价格太高": ["价格太高"],
            "请讲重点": ["请讲重点"],
            "听我说话": ["听我说话"],
            "肯定(没问题)": ["肯定(没问题)", "没问题"],
            "转人工客服": ["转人工客服"],
            "遭遇不幸": ["遭遇不幸"],
            "质疑来电号码": ["质疑来电号码"],
            "否定(取消)": ["否定(取消)", "取消"],
            "打错电话": ["打错电话"],
            "否定(不清楚)": ["否定(不清楚)", "不清楚"],
            "疑问(时长)": ["疑问(时长)", "问时长"],
            "资金充足": ["资金充足"],
            "祝贺用语": ["祝贺用语"],
            "已经购买": ["已经购买"],
            "查优惠政策": ["查优惠政策"],
            "肯定答复": ["肯定答复"],
            "会帮忙转告": ["会帮忙转告"],
            "疑问(姓名)": ["疑问(姓名)", "问姓名"],
            "时间推迟": ["时间推迟"],
            "考虑一下": ["考虑一下"],
            "疑问(能否)": ["疑问(能否)", "能否", "能不能"],
            "实体(时长)": ["实体(时长)", "时长"],
            "答状态": ["答状态"],
            "重复一次": ["重复一次"],
            "实体(组织)": ["实体(组织)", "组织"],
            "加快速度": ["加快速度"],
            "无所谓": ["无所谓"],
            "信号不好": ["信号不好"],
            "已经记录": ["已经记录"],
            "质疑隐私安全": ["质疑隐私安全"],
            "不是本人": ["不是本人"],
            "否定(不能)": ["否定(不能)", "不能"],
            "太少太低": ["太少太低"]
        }},
        "vira_intents": {
            "version_0": {
                "COVID-19 is not as dangerous as they say": [
                    "COVID-19 is not as dangerous as they say"
                ],
                "Do I need to continue safety measures after getting the vaccine?": [
                    "Do I need to continue safety measures after getting the vaccine?"
                ],
                "How long until I will be protected after taking the vaccine?": [
                    "How long until I will be protected after taking the vaccine?"
                ],
                "How many people already got the vaccine?": [
                    "How many people already got the vaccine?"
                ],
                "I am afraid the vaccine will change my DNA": [
                    "I am afraid the vaccine will change my DNA"
                ],
                "I am concerned getting the vaccine because I have a pre-existing condition": [
                    "I am concerned getting the vaccine because I have a pre-existing condition"
                ],
                "I am concerned I will be a guinea pig": [
                    "I am concerned I will be a guinea pig"
                ],
                "I'm concerned the vaccine will make me sick.": [
                    "I'm concerned the vaccine will make me sick."
                ],
                "I am not sure if I can trust the government": [
                    "I am not sure if I can trust the government"
                ],
                "I am young and healthy so I don't think I should vaccinate": [
                    "I am young and healthy so I don't think I should vaccinate"
                ],
                "I distrust this vaccine": [
                    "I distrust this vaccine"
                ],
                "How much will I have to pay for the vaccine": [
                    "How much will I have to pay for the vaccine"
                ],
                "I don't think the vaccine is necessary": [
                    "I don't think the vaccine is necessary"
                ],
                "I don't trust the companies producing the vaccines": [
                    "I don't trust the companies producing the vaccines"
                ],
                "I don't want my children to get the vaccine": [
                    "I don't want my children to get the vaccine"
                ],
                "I think the vaccine was not tested on my community": [
                    "I think the vaccine was not tested on my community"
                ],
                "I'm not sure it is effective enough": [
                    "I'm not sure it is effective enough"
                ],
                "I'm waiting to see how it affects others": [
                    "I'm waiting to see how it affects others"
                ],
                "COVID vaccines can be worse than the disease itself": [
                    "COVID vaccines can be worse than the disease itself"
                ],
                "Long term side-effects were not researched enough": [
                    "Long term side-effects were not researched enough"
                ],
                "Are regular safety measures enough to stay healthy?": [
                    "Are regular safety measures enough to stay healthy?"
                ],
                "Should people that had COVID get the vaccine?": [
                    "Should people that had COVID get the vaccine?"
                ],
                "Side effects and adverse reactions worry me": [
                    "Side effects and adverse reactions worry me"
                ],
                "The COVID vaccine is not safe": [
                    "The COVID vaccine is not safe"
                ],
                "The vaccine should not be mandatory": [
                    "The vaccine should not be mandatory"
                ],
                "Do vaccines work against the mutated strains of COVID-19?": [
                    "Do vaccines work against the mutated strains of COVID-19?"
                ],
                "They will put a chip/microchip to manipulate me": [
                    "They will put a chip/microchip to manipulate me"
                ],
                "What can this chatbot do?": [
                    "What can this chatbot do?"
                ],
                "What is in the vaccine?": [
                    "What is in the vaccine?"
                ],
                "Which one of the vaccines should I take?": [
                    "Which one of the vaccines should I take?"
                ],
                "Will I test positive after getting the vaccine?": [
                    "Will I test positive after getting the vaccine?"
                ],
                "Can other vaccines protect me from COVID-19?": [
                    "Can other vaccines protect me from COVID-19?"
                ],
                "Do I qualify for the vaccine?": [
                    "Do I qualify for the vaccine?"
                ],
                "I don't trust vaccines if they're from China or Russia": [
                    "I don't trust vaccines if they're from China or Russia"
                ],
                "Are the side effects worse for the second shot": [
                    "Are the side effects worse for the second shot"
                ],
                "Can I get a second dose even after a COVID exposure?": [
                    "Can I get a second dose even after a COVID exposure?"
                ],
                "Can I get other vaccines at the same time?": [
                    "Can I get other vaccines at the same time?"
                ],
                "Can I get the vaccine if I have allergies?": [
                    "Can I get the vaccine if I have allergies?"
                ],
                "Can I get the vaccine if I have had allergic reactions to vaccines before?": [
                    "Can I get the vaccine if I have had allergic reactions to vaccines before?"
                ],
                "Can I have the vaccine as a Catholic?": [
                    "Can I have the vaccine as a Catholic?"
                ],
                "Can I have the vaccine if I'm allergic to penicillin?": [
                    "Can I have the vaccine if I'm allergic to penicillin?"
                ],
                "Can I still get COVID even after being vaccinated?": [
                    "Can I still get COVID even after being vaccinated?"
                ],
                "Can you mix the vaccines?": [
                    "Can you mix the vaccines?"
                ],
                "COVID-19 vaccines cause brain inflammation": [
                    "COVID-19 vaccines cause brain inflammation"
                ],
                "Do the COVID-19 vaccines cause Bell's palsy?": [
                    "Do the COVID-19 vaccines cause Bell's palsy?"
                ],
                "Do the mRNA vaccines contain preservatives, like thimerosal?": [
                    "Do the mRNA vaccines contain preservatives, like thimerosal?"
                ],
                "Do the vaccines work in obese people?": [
                    "Do the vaccines work in obese people?"
                ],
                "Do you have to be tested for COVID before you vaccinated?": [
                    "Do you have to be tested for COVID before you vaccinated?"
                ],
                "Does the vaccine contain animal products?": [
                    "Does the vaccine contain animal products?"
                ],
                "Does the vaccine contain live COVID virus?": [
                    "Does the vaccine contain live COVID virus?"
                ],
                "Does the vaccine impact pregnancy?": [
                    "Does the vaccine impact pregnancy?"
                ],
                "Does the vaccine work if I do not experience any side effects?": [
                    "Does the vaccine work if I do not experience any side effects?"
                ],
                "How can I stay safe until I'm vaccinated?": [
                    "How can I stay safe until I'm vaccinated?"
                ],
                "How do I know I'm getting a legitimate, authorized vaccine?": [
                    "How do I know I'm getting a legitimate, authorized vaccine?"
                ],
                "How do I report an adverse reaction or side-effect": [
                    "How do I report an adverse reaction or side-effect"
                ],
                "How long do I have to wait between doses?": [
                    "How long do I have to wait between doses?"
                ],
                "How many doses do I need?": [
                    "How many doses do I need?"
                ],
                "How was the vaccine tested?": [
                    "How was the vaccine tested?"
                ],
                "I am concerned about getting the vaccine because of my medications.": [
                    "I am concerned about getting the vaccine because of my medications."
                ],
                "I don't want the v-safe app monitoring or tracking me": [
                    "I don't want the v-safe app monitoring or tracking me"
                ],
                "I don't want to share my personal information": [
                    "I don't want to share my personal information"
                ],
                "Is breastfeeding safe with the vaccine": [
                    "Is breastfeeding safe with the vaccine"
                ],
                "Is the Johnson & Johnson vaccine less effective than the others?": [
                    "Is the Johnson & Johnson vaccine less effective than the others?"
                ],
                "Is the vaccine halal?": [
                    "Is the vaccine halal?"
                ],
                "Is the vaccine Kosher?": [
                    "Is the vaccine Kosher?"
                ],
                "Is there vaccine safety monitoring?": [
                    "Is there vaccine safety monitoring?"
                ],
                "Other vaccines have caused long-term health problems": [
                    "Other vaccines have caused long-term health problems"
                ],
                "Should I get the COVID-19 vaccine if I am immunocompromised": [
                    "Should I get the COVID-19 vaccine if I am immunocompromised"
                ],
                "Should I get the vaccine if I've tested positive for antibodies?": [
                    "Should I get the vaccine if I've tested positive for antibodies?"
                ],
                "The vaccine includes fetal tissue or abortion by-products": [
                    "The vaccine includes fetal tissue or abortion by-products"
                ],
                "The vaccine was rushed": [
                    "The vaccine was rushed"
                ],
                "Vaccine side effects are not getting reported": [
                    "Vaccine side effects are not getting reported"
                ],
                "What does vaccine efficacy mean?": [
                    "What does vaccine efficacy mean?"
                ],
                "What if I still get infected even after receiving the vaccine?": [
                    "What if I still get infected even after receiving the vaccine?"
                ],
                "What if I've been treated with convalescent plasma?": [
                    "What if I've been treated with convalescent plasma?"
                ],
                "What if I've been treated with monoclonal antibodies?": [
                    "What if I've been treated with monoclonal antibodies?"
                ],
                "What is mRNA?": [
                    "What is mRNA?"
                ],
                "What is the difference between mRNA and viral vector vaccines?": [
                    "What is the difference between mRNA and viral vector vaccines?"
                ],
                "When can I go back to normal life?": [
                    "When can I go back to normal life?"
                ],
                "Why are there different vaccines?": [
                    "Why are there different vaccines?"
                ],
                "Why do I need the COVID vaccine if I don't get immunized for flu": [
                    "Why do I need the COVID vaccine if I don't get immunized for flu"
                ],
                "Why do we need the vaccine if we can wait for herd immunity?": [
                    "Why do we need the vaccine if we can wait for herd immunity?"
                ],
                "Why get vaccinated if I can still transmit the virus?": [
                    "Why get vaccinated if I can still transmit the virus?"
                ],
                "Will 1 dose of vaccine protect me?": [
                    "Will 1 dose of vaccine protect me?"
                ],
                "Can I take a pain reliever when I get vaccinated?": [
                    "Can I take a pain reliever when I get vaccinated?"
                ],
                "Will the vaccine benefit me?": [
                    "Will the vaccine benefit me?"
                ],
                "Will the vaccine make me sterile or infertile?": [
                    "Will the vaccine make me sterile or infertile?"
                ],
                "Can we change the vaccine quickly if the virus mutates?": [
                    "Can we change the vaccine quickly if the virus mutates?"
                ],
                "Can I get COVID-19 from the vaccine?": [
                    "Can I get COVID-19 from the vaccine?"
                ],
                "I am still experiencing COVID symptoms even after testing negative, should I still take the vaccine?": [
                    "I am still experiencing COVID symptoms even after testing negative, should I still take the vaccine?"
                ],
                "Can children get the vaccine?": [
                    "Can children get the vaccine?"
                ],
                "Can we choose which vaccine we want?": [
                    "Can we choose which vaccine we want?"
                ],
                "How long does the immunity from the vaccine last?": [
                    "How long does the immunity from the vaccine last?"
                ],
                "The mortality rate of COVID-19 is low, why should I get the vaccine?": [
                    "The mortality rate of COVID-19 is low, why should I get the vaccine?"
                ],
                "There are many reports of severe side effects or deaths from the vaccine": [
                    "There are many reports of severe side effects or deaths from the vaccine"
                ],
                "How can I get the vaccine?": [
                    "How can I get the vaccine?"
                ],
                "I am worried about blood clots as a result of the vaccine": [
                    "I am worried about blood clots as a result of the vaccine"
                ],
                "what is covid?": [
                    "what is covid?"
                ],
                "Who developed the vaccine?": [
                    "Who developed the vaccine?"
                ],
                "Which vaccines are available?": [
                    "Which vaccines are available?"
                ],
                "What are the side effect of the vaccine?": [
                    "What are the side effect of the vaccine?"
                ],
                "Can I meet in groups after I'm vaccinated?": [
                    "Can I meet in groups after I'm vaccinated?"
                ],
                "Is it safe to go to the gym indoors if I'm vaccinated?": [
                    "Is it safe to go to the gym indoors if I'm vaccinated?"
                ],
                "How do I protect myself indoors?": [
                    "How do I protect myself indoors?"
                ],
                "What are the effects of long COVID?": [
                    "What are the effects of long COVID?"
                ],
                "Do you need a social security number to get a COVID-19 vaccine?": [
                    "Do you need a social security number to get a COVID-19 vaccine?"
                ],
                "Do you need to be a U.S. citizen to get a COVID-19 vaccine?": [
                    "Do you need to be a U.S. citizen to get a COVID-19 vaccine?"
                ],
                "Is it okay for me to travel internationally if I'm vaccinated?": [
                    "Is it okay for me to travel internationally if I'm vaccinated?"
                ],
                "Can my kids go back to school without a vaccine?": [
                    "Can my kids go back to school without a vaccine?"
                ],
                "Will I need a booster shot?": [
                    "Will I need a booster shot?"
                ],
                "If I live with an immuno-compromised individual, do I still need to wear a mask outdoors if I'm vaccinated?": [
                    "If I live with an immuno-compromised individual, do I still need to wear a mask outdoors if I'm vaccinated?"
                ],
                "Does the vaccine prevent transmission?": [
                    "Does the vaccine prevent transmission?"
                ],
                "Why is AstraZeneca not approved in the USA?": [
                    "Why is AstraZeneca not approved in the USA?"
                ],
                "Do I need to change my masking and social distancing practices depending on which COVID-19 vaccine I got?": [
                    "Do I need to change my masking and social distancing practices depending on which COVID-19 vaccine I got?"
                ],
                "Does the Pfizer vaccine cause myocarditis?": [
                    "Does the Pfizer vaccine cause myocarditis?"
                ],
                "Does the Pfizer vaccine cause heart problems?": [
                    "Does the Pfizer vaccine cause heart problems?"
                ],
                "What can you tell me about COVID-19 vaccines?": [
                    "What can you tell me about COVID-19 vaccines?"
                ],
                "Are there medical contraindications to the vaccines?": [
                    "Are there medical contraindications to the vaccines?"
                ],
                "How many people died from COVID-19?": [
                    "How many people died from COVID-19?"
                ],
                "What about reports of abnormal periods due to the vaccine?": [
                    "What about reports of abnormal periods due to the vaccine?"
                ],
                "Do I need the vaccine?": [
                    "Do I need the vaccine?"
                ],
                "Tell me about the vaccine": [
                    "Tell me about the vaccine"
                ],
                "Is the Pfizer vaccine safe for young men?": [
                    "Is the Pfizer vaccine safe for young men?"
                ],
                "Will vaccination lead to more dangerous variants?": [
                    "Will vaccination lead to more dangerous variants?"
                ],
                "Is it safe for my baby to get the vaccine?": [
                    "Is it safe for my baby to get the vaccine?"
                ],
                "Did a volunteer in the Oxford trial die?": [
                    "Did a volunteer in the Oxford trial die?"
                ],
                "Can I get COVID-19 twice?": [
                    "Can I get COVID-19 twice?"
                ],
                "Are some vaccines safer for younger children than others?": [
                    "Are some vaccines safer for younger children than others?"
                ],
                "How long am I immune from COVID-19 if I had the virus?": [
                    "How long am I immune from COVID-19 if I had the virus?"
                ],
                "Are women more likely to get worse side effects than men?": [
                    "Are women more likely to get worse side effects than men?"
                ],
                "How do I convince my family and friends to get the COVID-19 vaccine?": [
                    "How do I convince my family and friends to get the COVID-19 vaccine?"
                ],
                "Why are COVID-19 vaccination rates slowing in the U.S.?": [
                    "Why are COVID-19 vaccination rates slowing in the U.S.?"
                ],
                "I'm going to get vaccinated": [
                    "I'm going to get vaccinated"
                ],
                "Is getting vaccinated painful?": [
                    "Is getting vaccinated painful?"
                ],
                "What do I do if I lose my COVID-19 vaccination card?": [
                    "What do I do if I lose my COVID-19 vaccination card?"
                ],
                "Can I get swollen lymph nodes from the vaccine?": [
                    "Can I get swollen lymph nodes from the vaccine?"
                ],
                "Can my newborn become immune to COVID-19 if I'm vaccinated?": [
                    "Can my newborn become immune to COVID-19 if I'm vaccinated?"
                ],
                "COVID-19 is over, why should I get the vaccine?": [
                    "COVID-19 is over, why should I get the vaccine?"
                ],
                "Did one woman die after getting the J&J vaccine?": [
                    "Did one woman die after getting the J&J vaccine?"
                ],
                "Do people become magnetic after getting vaccinated?": [
                    "Do people become magnetic after getting vaccinated?"
                ],
                "Does the vaccine contain eggs?": [
                    "Does the vaccine contain eggs?"
                ],
                "How is the COVID-19 vaccine different than others?": [
                    "How is the COVID-19 vaccine different than others?"
                ],
                "How soon after I've had COVID-19 can I get the vaccination?": [
                    "How soon after I've had COVID-19 can I get the vaccination?"
                ],
                "Is it safe for my teen to get the vaccine?": [
                    "Is it safe for my teen to get the vaccine?"
                ],
                "Is this Pfizer vaccine equally effective in kids as it is in adults?": [
                    "Is this Pfizer vaccine equally effective in kids as it is in adults?"
                ],
                "Were the COVID-19 vaccines tested on animals?": [
                    "Were the COVID-19 vaccines tested on animals?"
                ],
                "What are the side effects of the vaccine in children?": [
                    "What are the side effects of the vaccine in children?"
                ],
                "What is the delta variant?": [
                    "What is the delta variant?"
                ],
                "What is the J&J vaccine?": [
                    "What is the J&J vaccine?"
                ],
                "What is the Moderna vaccine?": [
                    "What is the Moderna vaccine?"
                ],
                "What is the Pfizer vaccine?": [
                    "What is the Pfizer vaccine?"
                ],
                "Where are we required to wear masks now?": [
                    "Where are we required to wear masks now?"
                ],
                "Who can get the Pfizer vaccine?": [
                    "Who can get the Pfizer vaccine?"
                ],
                "Who can I talk to about COVID-19 in person?": [
                    "Who can I talk to about COVID-19 in person?"
                ],
                "Why should I trust you?": [
                    "Why should I trust you?"
                ],
                "Will my child need my permission to get vaccinated?": [
                    "Will my child need my permission to get vaccinated?"
                ],
                "Will the US reach herd immunity?": [
                    "Will the US reach herd immunity?"
                ],
                "Will my child miss school when they get vaccinated?": [
                    "Will my child miss school when they get vaccinated?"
                ],
                "Is the vaccine FDA approved?": [
                    "Is the vaccine FDA approved?"
                ],
                "Why do vaccinated people need to wear a mask indoors?": [
                    "Why do vaccinated people need to wear a mask indoors?"
                ],
                "Do vaccinated people need to quarantine if exposed to COVID-19?": [
                    "Do vaccinated people need to quarantine if exposed to COVID-19?"
                ],
                "What is Ivermectin?": [
                    "What is Ivermectin?"
                ],
                "Does the Johnson and Johnson vaccine cause Rare Nerve Syndrome?": [
                    "Does the Johnson and Johnson vaccine cause Rare Nerve Syndrome?"
                ],
                "What is the difference between quarantine and isolation?": [
                    "What is the difference between quarantine and isolation?"
                ],
                "Does the COVID-19 vaccine cause autism?": [
                    "Does the COVID-19 vaccine cause autism?"
                ],
                "Does the vaccine cause impotence?": [
                    "Does the vaccine cause impotence?"
                ],
                "Who is required to get vaccinated under the federal vaccine mandate?": [
                    "Who is required to get vaccinated under the federal vaccine mandate?"
                ],
                "Is the Delta variant more dangerous for kids?": [
                    "Is the Delta variant more dangerous for kids?"
                ],
                "Will there be a booster shot for J&J and Moderna?": [
                    "Will there be a booster shot for J&J and Moderna?"
                ],
                "Is the booster the same as the original vaccine?": [
                    "Is the booster the same as the original vaccine?"
                ],
                "What are the side effects of booster shots?": [
                    "What are the side effects of booster shots?"
                ],
                "What is the difference between the third shot and a booster shot?": [
                    "What is the difference between the third shot and a booster shot?"
                ],
                "How common are vaccine side effects?": [
                    "How common are vaccine side effects?"
                ],
                "Why do my kids need a vaccine if they're unlikely to get sick with COVID-19?": [
                    "Why do my kids need a vaccine if they're unlikely to get sick with COVID-19?"
                ],
                "What happens if there is a COVID-19 case at my child's school?": [
                    "What happens if there is a COVID-19 case at my child's school?"
                ],
                "Are booster shot side effects worse than those from the second shot?": [
                    "Are booster shot side effects worse than those from the second shot?"
                ],
                "Is the booster shot dangerous?": [
                    "Is the booster shot dangerous?"
                ],
                "Can I get the vaccine if I have Multiple Sclerosis?": [
                    "Can I get the vaccine if I have Multiple Sclerosis?"
                ],
                "Do children receive the same dose of Pfizer as adults?": [
                    "Do children receive the same dose of Pfizer as adults?"
                ],
                "What is the Omicron variant?": [
                    "What is the Omicron variant?"
                ],
                "How effective is the vaccine against the Omicron variant?": [
                    "How effective is the vaccine against the Omicron variant?"
                ],
                "How can I get free masks?": [
                    "How can I get free masks?"
                ],
                "Are the rapid, at-home tests accurate?": [
                    "Are the rapid, at-home tests accurate?"
                ],
                "Does a COVID-19 vaccine booster protect me against the omicron variant?": [
                    "Does a COVID-19 vaccine booster protect me against the omicron variant?"
                ],
                "What is the new omicron variant (BA.2)?": [
                    "What is the new omicron variant (BA.2)?"
                ],
                "Is the fourth shot available in the US?": [
                    "Is the fourth shot available in the US?"
                ],
                "What mask should I be wearing?": [
                    "What mask should I be wearing?"
                ],
                "How do I request at-home tests for my family?": [
                    "How do I request at-home tests for my family?"
                ],
                "Will insurance cover costs of the tests requested?": [
                    "Will insurance cover costs of the tests requested?"
                ],
                "Does the COVID-19 vaccine protect me against the \"stealth variant\"?": [
                    "Does the COVID-19 vaccine protect me against the \"stealth variant\"?"
                ],
                "Does the COVID-19 vaccine cause heart attacks?": [
                    "Does the COVID-19 vaccine cause heart attacks?"
                ],
                "Does the COVID-19 vaccine affect white blood cells?": [
                    "Does the COVID-19 vaccine affect white blood cells?"
                ],
                "Have the COVID-19 vaccines completed clinical trials?": [
                    "Have the COVID-19 vaccines completed clinical trials?"
                ],
                "What is deltacron?": [
                    "What is deltacron?"
                ],
                "How do I find the COVID-19 Community levels of my county?": [
                    "How do I find the COVID-19 Community levels of my county?"
                ],
                "What is breakthrough infection?": [
                    "What is breakthrough infection?"
                ],
                "Does the COVID-19 vaccine cause tinnitus?": [
                    "Does the COVID-19 vaccine cause tinnitus?"
                ],
                "My kids get too many injections as it is": [
                    "My kids get too many injections as it is"
                ],
                "How many doses does my child under 5 need?": [
                    "How many doses does my child under 5 need?"
                ],
                "Kids can still spread COVID after getting vaccinated": [
                    "Kids can still spread COVID after getting vaccinated"
                ],
                "Is the vaccine effective for children under 5": [
                    "Is the vaccine effective for children under 5"
                ],
                "Do I need the second booster dose?": [
                    "Do I need the second booster dose?"
                ],
                "How is the Novavax vaccine different from the other vaccines?": [
                    "How is the Novavax vaccine different from the other vaccines?"
                ],
                "What is Paxlovid?": [
                    "What is Paxlovid?"
                ],
                "Are children under 5 eligible for a vaccine?": [
                    "Are children under 5 eligible for a vaccine?"
                ],
                "What is the Novavax vaccine?": [
                    "What is the Novavax vaccine?"
                ],
                "Was the vaccine tested in kids before authorization?": [
                    "Was the vaccine tested in kids before authorization?"
                ],
                "What are the long-term effects of the vaccine for my kids?": [
                    "What are the long-term effects of the vaccine for my kids?"
                ],
                "Can my child get the booster?": [
                    "Can my child get the booster?"
                ],
                "Is the vaccine safe for children under 5?": [
                    "Is the vaccine safe for children under 5?"
                ],
                "How do I explain the benefits of the vaccine to my school age children?": [
                    "How do I explain the benefits of the vaccine to my school age children?"
                ],
                "What are the side effects of the Novavax vaccine?": [
                    "What are the side effects of the Novavax vaccine?"
                ],
                "Can my infant or child get a Moderna vaccine?": [
                    "Can my infant or child get a Moderna vaccine?"
                ],
                "I prefer to wait and see how vaccines work for my child": [
                    "I prefer to wait and see how vaccines work for my child"
                ],
                "It's too experimental for my kids": [
                    "It's too experimental for my kids"
                ],
                "What does bivalent mean?": [
                    "What does bivalent mean?"
                ],
                "Were the new boosters tested?": [
                    "Were the new boosters tested?"
                ],
                "Why didn't the new booster undergo clinical trials?": [
                    "Why didn't the new booster undergo clinical trials?"
                ],
                "Do I need another booster?": [
                    "Do I need another booster?"
                ],
                "How do the new boosters work?": [
                    "How do the new boosters work?"
                ],
                "How many boosters can I get?": [
                    "How many boosters can I get?"
                ],
                "Will the old boosters still be available?": [
                    "Will the old boosters still be available?"
                ]
            }
        },

    }


class DatasetLabels(object):
    label_map = {
        "a_intent": {
            "version_0": {
                "Travel-Query": [
                    "Travel-Query"
                ],
                "Music-Play": [
                    "Music-Play"
                ],
                "FilmTele-Play": [
                    "FilmTele-Play"
                ],
                "Video-Play": [
                    "Video-Play"
                ],
                "Radio-Listen": [
                    "Radio-Listen"
                ],
                "HomeAppliance-Control": [
                    "HomeAppliance-Control"
                ],
                "Weather-Query": [
                    "Weather-Query"
                ],
                "Alarm-Update": [
                    "Alarm-Update"
                ],
                "Calendar-Query": [
                    "Calendar-Query"
                ],
                "TVProgram-Play": [
                    "TVProgram-Play"
                ],
                "Audio-Play": [
                    "Audio-Play"
                ],
                "Other": [
                    "Other"
                ]
            },
            "version_1": {
                "Travel-Query": [
                    "Travel Query"
                ],
                "Music-Play": [
                    "Music Play"
                ],
                "FilmTele-Play": [
                    "FilmTele Play"
                ],
                "Video-Play": [
                    "Video Play"
                ],
                "Radio-Listen": [
                    "Radio Listen"
                ],
                "HomeAppliance-Control": [
                    "HomeAppliance Control"
                ],
                "Weather-Query": [
                    "Weather Query"
                ],
                "Alarm-Update": [
                    "Alarm Update"
                ],
                "Calendar-Query": [
                    "Calendar Query"
                ],
                "TVProgram-Play": [
                    "TVProgram Play"
                ],
                "Audio-Play": [
                    "Audio Play"
                ],
                "Other": [
                    "Other"
                ]
            },
            "version_2": {
                "Travel-Query": [
                    "Travel Query"
                ],
                "Music-Play": [
                    "Music Play"
                ],
                "FilmTele-Play": [
                    "FilmTele Play"
                ],
                "Video-Play": [
                    "Video Play"
                ],
                "Radio-Listen": [
                    "Radio Listen"
                ],
                "HomeAppliance-Control": [
                    "HomeAppliance Control"
                ],
                "Weather-Query": [
                    "Weather Query"
                ],
                "Alarm-Update": [
                    "Alarm Update"
                ],
                "Calendar-Query": [
                    "Calendar Query"
                ],
                "TVProgram-Play": [
                    "TVProgram Play"
                ],
                "Audio-Play": [
                    "Audio Play"
                ],
                "Other": [
                    "Other"
                ]
            },
            "version_3": {
                "Travel-Query": [
                    "Travel Query"
                ],
                "Music-Play": [
                    "Music Play"
                ],
                "FilmTele-Play": [
                    "FilmTele Play"
                ],
                "Video-Play": [
                    "Video Play"
                ],
                "Radio-Listen": [
                    "Radio Listen"
                ],
                "HomeAppliance-Control": [
                    "HomeAppliance Control"
                ],
                "Weather-Query": [
                    "Weather Query"
                ],
                "Alarm-Update": [
                    "Alarm Update"
                ],
                "Calendar-Query": [
                    "Calendar Query"
                ],
                "TVProgram-Play": [
                    "TVProgram Play"
                ],
                "Audio-Play": [
                    "Audio Play"
                ],
                "Other": [
                    "Other"
                ]
            },
            "version_4": {
                "Travel-Query": [
                    "Travel_Query"
                ],
                "Music-Play": [
                    "Music_Play"
                ],
                "FilmTele-Play": [
                    "FilmTele_Play"
                ],
                "Video-Play": [
                    "Video_Play"
                ],
                "Radio-Listen": [
                    "Radio_Listen"
                ],
                "HomeAppliance-Control": [
                    "HomeAppliance_Control"
                ],
                "Weather-Query": [
                    "Weather_Query"
                ],
                "Alarm-Update": [
                    "Alarm_Update"
                ],
                "Calendar-Query": [
                    "Calendar_Query"
                ],
                "TVProgram-Play": [
                    "TVProgram_Play"
                ],
                "Audio-Play": [
                    "Audio_Play"
                ],
                "Other": [
                    "Other"
                ]
            },
            "version_5": {
                "Travel-Query": [
                    "旅游查询"
                ],
                "Music-Play": [
                    "音乐播放"
                ],
                "FilmTele-Play": [
                    "电影电视剧"
                ],
                "Video-Play": [
                    "视频播放"
                ],
                "Radio-Listen": [
                    "广播收听"
                ],
                "HomeAppliance-Control": [
                    "家用电器控制"
                ],
                "Weather-Query": [
                    "天气查询"
                ],
                "Alarm-Update": [
                    "闹钟更新"
                ],
                "Calendar-Query": [
                    "日历查询"
                ],
                "TVProgram-Play": [
                    "电视节目播放"
                ],
                "Audio-Play": [
                    "音频播放"
                ],
                "Other": [
                    "其他"
                ]
            },
        },
        "amazon_massive_intent_en_us": {
            "version_0": {
                "alarm_set": [
                    "alarm_set"
                ],
                "audio_volume_mute": [
                    "audio_volume_mute"
                ],
                "iot_hue_lightchange": [
                    "iot_hue_lightchange"
                ],
                "iot_hue_lightoff": [
                    "iot_hue_lightoff"
                ],
                "iot_hue_lightdim": [
                    "iot_hue_lightdim"
                ],
                "iot_cleaning": [
                    "iot_cleaning"
                ],
                "calendar_query": [
                    "calendar_query"
                ],
                "play_music": [
                    "play_music"
                ],
                "general_quirky": [
                    "general_quirky"
                ],
                "general_greet": [
                    "general_greet"
                ],
                "datetime_query": [
                    "datetime_query"
                ],
                "datetime_convert": [
                    "datetime_convert"
                ],
                "takeaway_query": [
                    "takeaway_query"
                ],
                "alarm_remove": [
                    "alarm_remove"
                ],
                "alarm_query": [
                    "alarm_query"
                ],
                "news_query": [
                    "news_query"
                ],
                "music_likeness": [
                    "music_likeness"
                ],
                "music_query": [
                    "music_query"
                ],
                "iot_hue_lightup": [
                    "iot_hue_lightup"
                ],
                "takeaway_order": [
                    "takeaway_order"
                ],
                "weather_query": [
                    "weather_query"
                ],
                "music_settings": [
                    "music_settings"
                ],
                "general_joke": [
                    "general_joke"
                ],
                "music_dislikeness": [
                    "music_dislikeness"
                ],
                "audio_volume_other": [
                    "audio_volume_other"
                ],
                "iot_coffee": [
                    "iot_coffee"
                ],
                "audio_volume_up": [
                    "audio_volume_up"
                ],
                "iot_wemo_on": [
                    "iot_wemo_on"
                ],
                "iot_hue_lighton": [
                    "iot_hue_lighton"
                ],
                "iot_wemo_off": [
                    "iot_wemo_off"
                ],
                "audio_volume_down": [
                    "audio_volume_down"
                ],
                "qa_stock": [
                    "qa_stock"
                ],
                "play_radio": [
                    "play_radio"
                ],
                "recommendation_locations": [
                    "recommendation_locations"
                ],
                "qa_factoid": [
                    "qa_factoid"
                ],
                "calendar_set": [
                    "calendar_set"
                ],
                "play_audiobook": [
                    "play_audiobook"
                ],
                "play_podcasts": [
                    "play_podcasts"
                ],
                "social_query": [
                    "social_query"
                ],
                "transport_query": [
                    "transport_query"
                ],
                "email_sendemail": [
                    "email_sendemail"
                ],
                "recommendation_movies": [
                    "recommendation_movies"
                ],
                "lists_query": [
                    "lists_query"
                ],
                "play_game": [
                    "play_game"
                ],
                "transport_ticket": [
                    "transport_ticket"
                ],
                "recommendation_events": [
                    "recommendation_events"
                ],
                "email_query": [
                    "email_query"
                ],
                "transport_traffic": [
                    "transport_traffic"
                ],
                "cooking_query": [
                    "cooking_query"
                ],
                "qa_definition": [
                    "qa_definition"
                ],
                "calendar_remove": [
                    "calendar_remove"
                ],
                "lists_remove": [
                    "lists_remove"
                ],
                "cooking_recipe": [
                    "cooking_recipe"
                ],
                "email_querycontact": [
                    "email_querycontact"
                ],
                "lists_createoradd": [
                    "lists_createoradd"
                ],
                "transport_taxi": [
                    "transport_taxi"
                ],
                "qa_maths": [
                    "qa_maths"
                ],
                "social_post": [
                    "social_post"
                ],
                "qa_currency": [
                    "qa_currency"
                ],
                "email_addcontact": [
                    "email_addcontact"
                ]
            },
            "version_1": {
                "alarm_set": [
                    "alarm set"
                ],
                "audio_volume_mute": [
                    "audio volume mute"
                ],
                "iot_hue_lightchange": [
                    "iot hue lightchange"
                ],
                "iot_hue_lightoff": [
                    "iot hue lightoff"
                ],
                "iot_hue_lightdim": [
                    "iot hue lightdim"
                ],
                "iot_cleaning": [
                    "iot cleaning"
                ],
                "calendar_query": [
                    "calendar query"
                ],
                "play_music": [
                    "play music"
                ],
                "general_quirky": [
                    "general quirky"
                ],
                "general_greet": [
                    "general greet"
                ],
                "datetime_query": [
                    "datetime query"
                ],
                "datetime_convert": [
                    "datetime convert"
                ],
                "takeaway_query": [
                    "takeaway query"
                ],
                "alarm_remove": [
                    "alarm remove"
                ],
                "alarm_query": [
                    "alarm query"
                ],
                "news_query": [
                    "news query"
                ],
                "music_likeness": [
                    "music likeness"
                ],
                "music_query": [
                    "music query"
                ],
                "iot_hue_lightup": [
                    "iot hue lightup"
                ],
                "takeaway_order": [
                    "takeaway order"
                ],
                "weather_query": [
                    "weather query"
                ],
                "music_settings": [
                    "music settings"
                ],
                "general_joke": [
                    "general joke"
                ],
                "music_dislikeness": [
                    "music dislikeness"
                ],
                "audio_volume_other": [
                    "audio volume other"
                ],
                "iot_coffee": [
                    "iot coffee"
                ],
                "audio_volume_up": [
                    "audio volume up"
                ],
                "iot_wemo_on": [
                    "iot wemo on"
                ],
                "iot_hue_lighton": [
                    "iot hue lighton"
                ],
                "iot_wemo_off": [
                    "iot wemo off"
                ],
                "audio_volume_down": [
                    "audio volume down"
                ],
                "qa_stock": [
                    "qa stock"
                ],
                "play_radio": [
                    "play radio"
                ],
                "recommendation_locations": [
                    "recommendation locations"
                ],
                "qa_factoid": [
                    "qa factoid"
                ],
                "calendar_set": [
                    "calendar set"
                ],
                "play_audiobook": [
                    "play audiobook"
                ],
                "play_podcasts": [
                    "play podcasts"
                ],
                "social_query": [
                    "social query"
                ],
                "transport_query": [
                    "transport query"
                ],
                "email_sendemail": [
                    "email sendemail"
                ],
                "recommendation_movies": [
                    "recommendation movies"
                ],
                "lists_query": [
                    "lists query"
                ],
                "play_game": [
                    "play game"
                ],
                "transport_ticket": [
                    "transport ticket"
                ],
                "recommendation_events": [
                    "recommendation events"
                ],
                "email_query": [
                    "email query"
                ],
                "transport_traffic": [
                    "transport traffic"
                ],
                "cooking_query": [
                    "cooking query"
                ],
                "qa_definition": [
                    "qa definition"
                ],
                "calendar_remove": [
                    "calendar remove"
                ],
                "lists_remove": [
                    "lists remove"
                ],
                "cooking_recipe": [
                    "cooking recipe"
                ],
                "email_querycontact": [
                    "email querycontact"
                ],
                "lists_createoradd": [
                    "lists createoradd"
                ],
                "transport_taxi": [
                    "transport taxi"
                ],
                "qa_maths": [
                    "qa maths"
                ],
                "social_post": [
                    "social post"
                ],
                "qa_currency": [
                    "qa currency"
                ],
                "email_addcontact": [
                    "email addcontact"
                ]
            },
            "version_2": {
                "alarm_set": [
                    "Alarm Set"
                ],
                "audio_volume_mute": [
                    "Audio Volume Mute"
                ],
                "iot_hue_lightchange": [
                    "Iot Hue Lightchange"
                ],
                "iot_hue_lightoff": [
                    "Iot Hue Lightoff"
                ],
                "iot_hue_lightdim": [
                    "Iot Hue Lightdim"
                ],
                "iot_cleaning": [
                    "Iot Cleaning"
                ],
                "calendar_query": [
                    "Calendar Query"
                ],
                "play_music": [
                    "Play Music"
                ],
                "general_quirky": [
                    "General Quirky"
                ],
                "general_greet": [
                    "General Greet"
                ],
                "datetime_query": [
                    "Datetime Query"
                ],
                "datetime_convert": [
                    "Datetime Convert"
                ],
                "takeaway_query": [
                    "Takeaway Query"
                ],
                "alarm_remove": [
                    "Alarm Remove"
                ],
                "alarm_query": [
                    "Alarm Query"
                ],
                "news_query": [
                    "News Query"
                ],
                "music_likeness": [
                    "Music Likeness"
                ],
                "music_query": [
                    "Music Query"
                ],
                "iot_hue_lightup": [
                    "Iot Hue Lightup"
                ],
                "takeaway_order": [
                    "Takeaway Order"
                ],
                "weather_query": [
                    "Weather Query"
                ],
                "music_settings": [
                    "Music Settings"
                ],
                "general_joke": [
                    "General Joke"
                ],
                "music_dislikeness": [
                    "Music Dislikeness"
                ],
                "audio_volume_other": [
                    "Audio Volume Other"
                ],
                "iot_coffee": [
                    "Iot Coffee"
                ],
                "audio_volume_up": [
                    "Audio Volume Up"
                ],
                "iot_wemo_on": [
                    "Iot Wemo On"
                ],
                "iot_hue_lighton": [
                    "Iot Hue Lighton"
                ],
                "iot_wemo_off": [
                    "Iot Wemo Off"
                ],
                "audio_volume_down": [
                    "Audio Volume Down"
                ],
                "qa_stock": [
                    "Qa Stock"
                ],
                "play_radio": [
                    "Play Radio"
                ],
                "recommendation_locations": [
                    "Recommendation Locations"
                ],
                "qa_factoid": [
                    "Qa Factoid"
                ],
                "calendar_set": [
                    "Calendar Set"
                ],
                "play_audiobook": [
                    "Play Audiobook"
                ],
                "play_podcasts": [
                    "Play Podcasts"
                ],
                "social_query": [
                    "Social Query"
                ],
                "transport_query": [
                    "Transport Query"
                ],
                "email_sendemail": [
                    "Email Sendemail"
                ],
                "recommendation_movies": [
                    "Recommendation Movies"
                ],
                "lists_query": [
                    "Lists Query"
                ],
                "play_game": [
                    "Play Game"
                ],
                "transport_ticket": [
                    "Transport Ticket"
                ],
                "recommendation_events": [
                    "Recommendation Events"
                ],
                "email_query": [
                    "Email Query"
                ],
                "transport_traffic": [
                    "Transport Traffic"
                ],
                "cooking_query": [
                    "Cooking Query"
                ],
                "qa_definition": [
                    "Qa Definition"
                ],
                "calendar_remove": [
                    "Calendar Remove"
                ],
                "lists_remove": [
                    "Lists Remove"
                ],
                "cooking_recipe": [
                    "Cooking Recipe"
                ],
                "email_querycontact": [
                    "Email Querycontact"
                ],
                "lists_createoradd": [
                    "Lists Createoradd"
                ],
                "transport_taxi": [
                    "Transport Taxi"
                ],
                "qa_maths": [
                    "Qa Maths"
                ],
                "social_post": [
                    "Social Post"
                ],
                "qa_currency": [
                    "Qa Currency"
                ],
                "email_addcontact": [
                    "Email Addcontact"
                ]
            },
            "version_3": {
                "alarm_set": [
                    "AlarmSet"
                ],
                "audio_volume_mute": [
                    "AudioVolumeMute"
                ],
                "iot_hue_lightchange": [
                    "IotHueLightchange"
                ],
                "iot_hue_lightoff": [
                    "IotHueLightoff"
                ],
                "iot_hue_lightdim": [
                    "IotHueLightdim"
                ],
                "iot_cleaning": [
                    "IotCleaning"
                ],
                "calendar_query": [
                    "CalendarQuery"
                ],
                "play_music": [
                    "PlayMusic"
                ],
                "general_quirky": [
                    "GeneralQuirky"
                ],
                "general_greet": [
                    "GeneralGreet"
                ],
                "datetime_query": [
                    "DatetimeQuery"
                ],
                "datetime_convert": [
                    "DatetimeConvert"
                ],
                "takeaway_query": [
                    "TakeawayQuery"
                ],
                "alarm_remove": [
                    "AlarmRemove"
                ],
                "alarm_query": [
                    "AlarmQuery"
                ],
                "news_query": [
                    "NewsQuery"
                ],
                "music_likeness": [
                    "MusicLikeness"
                ],
                "music_query": [
                    "MusicQuery"
                ],
                "iot_hue_lightup": [
                    "IotHueLightup"
                ],
                "takeaway_order": [
                    "TakeawayOrder"
                ],
                "weather_query": [
                    "WeatherQuery"
                ],
                "music_settings": [
                    "MusicSettings"
                ],
                "general_joke": [
                    "GeneralJoke"
                ],
                "music_dislikeness": [
                    "MusicDislikeness"
                ],
                "audio_volume_other": [
                    "AudioVolumeOther"
                ],
                "iot_coffee": [
                    "IotCoffee"
                ],
                "audio_volume_up": [
                    "AudioVolumeUp"
                ],
                "iot_wemo_on": [
                    "IotWemoOn"
                ],
                "iot_hue_lighton": [
                    "IotHueLighton"
                ],
                "iot_wemo_off": [
                    "IotWemoOff"
                ],
                "audio_volume_down": [
                    "AudioVolumeDown"
                ],
                "qa_stock": [
                    "QaStock"
                ],
                "play_radio": [
                    "PlayRadio"
                ],
                "recommendation_locations": [
                    "RecommendationLocations"
                ],
                "qa_factoid": [
                    "QaFactoid"
                ],
                "calendar_set": [
                    "CalendarSet"
                ],
                "play_audiobook": [
                    "PlayAudiobook"
                ],
                "play_podcasts": [
                    "PlayPodcasts"
                ],
                "social_query": [
                    "SocialQuery"
                ],
                "transport_query": [
                    "TransportQuery"
                ],
                "email_sendemail": [
                    "EmailSendemail"
                ],
                "recommendation_movies": [
                    "RecommendationMovies"
                ],
                "lists_query": [
                    "ListsQuery"
                ],
                "play_game": [
                    "PlayGame"
                ],
                "transport_ticket": [
                    "TransportTicket"
                ],
                "recommendation_events": [
                    "RecommendationEvents"
                ],
                "email_query": [
                    "EmailQuery"
                ],
                "transport_traffic": [
                    "TransportTraffic"
                ],
                "cooking_query": [
                    "CookingQuery"
                ],
                "qa_definition": [
                    "QaDefinition"
                ],
                "calendar_remove": [
                    "CalendarRemove"
                ],
                "lists_remove": [
                    "ListsRemove"
                ],
                "cooking_recipe": [
                    "CookingRecipe"
                ],
                "email_querycontact": [
                    "EmailQuerycontact"
                ],
                "lists_createoradd": [
                    "ListsCreateoradd"
                ],
                "transport_taxi": [
                    "TransportTaxi"
                ],
                "qa_maths": [
                    "QaMaths"
                ],
                "social_post": [
                    "SocialPost"
                ],
                "qa_currency": [
                    "QaCurrency"
                ],
                "email_addcontact": [
                    "EmailAddcontact"
                ]
            }
        },
        "amazon_massive_intent_zh_cn": {"version_0": {
            "报警器": [
                "闹钟"
            ],
            "音量静音": [
                "音量静音"
            ],
            "物联网色调光变": [
                "物联网色调光变"
            ],
            "物联网色调熄灯": [
                "物联网色调熄灯"
            ],
            "物联网色调 lightdim": [
                "物联网色调 lightdim"
            ],
            "物联网清洁": [
                "物联网清洁"
            ],
            "日历查询": [
                "日历查询", "查询日历"
            ],
            "播放音乐": [
                "播放音乐", "音乐播放"
            ],
            "一般古怪": [
                "一般聊天", "闲聊"
            ],
            "一般问候": [
                "一般问候", "问候"
            ],
            "日期时间查询": [
                "日期时间查询", "查询时间或日期", "查询日期或时间"
            ],
            "日期时间转换": [
                "日期时间转换", "日期或时间转换"
            ],
            "外卖查询": [
                "外卖查询", "查询外卖"
            ],
            "警报解除": [
                "解除闹钟", "删除闹钟", "取消闹钟"
            ],
            "报警查询": [
                "查询闹钟", "闹钟查询"
            ],
            "新闻查询": [
                "新闻查询", "查询新闻"
            ],
            "音乐相似度": [
                "音乐偏好", "音乐喜好", "表达音乐喜好", "表达音乐偏好"
            ],
            "音乐查询": [
                "音乐查询", "查询音乐"
            ],
            "物联网色调点亮": [
                "物联网色调点亮"
            ],
            "外卖订单": [
                "外卖订单"
            ],
            "天气查询": [
                "天气查询", "查询天气"
            ],
            "音乐设置": [
                "音乐设置", "设置音乐"
            ],
            "一般笑话": [
                "一般笑话", "笑话", "讲个笑话", "给我讲个笑话"
            ],
            "不喜欢音乐": [
                "不喜欢音乐"
            ],
            "音量 其他": [
                "音量", "调节音量", "改变音量", "调整音量"
            ],
            "物联网咖啡": [
                "物联网咖啡", "咖啡"
            ],
            "音量调高": [
                "音量调高", "调高音量"
            ],
            "iot wemo on": [
                "打开智能插座", "打开智能插头", "打开插座", "打开插头", "开启智能插座", "开启智能插头", "开启插座", "开启插头"
            ],
            "物联网色调莱顿": [
                "开灯", "打开灯光"
            ],
            "iot wemo 关闭": [
                "关闭智能插座", "关闭智能插头", "关闭插座", "关闭插头"
            ],
            "音量降低": [
                "音量降低", "降低音量"
            ],
            "库存": [
                "股票查询"
            ],
            "播放收音机": [
                "播放收音机", "开启收音机"
            ],
            "推荐地点": [
                "推荐地点", "推荐地址"
            ],
            "质量保证": [
                "QA", "一般QA", "一般问答"
            ],
            "日历集": [
                "日历集"
            ],
            "播放有声读物": [
                "播放有声读物"
            ],
            "播放播客": [
                "播放播客"
            ],
            "社会查询": [
                "社会查询"
            ],
            "运输查询": [
                "运输查询"
            ],
            "发送电子邮件": [
                "发送电子邮件"
            ],
            "推荐电影": [
                "推荐电影"
            ],
            "列出查询": [
                "列出查询"
            ],
            "玩游戏": [
                "玩游戏"
            ],
            "交通票": [
                "交通票"
            ],
            "推荐活动": [
                "推荐活动"
            ],
            "电子邮件查询": [
                "电子邮件查询", "查询邮件", "查询电子邮件"
            ],
            "交通运输": [
                "交通运输"
            ],
            "烹饪查询": [
                "烹饪查询"
            ],
            "质量保证定义": [
                "QA定义", "定义问答"
            ],
            "日历删除": [
                "日历删除", "删除日历"
            ],
            "列表删除": [
                "列表删除", "删除列表"
            ],
            "烹饪食谱": [
                "烹饪食谱"
            ],
            "电子邮件查询联系方式": [
                "电子邮件查询联系方式"
            ],
            "列出创建或添加": [
                "列表创建或添加"
            ],
            "运输出租车": [
                "运输出租车"
            ],
            "qa数学": [
                "数学问答", "数学问题"
            ],
            "社交帖子": [
                "社交帖子"
            ],
            "qa 货币": [
                "货币问答", "汇率查询", "查询汇率"
            ],
            "电子邮件添加联系人": [
                "电子邮件添加联系人"
            ]
        }},
        "atis_intents": {
            "version_0": {
                "atis_flight": ["Flight", "Check Flights", "Query Flights", "Book a Flight"],
                "atis_flight_time": ["Flight Time", "Check Flights Time", "Query Flights Time", "Flight Schedule"],
                "atis_airfare": ["Airfare", "Air Ticket Price", "Price"],
                "atis_aircraft": ["Aircraft", "Aircraft Type", "Type of Plane"],
                "atis_ground_service": ["Ground Service"],
                "atis_airline": ["Airline", "Airway", "Shipping Line"],
                "atis_abbreviation": ["Abbreviation"],
                "atis_quantity": ["Quantity"],
            },
            "version_1": {
                "atis_flight": ["Flight", "CheckFlights", "QueryFlights", "BookFlight"],
                "atis_flight_time": ["FlightTime", "CheckFlightsTime", "QueryFlightsTime", "FlightSchedule"],
                "atis_airfare": ["Airfare", "AirTicketPrice", "Price"],
                "atis_aircraft": ["Aircraft", "AircraftType", "TypeOfPlane"],
                "atis_ground_service": ["GroundService"],
                "atis_airline": ["Airline", "Airway", "ShippingLine"],
                "atis_abbreviation": ["Abbreviation"],
                "atis_quantity": ["Quantity"],
            },
            "version_2": {
                "atis_flight": ["flight", "check_flights", "query_flights", "book_flight"],
                "atis_flight_time": ["flight_time", "check_flights_time", "query_flights_time", "flight_schedule"],
                "atis_airfare": ["airfare", "air_ticket_price", "price"],
                "atis_aircraft": ["aircraft", "aircraft_type", "type_of_plane"],
                "atis_ground_service": ["ground_service"],
                "atis_airline": ["airline", "airway", "shipping_line"],
                "atis_abbreviation": ["abbreviation"],
                "atis_quantity": ["quantity"],
            },
            "version_3": {
                "atis_flight": ["flight", "check flights", "query flights", "book flight"],
                "atis_flight_time": ["flight time", "check flights time", "query flights time", "flight schedule"],
                "atis_airfare": ["airfare", "air ticket price", "price"],
                "atis_aircraft": ["aircraft", "aircraft type", "type of plane"],
                "atis_ground_service": ["ground service"],
                "atis_airline": ["airline", "airway", "shipping line"],
                "atis_abbreviation": ["abbreviation"],
                "atis_quantity": ["quantity"],
            }
        },
        "banking77": {
            "version_0": {
                "activate_my_card": [
                    "activate_my_card"
                ],
                "age_limit": [
                    "age_limit"
                ],
                "apple_pay_or_google_pay": [
                    "apple_pay_or_google_pay"
                ],
                "atm_support": [
                    "atm_support"
                ],
                "automatic_top_up": [
                    "automatic_top_up"
                ],
                "balance_not_updated_after_bank_transfer": [
                    "balance_not_updated_after_bank_transfer"
                ],
                "balance_not_updated_after_cheque_or_cash_deposit": [
                    "balance_not_updated_after_cheque_or_cash_deposit"
                ],
                "beneficiary_not_allowed": [
                    "beneficiary_not_allowed"
                ],
                "cancel_transfer": [
                    "cancel_transfer"
                ],
                "card_about_to_expire": [
                    "card_about_to_expire"
                ],
                "card_acceptance": [
                    "card_acceptance"
                ],
                "card_arrival": [
                    "card_arrival"
                ],
                "card_delivery_estimate": [
                    "card_delivery_estimate"
                ],
                "card_linking": [
                    "card_linking"
                ],
                "card_not_working": [
                    "card_not_working"
                ],
                "card_payment_fee_charged": [
                    "card_payment_fee_charged"
                ],
                "card_payment_not_recognised": [
                    "card_payment_not_recognised"
                ],
                "card_payment_wrong_exchange_rate": [
                    "card_payment_wrong_exchange_rate"
                ],
                "card_swallowed": [
                    "card_swallowed"
                ],
                "cash_withdrawal_charge": [
                    "cash_withdrawal_charge"
                ],
                "cash_withdrawal_not_recognised": [
                    "cash_withdrawal_not_recognised"
                ],
                "change_pin": [
                    "change_pin"
                ],
                "compromised_card": [
                    "compromised_card"
                ],
                "contactless_not_working": [
                    "contactless_not_working"
                ],
                "country_support": [
                    "country_support"
                ],
                "declined_card_payment": [
                    "declined_card_payment"
                ],
                "declined_cash_withdrawal": [
                    "declined_cash_withdrawal"
                ],
                "declined_transfer": [
                    "declined_transfer"
                ],
                "direct_debit_payment_not_recognised": [
                    "direct_debit_payment_not_recognised"
                ],
                "disposable_card_limits": [
                    "disposable_card_limits"
                ],
                "edit_personal_details": [
                    "edit_personal_details"
                ],
                "exchange_charge": [
                    "exchange_charge"
                ],
                "exchange_rate": [
                    "exchange_rate"
                ],
                "exchange_via_app": [
                    "exchange_via_app"
                ],
                "extra_charge_on_statement": [
                    "extra_charge_on_statement"
                ],
                "failed_transfer": [
                    "failed_transfer"
                ],
                "fiat_currency_support": [
                    "fiat_currency_support"
                ],
                "get_disposable_virtual_card": [
                    "get_disposable_virtual_card"
                ],
                "get_physical_card": [
                    "get_physical_card"
                ],
                "getting_spare_card": [
                    "getting_spare_card"
                ],
                "getting_virtual_card": [
                    "getting_virtual_card"
                ],
                "lost_or_stolen_card": [
                    "lost_or_stolen_card"
                ],
                "lost_or_stolen_phone": [
                    "lost_or_stolen_phone"
                ],
                "order_physical_card": [
                    "order_physical_card"
                ],
                "passcode_forgotten": [
                    "passcode_forgotten"
                ],
                "pending_card_payment": [
                    "pending_card_payment"
                ],
                "pending_cash_withdrawal": [
                    "pending_cash_withdrawal"
                ],
                "pending_top_up": [
                    "pending_top_up"
                ],
                "pending_transfer": [
                    "pending_transfer"
                ],
                "pin_blocked": [
                    "pin_blocked"
                ],
                "receiving_money": [
                    "receiving_money"
                ],
                "Refund_not_showing_up": [
                    "Refund_not_showing_up"
                ],
                "request_refund": [
                    "request_refund", "return", "refund"
                ],
                "reverted_card_payment?": [
                    "reverted_card_payment?"
                ],
                "supported_cards_and_currencies": [
                    "supported_cards_and_currencies"
                ],
                "terminate_account": [
                    "terminate_account"
                ],
                "top_up_by_bank_transfer_charge": [
                    "top_up_by_bank_transfer_charge"
                ],
                "top_up_by_card_charge": [
                    "top_up_by_card_charge"
                ],
                "top_up_by_cash_or_cheque": [
                    "top_up_by_cash_or_cheque"
                ],
                "top_up_failed": [
                    "top_up_failed"
                ],
                "top_up_limits": [
                    "top_up_limits"
                ],
                "top_up_reverted": [
                    "top_up_reverted"
                ],
                "topping_up_by_card": [
                    "topping_up_by_card"
                ],
                "transaction_charged_twice": [
                    "transaction_charged_twice"
                ],
                "transfer_fee_charged": [
                    "transfer_fee_charged"
                ],
                "transfer_into_account": [
                    "transfer_into_account"
                ],
                "transfer_not_received_by_recipient": [
                    "transfer_not_received_by_recipient"
                ],
                "transfer_timing": [
                    "transfer_timing"
                ],
                "unable_to_verify_identity": [
                    "unable_to_verify_identity"
                ],
                "verify_my_identity": [
                    "verify_my_identity"
                ],
                "verify_source_of_funds": [
                    "verify_source_of_funds"
                ],
                "verify_top_up": [
                    "verify_top_up"
                ],
                "virtual_card_not_working": [
                    "virtual_card_not_working"
                ],
                "visa_or_mastercard": [
                    "visa_or_mastercard"
                ],
                "why_verify_identity": [
                    "why_verify_identity"
                ],
                "wrong_amount_of_cash_received": [
                    "wrong_amount_of_cash_received"
                ],
                "wrong_exchange_rate_for_cash_withdrawal": [
                    "wrong_exchange_rate_for_cash_withdrawal"
                ]
            },
            "version_1": {
                "activate_my_card": [
                    "activate my card"
                ],
                "age_limit": [
                    "age limit"
                ],
                "apple_pay_or_google_pay": [
                    "apple pay or google pay"
                ],
                "atm_support": [
                    "atm support"
                ],
                "automatic_top_up": [
                    "automatic top up"
                ],
                "balance_not_updated_after_bank_transfer": [
                    "balance not updated after bank transfer"
                ],
                "balance_not_updated_after_cheque_or_cash_deposit": [
                    "balance not updated after cheque or cash deposit"
                ],
                "beneficiary_not_allowed": [
                    "beneficiary not allowed"
                ],
                "cancel_transfer": [
                    "cancel transfer"
                ],
                "card_about_to_expire": [
                    "card about to expire"
                ],
                "card_acceptance": [
                    "card acceptance"
                ],
                "card_arrival": [
                    "card arrival"
                ],
                "card_delivery_estimate": [
                    "card delivery estimate"
                ],
                "card_linking": [
                    "card linking"
                ],
                "card_not_working": [
                    "card not working"
                ],
                "card_payment_fee_charged": [
                    "card payment fee charged"
                ],
                "card_payment_not_recognised": [
                    "card payment not recognised"
                ],
                "card_payment_wrong_exchange_rate": [
                    "card payment wrong exchange rate"
                ],
                "card_swallowed": [
                    "card swallowed"
                ],
                "cash_withdrawal_charge": [
                    "cash withdrawal charge"
                ],
                "cash_withdrawal_not_recognised": [
                    "cash withdrawal not recognised"
                ],
                "change_pin": [
                    "change pin"
                ],
                "compromised_card": [
                    "compromised card"
                ],
                "contactless_not_working": [
                    "contactless not working"
                ],
                "country_support": [
                    "country support"
                ],
                "declined_card_payment": [
                    "declined card payment"
                ],
                "declined_cash_withdrawal": [
                    "declined cash withdrawal"
                ],
                "declined_transfer": [
                    "declined transfer"
                ],
                "direct_debit_payment_not_recognised": [
                    "direct debit payment not recognised"
                ],
                "disposable_card_limits": [
                    "disposable card limits"
                ],
                "edit_personal_details": [
                    "edit personal details"
                ],
                "exchange_charge": [
                    "exchange charge"
                ],
                "exchange_rate": [
                    "exchange rate"
                ],
                "exchange_via_app": [
                    "exchange via app"
                ],
                "extra_charge_on_statement": [
                    "extra charge on statement"
                ],
                "failed_transfer": [
                    "failed transfer"
                ],
                "fiat_currency_support": [
                    "fiat currency support"
                ],
                "get_disposable_virtual_card": [
                    "get disposable virtual card"
                ],
                "get_physical_card": [
                    "get physical card"
                ],
                "getting_spare_card": [
                    "getting spare card"
                ],
                "getting_virtual_card": [
                    "getting virtual card"
                ],
                "lost_or_stolen_card": [
                    "lost or stolen card"
                ],
                "lost_or_stolen_phone": [
                    "lost or stolen phone"
                ],
                "order_physical_card": [
                    "order physical card"
                ],
                "passcode_forgotten": [
                    "passcode forgotten"
                ],
                "pending_card_payment": [
                    "pending card payment"
                ],
                "pending_cash_withdrawal": [
                    "pending cash withdrawal"
                ],
                "pending_top_up": [
                    "pending top up"
                ],
                "pending_transfer": [
                    "pending transfer"
                ],
                "pin_blocked": [
                    "pin blocked"
                ],
                "receiving_money": [
                    "receiving money"
                ],
                "Refund_not_showing_up": [
                    "Refund not showing up"
                ],
                "request_refund": [
                    "request refund", "return", "refund"
                ],
                "reverted_card_payment?": [
                    "reverted card payment?"
                ],
                "supported_cards_and_currencies": [
                    "supported cards and currencies"
                ],
                "terminate_account": [
                    "terminate account"
                ],
                "top_up_by_bank_transfer_charge": [
                    "top up by bank transfer charge"
                ],
                "top_up_by_card_charge": [
                    "top up by card charge"
                ],
                "top_up_by_cash_or_cheque": [
                    "top up by cash or cheque"
                ],
                "top_up_failed": [
                    "top up failed"
                ],
                "top_up_limits": [
                    "top up limits"
                ],
                "top_up_reverted": [
                    "top up reverted"
                ],
                "topping_up_by_card": [
                    "topping up by card"
                ],
                "transaction_charged_twice": [
                    "transaction charged twice"
                ],
                "transfer_fee_charged": [
                    "transfer fee charged"
                ],
                "transfer_into_account": [
                    "transfer into account"
                ],
                "transfer_not_received_by_recipient": [
                    "transfer not received by recipient"
                ],
                "transfer_timing": [
                    "transfer timing"
                ],
                "unable_to_verify_identity": [
                    "unable to verify identity"
                ],
                "verify_my_identity": [
                    "verify my identity"
                ],
                "verify_source_of_funds": [
                    "verify source of funds"
                ],
                "verify_top_up": [
                    "verify top up"
                ],
                "virtual_card_not_working": [
                    "virtual card not working"
                ],
                "visa_or_mastercard": [
                    "visa or mastercard"
                ],
                "why_verify_identity": [
                    "why verify identity"
                ],
                "wrong_amount_of_cash_received": [
                    "wrong amount of cash received"
                ],
                "wrong_exchange_rate_for_cash_withdrawal": [
                    "wrong exchange rate for cash withdrawal"
                ]
            },
            "version_2": {
                "activate_my_card": [
                    "Activate My Card"
                ],
                "age_limit": [
                    "Age Limit"
                ],
                "apple_pay_or_google_pay": [
                    "Apple Pay Or Google Pay"
                ],
                "atm_support": [
                    "Atm Support"
                ],
                "automatic_top_up": [
                    "Automatic Top Up"
                ],
                "balance_not_updated_after_bank_transfer": [
                    "Balance Not Updated After Bank Transfer"
                ],
                "balance_not_updated_after_cheque_or_cash_deposit": [
                    "Balance Not Updated After Cheque Or Cash Deposit"
                ],
                "beneficiary_not_allowed": [
                    "Beneficiary Not Allowed"
                ],
                "cancel_transfer": [
                    "Cancel Transfer"
                ],
                "card_about_to_expire": [
                    "Card About To Expire"
                ],
                "card_acceptance": [
                    "Card Acceptance"
                ],
                "card_arrival": [
                    "Card Arrival"
                ],
                "card_delivery_estimate": [
                    "Card Delivery Estimate"
                ],
                "card_linking": [
                    "Card Linking"
                ],
                "card_not_working": [
                    "Card Not Working"
                ],
                "card_payment_fee_charged": [
                    "Card Payment Fee Charged"
                ],
                "card_payment_not_recognised": [
                    "Card Payment Not Recognised"
                ],
                "card_payment_wrong_exchange_rate": [
                    "Card Payment Wrong Exchange Rate"
                ],
                "card_swallowed": [
                    "Card Swallowed"
                ],
                "cash_withdrawal_charge": [
                    "Cash Withdrawal Charge"
                ],
                "cash_withdrawal_not_recognised": [
                    "Cash Withdrawal Not Recognised"
                ],
                "change_pin": [
                    "Change Pin"
                ],
                "compromised_card": [
                    "Compromised Card"
                ],
                "contactless_not_working": [
                    "Contactless Not Working"
                ],
                "country_support": [
                    "Country Support"
                ],
                "declined_card_payment": [
                    "Declined Card Payment"
                ],
                "declined_cash_withdrawal": [
                    "Declined Cash Withdrawal"
                ],
                "declined_transfer": [
                    "Declined Transfer"
                ],
                "direct_debit_payment_not_recognised": [
                    "Direct Debit Payment Not Recognised"
                ],
                "disposable_card_limits": [
                    "Disposable Card Limits"
                ],
                "edit_personal_details": [
                    "Edit Personal Details"
                ],
                "exchange_charge": [
                    "Exchange Charge"
                ],
                "exchange_rate": [
                    "Exchange Rate"
                ],
                "exchange_via_app": [
                    "Exchange Via App"
                ],
                "extra_charge_on_statement": [
                    "Extra Charge On Statement"
                ],
                "failed_transfer": [
                    "Failed Transfer"
                ],
                "fiat_currency_support": [
                    "Fiat Currency Support"
                ],
                "get_disposable_virtual_card": [
                    "Get Disposable Virtual Card"
                ],
                "get_physical_card": [
                    "Get Physical Card"
                ],
                "getting_spare_card": [
                    "Getting Spare Card"
                ],
                "getting_virtual_card": [
                    "Getting Virtual Card"
                ],
                "lost_or_stolen_card": [
                    "Lost Or Stolen Card"
                ],
                "lost_or_stolen_phone": [
                    "Lost Or Stolen Phone"
                ],
                "order_physical_card": [
                    "Order Physical Card"
                ],
                "passcode_forgotten": [
                    "Passcode Forgotten"
                ],
                "pending_card_payment": [
                    "Pending Card Payment"
                ],
                "pending_cash_withdrawal": [
                    "Pending Cash Withdrawal"
                ],
                "pending_top_up": [
                    "Pending Top Up"
                ],
                "pending_transfer": [
                    "Pending Transfer"
                ],
                "pin_blocked": [
                    "Pin Blocked"
                ],
                "receiving_money": [
                    "Receiving Money"
                ],
                "Refund_not_showing_up": [
                    "Refund Not Showing Up"
                ],
                "request_refund": [
                    "Request Refund", "Return", "Refund"
                ],
                "reverted_card_payment?": [
                    "Reverted Card Payment?"
                ],
                "supported_cards_and_currencies": [
                    "Supported Cards And Currencies"
                ],
                "terminate_account": [
                    "Terminate Account"
                ],
                "top_up_by_bank_transfer_charge": [
                    "Top Up By Bank Transfer Charge"
                ],
                "top_up_by_card_charge": [
                    "Top Up By Card Charge"
                ],
                "top_up_by_cash_or_cheque": [
                    "Top Up By Cash Or Cheque"
                ],
                "top_up_failed": [
                    "Top Up Failed"
                ],
                "top_up_limits": [
                    "Top Up Limits"
                ],
                "top_up_reverted": [
                    "Top Up Reverted"
                ],
                "topping_up_by_card": [
                    "Topping Up By Card"
                ],
                "transaction_charged_twice": [
                    "Transaction Charged Twice"
                ],
                "transfer_fee_charged": [
                    "Transfer Fee Charged"
                ],
                "transfer_into_account": [
                    "Transfer Into Account"
                ],
                "transfer_not_received_by_recipient": [
                    "Transfer Not Received By Recipient"
                ],
                "transfer_timing": [
                    "Transfer Timing"
                ],
                "unable_to_verify_identity": [
                    "Unable To Verify Identity"
                ],
                "verify_my_identity": [
                    "Verify My Identity"
                ],
                "verify_source_of_funds": [
                    "Verify Source Of Funds"
                ],
                "verify_top_up": [
                    "Verify Top Up"
                ],
                "virtual_card_not_working": [
                    "Virtual Card Not Working"
                ],
                "visa_or_mastercard": [
                    "Visa Or Mastercard"
                ],
                "why_verify_identity": [
                    "Why Verify Identity"
                ],
                "wrong_amount_of_cash_received": [
                    "Wrong Amount Of Cash Received"
                ],
                "wrong_exchange_rate_for_cash_withdrawal": [
                    "Wrong Exchange Rate For Cash Withdrawal"
                ]
            },
            "version_3": {
                "activate_my_card": [
                    "ActivateMyCard"
                ],
                "age_limit": [
                    "AgeLimit"
                ],
                "apple_pay_or_google_pay": [
                    "ApplePayOrGooglePay"
                ],
                "atm_support": [
                    "AtmSupport"
                ],
                "automatic_top_up": [
                    "AutomaticTopUp"
                ],
                "balance_not_updated_after_bank_transfer": [
                    "BalanceNotUpdatedAfterBankTransfer"
                ],
                "balance_not_updated_after_cheque_or_cash_deposit": [
                    "BalanceNotUpdatedAfterChequeOrCashDeposit"
                ],
                "beneficiary_not_allowed": [
                    "BeneficiaryNotAllowed"
                ],
                "cancel_transfer": [
                    "CancelTransfer"
                ],
                "card_about_to_expire": [
                    "CardAboutToExpire"
                ],
                "card_acceptance": [
                    "CardAcceptance"
                ],
                "card_arrival": [
                    "CardArrival"
                ],
                "card_delivery_estimate": [
                    "CardDeliveryEstimate"
                ],
                "card_linking": [
                    "CardLinking"
                ],
                "card_not_working": [
                    "CardNotWorking"
                ],
                "card_payment_fee_charged": [
                    "CardPaymentFeeCharged"
                ],
                "card_payment_not_recognised": [
                    "CardPaymentNotRecognised"
                ],
                "card_payment_wrong_exchange_rate": [
                    "CardPaymentWrongExchangeRate"
                ],
                "card_swallowed": [
                    "CardSwallowed"
                ],
                "cash_withdrawal_charge": [
                    "CashWithdrawalCharge"
                ],
                "cash_withdrawal_not_recognised": [
                    "CashWithdrawalNotRecognised"
                ],
                "change_pin": [
                    "ChangePin"
                ],
                "compromised_card": [
                    "CompromisedCard"
                ],
                "contactless_not_working": [
                    "ContactlessNotWorking"
                ],
                "country_support": [
                    "CountrySupport"
                ],
                "declined_card_payment": [
                    "DeclinedCardPayment"
                ],
                "declined_cash_withdrawal": [
                    "DeclinedCashWithdrawal"
                ],
                "declined_transfer": [
                    "DeclinedTransfer"
                ],
                "direct_debit_payment_not_recognised": [
                    "DirectDebitPaymentNotRecognised"
                ],
                "disposable_card_limits": [
                    "DisposableCardLimits"
                ],
                "edit_personal_details": [
                    "EditPersonalDetails"
                ],
                "exchange_charge": [
                    "ExchangeCharge"
                ],
                "exchange_rate": [
                    "ExchangeRate"
                ],
                "exchange_via_app": [
                    "ExchangeViaApp"
                ],
                "extra_charge_on_statement": [
                    "ExtraChargeOnStatement"
                ],
                "failed_transfer": [
                    "FailedTransfer"
                ],
                "fiat_currency_support": [
                    "FiatCurrencySupport"
                ],
                "get_disposable_virtual_card": [
                    "GetDisposableVirtualCard"
                ],
                "get_physical_card": [
                    "GetPhysicalCard"
                ],
                "getting_spare_card": [
                    "GettingSpareCard"
                ],
                "getting_virtual_card": [
                    "GettingVirtualCard"
                ],
                "lost_or_stolen_card": [
                    "LostOrStolenCard"
                ],
                "lost_or_stolen_phone": [
                    "LostOrStolenPhone"
                ],
                "order_physical_card": [
                    "OrderPhysicalCard"
                ],
                "passcode_forgotten": [
                    "PasscodeForgotten"
                ],
                "pending_card_payment": [
                    "PendingCardPayment"
                ],
                "pending_cash_withdrawal": [
                    "PendingCashWithdrawal"
                ],
                "pending_top_up": [
                    "PendingTopUp"
                ],
                "pending_transfer": [
                    "PendingTransfer"
                ],
                "pin_blocked": [
                    "PinBlocked"
                ],
                "receiving_money": [
                    "ReceivingMoney"
                ],
                "Refund_not_showing_up": [
                    "RefundNotShowingUp"
                ],
                "request_refund": [
                    "RequestRefund", "Return", "Refund"
                ],
                "reverted_card_payment?": [
                    "RevertedCardPayment?"
                ],
                "supported_cards_and_currencies": [
                    "SupportedCardsAndCurrencies"
                ],
                "terminate_account": [
                    "TerminateAccount"
                ],
                "top_up_by_bank_transfer_charge": [
                    "TopUpByBankTransferCharge"
                ],
                "top_up_by_card_charge": [
                    "TopUpByCardCharge"
                ],
                "top_up_by_cash_or_cheque": [
                    "TopUpByCashOrCheque"
                ],
                "top_up_failed": [
                    "TopUpFailed"
                ],
                "top_up_limits": [
                    "TopUpLimits"
                ],
                "top_up_reverted": [
                    "TopUpReverted"
                ],
                "topping_up_by_card": [
                    "ToppingUpByCard"
                ],
                "transaction_charged_twice": [
                    "TransactionChargedTwice"
                ],
                "transfer_fee_charged": [
                    "TransferFeeCharged"
                ],
                "transfer_into_account": [
                    "TransferIntoAccount"
                ],
                "transfer_not_received_by_recipient": [
                    "TransferNotReceivedByRecipient"
                ],
                "transfer_timing": [
                    "TransferTiming"
                ],
                "unable_to_verify_identity": [
                    "UnableToVerifyIdentity"
                ],
                "verify_my_identity": [
                    "VerifyMyIdentity"
                ],
                "verify_source_of_funds": [
                    "VerifySourceOfFunds"
                ],
                "verify_top_up": [
                    "VerifyTopUp"
                ],
                "virtual_card_not_working": [
                    "VirtualCardNotWorking"
                ],
                "visa_or_mastercard": [
                    "VisaOrMastercard"
                ],
                "why_verify_identity": [
                    "WhyVerifyIdentity"
                ],
                "wrong_amount_of_cash_received": [
                    "WrongAmountOfCashReceived"
                ],
                "wrong_exchange_rate_for_cash_withdrawal": [
                    "WrongExchangeRateForCashWithdrawal"
                ]
            }
        },
        "bi_text11": {
            "version_0": {
                "order": [
                    "order"
                ],
                "shipping_address": [
                    "shipping_address"
                ],
                "cancellation_fee": [
                    "cancellation_fee"
                ],
                "invoice": [
                    "invoice"
                ],
                "payment": [
                    "payment"
                ],
                "refund": [
                    "refund", "return"
                ],
                "feedback": [
                    "feedback"
                ],
                "contact": [
                    "contact"
                ],
                "account": [
                    "account"
                ],
                "delivery": [
                    "delivery"
                ],
                "newsletter": [
                    "newsletter"
                ]
            },
            "version_1": {
                "order": [
                    "order"
                ],
                "shipping_address": [
                    "shipping address"
                ],
                "cancellation_fee": [
                    "cancellation fee"
                ],
                "invoice": [
                    "invoice"
                ],
                "payment": [
                    "payment"
                ],
                "refund": [
                    "refund", "return"
                ],
                "feedback": [
                    "feedback"
                ],
                "contact": [
                    "contact"
                ],
                "account": [
                    "account"
                ],
                "delivery": [
                    "delivery"
                ],
                "newsletter": [
                    "newsletter"
                ]
            },
            "version_2": {
                "order": [
                    "Order"
                ],
                "shipping_address": [
                    "Shipping Address"
                ],
                "cancellation_fee": [
                    "Cancellation Fee"
                ],
                "invoice": [
                    "Invoice"
                ],
                "payment": [
                    "Payment"
                ],
                "refund": [
                    "Refund", "Return"
                ],
                "feedback": [
                    "Feedback"
                ],
                "contact": [
                    "Contact"
                ],
                "account": [
                    "Account"
                ],
                "delivery": [
                    "Delivery"
                ],
                "newsletter": [
                    "Newsletter"
                ]
            },
            "version_3": {
                "order": [
                    "Order"
                ],
                "shipping_address": [
                    "ShippingAddress"
                ],
                "cancellation_fee": [
                    "CancellationFee"
                ],
                "invoice": [
                    "Invoice"
                ],
                "payment": [
                    "Payment"
                ],
                "refund": [
                    "Refund", "Return"
                ],
                "feedback": [
                    "Feedback"
                ],
                "contact": [
                    "Contact"
                ],
                "account": [
                    "Account"
                ],
                "delivery": [
                    "Delivery"
                ],
                "newsletter": [
                    "Newsletter"
                ]
            },
            "version_4": {
                "order": [
                    "ORDER"
                ],
                "shipping_address": [
                    "SHIPPING_ADDRESS"
                ],
                "cancellation_fee": [
                    "CANCELLATION_FEE"
                ],
                "invoice": [
                    "INVOICE"
                ],
                "payment": [
                    "PAYMENT"
                ],
                "refund": [
                    "REFUND", "RETURN"
                ],
                "feedback": [
                    "FEEDBACK"
                ],
                "contact": [
                    "CONTACT"
                ],
                "account": [
                    "ACCOUNT"
                ],
                "delivery": [
                    "DELIVERY"
                ],
                "newsletter": [
                    "NEWSLETTER"
                ]
            }
        },
        "bi_text27": {
            "version_0": {
                "cancel_order": [
                    "cancel_order"
                ],
                "change_order": [
                    "change_order"
                ],
                "change_shipping_address": [
                    "change_shipping_address"
                ],
                "check_cancellation_fee": [
                    "check_cancellation_fee"
                ],
                "check_invoice": [
                    "check_invoice"
                ],
                "check_payment_methods": [
                    "check_payment_methods"
                ],
                "check_refund_policy": [
                    "check_refund_policy"
                ],
                "complaint": [
                    "complaint"
                ],
                "contact_customer_service": [
                    "contact_customer_service"
                ],
                "contact_human_agent": [
                    "contact_human_agent"
                ],
                "create_account": [
                    "create_account"
                ],
                "delete_account": [
                    "delete_account"
                ],
                "delivery_options": [
                    "delivery_options"
                ],
                "delivery_period": [
                    "delivery_period"
                ],
                "edit_account": [
                    "edit_account"
                ],
                "get_invoice": [
                    "get_invoice"
                ],
                "get_refund": [
                    "get_refund"
                ],
                "newsletter_subscription": [
                    "newsletter_subscription"
                ],
                "payment_issue": [
                    "payment_issue"
                ],
                "place_order": [
                    "place_order"
                ],
                "recover_password": [
                    "recover_password"
                ],
                "registration_problems": [
                    "registration_problems"
                ],
                "review": [
                    "review"
                ],
                "set_up_shipping_address": [
                    "set_up_shipping_address"
                ],
                "switch_account": [
                    "switch_account"
                ],
                "track_order": [
                    "track_order"
                ],
                "track_refund": [
                    "track_refund"
                ]
            },
            "version_1": {
                "cancel_order": [
                    "cancel order"
                ],
                "change_order": [
                    "change order"
                ],
                "change_shipping_address": [
                    "change shipping address"
                ],
                "check_cancellation_fee": [
                    "check cancellation fee"
                ],
                "check_invoice": [
                    "check invoice"
                ],
                "check_payment_methods": [
                    "check payment methods"
                ],
                "check_refund_policy": [
                    "check refund policy"
                ],
                "complaint": [
                    "complaint"
                ],
                "contact_customer_service": [
                    "contact customer service"
                ],
                "contact_human_agent": [
                    "contact human agent"
                ],
                "create_account": [
                    "create account"
                ],
                "delete_account": [
                    "delete account"
                ],
                "delivery_options": [
                    "delivery options"
                ],
                "delivery_period": [
                    "delivery period"
                ],
                "edit_account": [
                    "edit account"
                ],
                "get_invoice": [
                    "get invoice"
                ],
                "get_refund": [
                    "get refund"
                ],
                "newsletter_subscription": [
                    "newsletter subscription"
                ],
                "payment_issue": [
                    "payment issue"
                ],
                "place_order": [
                    "place order"
                ],
                "recover_password": [
                    "recover password"
                ],
                "registration_problems": [
                    "registration problems"
                ],
                "review": [
                    "review"
                ],
                "set_up_shipping_address": [
                    "set up shipping address"
                ],
                "switch_account": [
                    "switch account"
                ],
                "track_order": [
                    "track order"
                ],
                "track_refund": [
                    "track refund"
                ]
            },
            "version_2": {
                "cancel_order": [
                    "Cancel Order"
                ],
                "change_order": [
                    "Change Order"
                ],
                "change_shipping_address": [
                    "Change Shipping Address"
                ],
                "check_cancellation_fee": [
                    "Check Cancellation Fee"
                ],
                "check_invoice": [
                    "Check Invoice"
                ],
                "check_payment_methods": [
                    "Check Payment Methods"
                ],
                "check_refund_policy": [
                    "Check Refund Policy"
                ],
                "complaint": [
                    "Complaint"
                ],
                "contact_customer_service": [
                    "Contact Customer Service"
                ],
                "contact_human_agent": [
                    "Contact Human Agent"
                ],
                "create_account": [
                    "Create Account"
                ],
                "delete_account": [
                    "Delete Account"
                ],
                "delivery_options": [
                    "Delivery Options"
                ],
                "delivery_period": [
                    "Delivery Period"
                ],
                "edit_account": [
                    "Edit Account"
                ],
                "get_invoice": [
                    "Get Invoice"
                ],
                "get_refund": [
                    "Get Refund"
                ],
                "newsletter_subscription": [
                    "Newsletter Subscription"
                ],
                "payment_issue": [
                    "Payment Issue"
                ],
                "place_order": [
                    "Place Order"
                ],
                "recover_password": [
                    "Recover Password"
                ],
                "registration_problems": [
                    "Registration Problems"
                ],
                "review": [
                    "Review"
                ],
                "set_up_shipping_address": [
                    "Set Up Shipping Address"
                ],
                "switch_account": [
                    "Switch Account"
                ],
                "track_order": [
                    "Track Order"
                ],
                "track_refund": [
                    "Track Refund"
                ]
            },
            "version_3": {
                "cancel_order": [
                    "CancelOrder"
                ],
                "change_order": [
                    "ChangeOrder"
                ],
                "change_shipping_address": [
                    "ChangeShippingAddress"
                ],
                "check_cancellation_fee": [
                    "CheckCancellationFee"
                ],
                "check_invoice": [
                    "CheckInvoice"
                ],
                "check_payment_methods": [
                    "CheckPaymentMethods"
                ],
                "check_refund_policy": [
                    "CheckRefundPolicy"
                ],
                "complaint": [
                    "Complaint"
                ],
                "contact_customer_service": [
                    "ContactCustomerService"
                ],
                "contact_human_agent": [
                    "ContactHumanAgent"
                ],
                "create_account": [
                    "CreateAccount"
                ],
                "delete_account": [
                    "DeleteAccount"
                ],
                "delivery_options": [
                    "DeliveryOptions"
                ],
                "delivery_period": [
                    "DeliveryPeriod"
                ],
                "edit_account": [
                    "EditAccount"
                ],
                "get_invoice": [
                    "GetInvoice"
                ],
                "get_refund": [
                    "GetRefund"
                ],
                "newsletter_subscription": [
                    "NewsletterSubscription"
                ],
                "payment_issue": [
                    "PaymentIssue"
                ],
                "place_order": [
                    "PlaceOrder"
                ],
                "recover_password": [
                    "RecoverPassword"
                ],
                "registration_problems": [
                    "RegistrationProblems"
                ],
                "review": [
                    "Review"
                ],
                "set_up_shipping_address": [
                    "SetUpShippingAddress"
                ],
                "switch_account": [
                    "SwitchAccount"
                ],
                "track_order": [
                    "TrackOrder"
                ],
                "track_refund": [
                    "TrackRefund"
                ]
            },
            "version_4": {
                "cancel_order": [
                    "CANCEL_ORDER"
                ],
                "change_order": [
                    "CHANGE_ORDER"
                ],
                "change_shipping_address": [
                    "CHANGE_SHIPPING_ADDRESS"
                ],
                "check_cancellation_fee": [
                    "CHECK_CANCELLATION_FEE"
                ],
                "check_invoice": [
                    "CHECK_INVOICE"
                ],
                "check_payment_methods": [
                    "CHECK_PAYMENT_METHODS"
                ],
                "check_refund_policy": [
                    "CHECK_REFUND_POLICY"
                ],
                "complaint": [
                    "COMPLAINT"
                ],
                "contact_customer_service": [
                    "CONTACT_CUSTOMER_SERVICE"
                ],
                "contact_human_agent": [
                    "CONTACT_HUMAN_AGENT"
                ],
                "create_account": [
                    "CREATE_ACCOUNT"
                ],
                "delete_account": [
                    "DELETE_ACCOUNT"
                ],
                "delivery_options": [
                    "DELIVERY_OPTIONS"
                ],
                "delivery_period": [
                    "DELIVERY_PERIOD"
                ],
                "edit_account": [
                    "EDIT_ACCOUNT"
                ],
                "get_invoice": [
                    "GET_INVOICE"
                ],
                "get_refund": [
                    "GET_REFUND"
                ],
                "newsletter_subscription": [
                    "NEWSLETTER_SUBSCRIPTION"
                ],
                "payment_issue": [
                    "PAYMENT_ISSUE"
                ],
                "place_order": [
                    "PLACE_ORDER"
                ],
                "recover_password": [
                    "RECOVER_PASSWORD"
                ],
                "registration_problems": [
                    "REGISTRATION_PROBLEMS"
                ],
                "review": [
                    "REVIEW"
                ],
                "set_up_shipping_address": [
                    "SET_UP_SHIPPING_ADDRESS"
                ],
                "switch_account": [
                    "SWITCH_ACCOUNT"
                ],
                "track_order": [
                    "TRACK_ORDER"
                ],
                "track_refund": [
                    "TRACK_REFUND"
                ]
            }
        },
        "book6": {
            "version_0": {
                "BookRestaurant": ["BookRestaurant"],
                "GetWeather": ["GetWeather"],
                "RateBook": ["RateBook"],
                "AddToPlaylist": ["AddToPlaylist"],
                "SearchScreeningEvent": ["SearchScreeningEvent"],
                "SearchCreativeWork": ["SearchCreativeWork"],
            },
            "version_1": {
                "BookRestaurant": ["Book Restaurant"],
                "GetWeather": ["Get Weather"],
                "RateBook": ["Rate Book"],
                "AddToPlaylist": ["Add To Playlist"],
                "SearchScreeningEvent": ["Search Screening Event"],
                "SearchCreativeWork": ["Search Creative Work"],
            },
            "version_2": {
                "BookRestaurant": ["book restaurant"],
                "GetWeather": ["get weather"],
                "RateBook": ["rate book"],
                "AddToPlaylist": ["add to playlist"],
                "SearchScreeningEvent": ["search screening event"],
                "SearchCreativeWork": ["search creative work"],
            },
            "version_3": {
                "BookRestaurant": ["book_restaurant"],
                "GetWeather": ["get_weather"],
                "RateBook": ["rate_book"],
                "AddToPlaylist": ["add_to_playlist"],
                "SearchScreeningEvent": ["search_screening_event"],
                "SearchCreativeWork": ["search_creative_work"],
            },
        },
        "carer": {
            "version_0": {
                "sadness": [
                    "sadness"
                ],
                "joy": [
                    "joy"
                ],
                "love": [
                    "love"
                ],
                "anger": [
                    "anger"
                ],
                "fear": [
                    "fear"
                ],
                "surprise": [
                    "surprise"
                ]
            },
            "version_1": {
                "sadness": [
                    "Sadness"
                ],
                "joy": [
                    "Joy"
                ],
                "love": [
                    "Love"
                ],
                "anger": [
                    "Anger"
                ],
                "fear": [
                    "Fear"
                ],
                "surprise": [
                    "Surprise"
                ]
            }
        },
        "chatbots": {
            "version_0": {
                "Greeting": ["Greeting", "Greet"],
                "GreetingResponse": ["GreetingResponse"],
                "CourtesyGreeting": ["CourtesyGreeting"],
                "CourtesyGreetingResponse": ["CourtesyGreetingResponse"],
                "CurrentHumanQuery": ["CurrentHumanQuery"],
                "NameQuery": ["NameQuery"],
                "RealNameQuery": ["RealNameQuery"],
                "TimeQuery": ["TimeQuery"],
                "Thanks": ["Thanks"],
                "NotTalking2U": ["NotTalking2U"],
                "UnderstandQuery": ["UnderstandQuery"],
                "Shutup": ["Shutup"],
                "Swearing": ["Swearing"],
                "GoodBye": ["GoodBye"],
                "CourtesyGoodBye": ["CourtesyGoodBye"],
                "WhoAmI": ["WhoAmI"],
                "Clever": ["Clever"],
                "Gossip": ["Gossip"],
                "Jokes": ["Jokes"],
                "PodBayDoor": ["PodBayDoor"],
                "PodBayDoorResponse": ["PodBayDoorResponse"],
                "SelfAware": ["SelfAware"],
            },
            "version_1": {
                "Greeting": ["Greeting", "Greet"],
                "GreetingResponse": ["Greeting Response"],
                "CourtesyGreeting": ["Courtesy Greeting"],
                "CourtesyGreetingResponse": ["Courtesy Greeting Response"],
                "CurrentHumanQuery": ["Current Human Query"],
                "NameQuery": ["Name Query"],
                "RealNameQuery": ["Real Name Query"],
                "TimeQuery": ["Time Query"],
                "Thanks": ["Thanks"],
                "NotTalking2U": ["Not Talking To You"],
                "UnderstandQuery": ["Understand Query"],
                "Shutup": ["Shut Up"],
                "Swearing": ["Swearing"],
                "GoodBye": ["Good Bye"],
                "CourtesyGoodBye": ["Courtesy Good Bye"],
                "WhoAmI": ["Who Am I"],
                "Clever": ["Clever"],
                "Gossip": ["Gossip"],
                "Jokes": ["Jokes"],
                "PodBayDoor": ["Pod Bay Door"],
                "PodBayDoorResponse": ["Pod Bay Door Response"],
                "SelfAware": ["Self Aware"],
            }
        },
        "chinese_news_title": {
            "version_0": {
                "health": [
                    "health"
                ],
                "joke": [
                    "joke"
                ],
                "digi": [
                    "digi"
                ],
                "constellation": [
                    "constellation"
                ],
                "movie": [
                    "movie"
                ],
                "star": [
                    "star"
                ],
                "science": [
                    "science"
                ],
                "photo": [
                    "photo"
                ],
                "pet": [
                    "pet"
                ],
                "music": [
                    "music"
                ],
                "sex": [
                    "sex"
                ],
                "design": [
                    "design"
                ],
                "baby": [
                    "baby"
                ],
                "education": [
                    "education"
                ],
                "drama": [
                    "drama"
                ],
                "it": [
                    "it", "information_technology"
                ],
                "comic": [
                    "comic"
                ],
                "manage": [
                    "manage"
                ],
                "money": [
                    "money"
                ],
                "lottery": [
                    "lottery"
                ],
                "sports": [
                    "sports"
                ],
                "beauty": [
                    "beauty"
                ],
                "game": [
                    "game"
                ],
                "news": [
                    "news"
                ],
                "house": [
                    "house"
                ],
                "dress": [
                    "dress"
                ],
                "travel": [
                    "travel"
                ],
                "mass_communication": [
                    "mass_communication"
                ],
                "food": [
                    "food"
                ],
                "car": [
                    "car"
                ],
                "tv": [
                    "tv"
                ],
                "cultural": [
                    "cultural"
                ]
            },
            "version_1": {
                "health": [
                    "health"
                ],
                "joke": [
                    "joke"
                ],
                "digi": [
                    "digi"
                ],
                "constellation": [
                    "constellation"
                ],
                "movie": [
                    "movie"
                ],
                "star": [
                    "star"
                ],
                "science": [
                    "science"
                ],
                "photo": [
                    "photo"
                ],
                "pet": [
                    "pet"
                ],
                "music": [
                    "music"
                ],
                "sex": [
                    "sex"
                ],
                "design": [
                    "design"
                ],
                "baby": [
                    "baby"
                ],
                "education": [
                    "education"
                ],
                "drama": [
                    "drama"
                ],
                "it": [
                    "it", "information technology"
                ],
                "comic": [
                    "comic"
                ],
                "manage": [
                    "manage"
                ],
                "money": [
                    "money"
                ],
                "lottery": [
                    "lottery"
                ],
                "sports": [
                    "sports"
                ],
                "beauty": [
                    "beauty"
                ],
                "game": [
                    "game"
                ],
                "news": [
                    "news"
                ],
                "house": [
                    "house"
                ],
                "dress": [
                    "dress"
                ],
                "travel": [
                    "travel"
                ],
                "mass_communication": [
                    "mass communication"
                ],
                "food": [
                    "food"
                ],
                "car": [
                    "car"
                ],
                "tv": [
                    "tv"
                ],
                "cultural": [
                    "cultural"
                ]
            },
            "version_2": {
                "health": [
                    "Health"
                ],
                "joke": [
                    "Joke"
                ],
                "digi": [
                    "Digi"
                ],
                "constellation": [
                    "Constellation"
                ],
                "movie": [
                    "Movie"
                ],
                "star": [
                    "Star"
                ],
                "science": [
                    "Science"
                ],
                "photo": [
                    "Photo"
                ],
                "pet": [
                    "Pet"
                ],
                "music": [
                    "Music"
                ],
                "sex": [
                    "Sex"
                ],
                "design": [
                    "Design"
                ],
                "baby": [
                    "Baby"
                ],
                "education": [
                    "Education"
                ],
                "drama": [
                    "Drama"
                ],
                "it": [
                    "Information Technology"
                ],
                "comic": [
                    "Comic"
                ],
                "manage": [
                    "Manage"
                ],
                "money": [
                    "Money"
                ],
                "lottery": [
                    "Lottery"
                ],
                "sports": [
                    "Sports"
                ],
                "beauty": [
                    "Beauty"
                ],
                "game": [
                    "Game"
                ],
                "news": [
                    "News"
                ],
                "house": [
                    "House"
                ],
                "dress": [
                    "Dress"
                ],
                "travel": [
                    "Travel"
                ],
                "mass_communication": [
                    "Mass Communication"
                ],
                "food": [
                    "Food"
                ],
                "car": [
                    "Car"
                ],
                "tv": [
                    "Tv"
                ],
                "cultural": [
                    "Cultural"
                ]
            },
            "version_3": {
                "health": [
                    "Health"
                ],
                "joke": [
                    "Joke"
                ],
                "digi": [
                    "Digi"
                ],
                "constellation": [
                    "Constellation"
                ],
                "movie": [
                    "Movie"
                ],
                "star": [
                    "Star"
                ],
                "science": [
                    "Science"
                ],
                "photo": [
                    "Photo"
                ],
                "pet": [
                    "Pet"
                ],
                "music": [
                    "Music"
                ],
                "sex": [
                    "Sex"
                ],
                "design": [
                    "Design"
                ],
                "baby": [
                    "Baby"
                ],
                "education": [
                    "Education"
                ],
                "drama": [
                    "Drama"
                ],
                "it": [
                    "It", "InformationTechnology"
                ],
                "comic": [
                    "Comic"
                ],
                "manage": [
                    "Manage"
                ],
                "money": [
                    "Money"
                ],
                "lottery": [
                    "Lottery"
                ],
                "sports": [
                    "Sports"
                ],
                "beauty": [
                    "Beauty"
                ],
                "game": [
                    "Game"
                ],
                "news": [
                    "News"
                ],
                "house": [
                    "House"
                ],
                "dress": [
                    "Dress"
                ],
                "travel": [
                    "Travel"
                ],
                "mass_communication": [
                    "MassCommunication"
                ],
                "food": [
                    "Food"
                ],
                "car": [
                    "Car"
                ],
                "tv": [
                    "Tv"
                ],
                "cultural": [
                    "Cultural"
                ]
            },
            "version_4": {
                "health": [
                    "HEALTH"
                ],
                "joke": [
                    "JOKE"
                ],
                "digi": [
                    "DIGI"
                ],
                "constellation": [
                    "CONSTELLATION"
                ],
                "movie": [
                    "MOVIE"
                ],
                "star": [
                    "STAR"
                ],
                "science": [
                    "SCIENCE"
                ],
                "photo": [
                    "PHOTO"
                ],
                "pet": [
                    "PET"
                ],
                "music": [
                    "MUSIC"
                ],
                "sex": [
                    "SEX"
                ],
                "design": [
                    "DESIGN"
                ],
                "baby": [
                    "BABY"
                ],
                "education": [
                    "EDUCATION"
                ],
                "drama": [
                    "DRAMA"
                ],
                "it": [
                    "IT", "INFORMATION TECHNOLOGY"
                ],
                "comic": [
                    "COMIC"
                ],
                "manage": [
                    "MANAGE"
                ],
                "money": [
                    "MONEY"
                ],
                "lottery": [
                    "LOTTERY"
                ],
                "sports": [
                    "SPORTS"
                ],
                "beauty": [
                    "BEAUTY"
                ],
                "game": [
                    "GAME"
                ],
                "news": [
                    "NEWS"
                ],
                "house": [
                    "HOUSE"
                ],
                "dress": [
                    "DRESS"
                ],
                "travel": [
                    "TRAVEL"
                ],
                "mass_communication": [
                    "MASS_COMMUNICATION"
                ],
                "food": [
                    "FOOD"
                ],
                "car": [
                    "CAR"
                ],
                "tv": [
                    "TV"
                ],
                "cultural": [
                    "CULTURAL"
                ]
            },
            "version_5": {
                "health": [
                    "健康"
                ],
                "joke": [
                    "玩笑"
                ],
                "digi": [
                    "数码"
                ],
                "constellation": [
                    "星座"
                ],
                "movie": [
                    "电影"
                ],
                "star": [
                    "明星"
                ],
                "science": [
                    "科学"
                ],
                "photo": [
                    "照片", "摄影"
                ],
                "pet": [
                    "宠物"
                ],
                "music": [
                    "音乐"
                ],
                "sex": [
                    "两性"
                ],
                "design": [
                    "设计"
                ],
                "baby": [
                    "婴儿", "孩子", "育儿"
                ],
                "education": [
                    "教育", "教学"
                ],
                "drama": [
                    "戏剧", "戏曲"
                ],
                "it": [
                    "IT", "编程", "信息技术"
                ],
                "comic": [
                    "漫画"
                ],
                "manage": [
                    "管理", "经营"
                ],
                "money": [
                    "金钱", "钱财", "财富"
                ],
                "lottery": [
                    "彩票", "抽奖"
                ],
                "sports": [
                    "体育", "运动"
                ],
                "beauty": [
                    "美妆", "美丽"
                ],
                "game": [
                    "游戏"
                ],
                "news": [
                    "消息", "新闻"
                ],
                "house": [
                    "房子", "住宅", "居家"
                ],
                "dress": [
                    "穿搭"
                ],
                "travel": [
                    "旅行", "旅游"
                ],
                "mass_communication": [
                    "大众传播", "大众传媒"
                ],
                "food": [
                    "食物", "食品", "美食"
                ],
                "car": [
                    "汽车"
                ],
                "tv": [
                    "电视", "电视剧"
                ],
                "cultural": [
                    "文化"
                ]
            },
        },
        "cmid_4class": {
            "version_0": {
                "病症": ["病症"],
                "药物": ["药物"],
                "其他": ["其他"],
                "治疗方案": ["治疗方案"],
            }
        },
        "cmid_36class": {
            "version_0": {
                "治疗方法": [
                    "治疗方法"
                ],
                "定义": [
                    "定义"
                ],
                "临床表现(病症表现)": [
                    "临床表现(病症表现)"
                ],
                "适用症": [
                    "适用症"
                ],
                "无法确定": [
                    "无法确定"
                ],
                "禁忌": [
                    "禁忌"
                ],
                "相关病症": [
                    "相关病症"
                ],
                "对比": [
                    "对比"
                ],
                "副作用": [
                    "副作用"
                ],
                "多问": [
                    "多问"
                ],
                "病因": [
                    "病因"
                ],
                "化验/体检方案": [
                    "化验/体检方案"
                ],
                "恢复": [
                    "恢复"
                ],
                "严重性": [
                    "严重性"
                ],
                "治愈率": [
                    "治愈率"
                ],
                "用法": [
                    "用法"
                ],
                "功效": [
                    "功效"
                ],
                "两性": [
                    "两性"
                ],
                "正常指标": [
                    "正常指标"
                ],
                "养生": [
                    "养生"
                ],
                "方法": [
                    "方法"
                ],
                "传染性": [
                    "传染性"
                ],
                "成分": [
                    "成分"
                ],
                "预防": [
                    "预防"
                ],
                "恢复时间": [
                    "恢复时间"
                ],
                "推荐医院": [
                    "推荐医院"
                ],
                "费用": [
                    "费用"
                ],
                "临床意义/检查目的": [
                    "临床意义/检查目的"
                ],
                "设备用法": [
                    "设备用法"
                ],
                "疗效": [
                    "疗效"
                ],
                "作用": [
                    "作用"
                ],
                "价钱": [
                    "价钱"
                ],
                "有效时间": [
                    "有效时间"
                ],
                "整容": [
                    "整容"
                ],
                "所属科室": [
                    "所属科室"
                ],
                "治疗时间": [
                    "治疗时间"
                ],
                "药物禁忌": [
                    "药物禁忌"
                ],
                "病症禁忌": [
                    "病症禁忌"
                ],
                "诱因": [
                    "诱因"
                ],
                "手术时间": [
                    "手术时间"
                ]
            }
        },
        "coig_cqia": {
            "version_0": {
                "成语释义": [
                    "成语释义"
                ],
                "古诗续写": [
                    "古诗续写"
                ],
                "文言文翻译": [
                    "文言文翻译"
                ],
                "命名实体识别": [
                    "命名实体识别"
                ],
                "中文分词": [
                    "中文分词"
                ],
                "情感分类": [
                    "情感分类"
                ],
                "依存句法分析": [
                    "依存句法分析"
                ],
                "论元抽取": [
                    "论元抽取"
                ],
                "事件类型分类": [
                    "事件类型分类"
                ],
                "问题生成": [
                    "问题生成",
                ],
                "SQL": [
                    "SQL生成"
                ],
                "主题分类": [
                    "主题分类"
                ],
                "句子重写": [
                    "句子重写"
                ],
                "特殊格式": [
                    "特殊格式"
                ],
                "语义相关性": [
                    "语义相关性"
                ],
                "古诗词": [
                    "古诗词",
                ],
                "实体判断": [
                    "实体判断"
                ],
                "文本扩写": [
                    "文本扩写",
                ],
                "意图分析": [
                    "意图分析",
                ],
                "有效性判断": [
                    "有效性判断"
                ],
                "情感分析": [
                    "情感分析"
                ],
                "语法纠错": [
                    "语法纠错"
                ],
                "信息检索": [
                    "信息检索"
                ],
                "简繁体转换": [
                    "简繁体转换"
                ],
                "同义词": [
                    "同义词"
                ],
                "信息抽取": [
                    "信息抽取"
                ],
                "语义分析": [
                    "语义分析"
                ],
                "翻译": [
                    "翻译"
                ],
                "实体抽取": [
                    "实体抽取",
                ],
                "因果分析": [
                    "因果分析"
                ],
                "文本生成": [
                    "文本生成",
                ],
                "事件抽取": [
                    "事件抽取"
                ],
                "对联": [
                    "对联"
                ],
                "语义分割": [
                    "语义分割"
                ],
                "关键词生成": [
                    "关键词生成"
                ],
                "论文门类分类": [
                    "论文门类分类"
                ],
                "论文学科分类": [
                    "论文学科分类"
                ],
                "同义替换": [
                    "同义替换"
                ],
                "标题生成": [
                    "标题生成"
                ],
                "对话补全": [
                    "对话补全"
                ],
                "错别字": [
                    "错别字"
                ],
                "医疗诊断": [
                    "医疗诊断"
                ],
                "完形填空": [
                    "完形填空"
                ],
                "原子编辑": [
                    "原子编辑"
                ],
                "图书介绍": [
                    "图书介绍"
                ],
                "作者介绍": [
                    "作者介绍"
                ],
                "故事概要": [
                    "故事概要",
                ],
                "电影推荐": [
                    "电影推荐"
                ],
                "电视剧推荐": [
                    "电视剧推荐"
                ],
                "中学考试": [
                    "中学考试"
                ],
                "法律考研": [
                    "法律考研",
                ],
                "论元角色分类": [
                    "论元角色分类"
                ],
                "代码问答": [
                    "代码问答"
                ],
                "医药问答": [
                    "医药问答",
                ],
            }
        },
        "conv_intent": {
            "version_0": {
                "RateBook": [
                    "RateBook"
                ],
                "SearchCreativeWork": [
                    "SearchCreativeWork"
                ],
                "BookRestaurant": [
                    "BookRestaurant"
                ],
                "GetWeather": [
                    "GetWeather"
                ],
                "SearchScreeningEvent": [
                    "SearchScreeningEvent"
                ],
                "AddToPlaylist": [
                    "AddToPlaylist"
                ],
                "PlayMusic": [
                    "PlayMusic"
                ]
            },
            "version_1": {
                "RateBook": [
                    "RateBook"
                ],
                "SearchCreativeWork": [
                    "SearchCreativeWork"
                ],
                "BookRestaurant": [
                    "BookRestaurant"
                ],
                "GetWeather": [
                    "GetWeather"
                ],
                "SearchScreeningEvent": [
                    "SearchScreeningEvent"
                ],
                "AddToPlaylist": [
                    "AddToPlaylist"
                ],
                "PlayMusic": [
                    "PlayMusic"
                ]
            },
            "version_2": {
                "RateBook": [
                    "RateBook"
                ],
                "SearchCreativeWork": [
                    "SearchCreativeWork"
                ],
                "BookRestaurant": [
                    "BookRestaurant"
                ],
                "GetWeather": [
                    "GetWeather"
                ],
                "SearchScreeningEvent": [
                    "SearchScreeningEvent"
                ],
                "AddToPlaylist": [
                    "AddToPlaylist"
                ],
                "PlayMusic": [
                    "PlayMusic"
                ]
            },
            "version_3": {
                "RateBook": [
                    "RateBook"
                ],
                "SearchCreativeWork": [
                    "SearchCreativeWork"
                ],
                "BookRestaurant": [
                    "BookRestaurant"
                ],
                "GetWeather": [
                    "GetWeather"
                ],
                "SearchScreeningEvent": [
                    "SearchScreeningEvent"
                ],
                "AddToPlaylist": [
                    "AddToPlaylist"
                ],
                "PlayMusic": [
                    "PlayMusic"
                ]
            }
        },
        "crosswoz": {
            "version_0": {
                "greet": ["打招呼"],
                "thank": ["感谢"],
                "bye": ["拜拜", "结束"]
            },
            "version_1": {
                "greet": ["greet"],
                "thank": ["thank"],
                "bye": ["bye"]
            },
            "version_2": {
                "greet": ["招呼用语"],
                "thank": ["感谢用语"],
                "bye": ["结束用语"]
            },
            "version_3": {
                "greet": ["问候语", "招呼语"],
                "thank": ["感谢语"],
                "bye": ["结束语"]
            },
        },
        "dmslots": {
            "version_0": {
                "domain.dialog.chat": ["chat"],
                "domain.dialog.complain": ["complain"],
                "domain.dialog.kgsearch": ["knowledge graph search"],
                "domain.dialog.lbs": ["location-based services", "location based services"],
                "domain.dialog.manual": ["dialog manual"],
                "domain.dialog.other": ["dialog other"],
                "domain.dialog.status": ["status"],
                "domain.dialog.traffic": ["traffic"],
                "domain.dialog.weather": ["weather"],
                "domain.op.app": ["operate app"],
                "domain.op.booking": ["booking"],
                "domain.op.control": ["control"],
                "domain.op.geonavi": ["geographic navigation"],
                "domain.op.media.fm": ["fm"],
                "domain.op.media.music": ["music"],
                "domain.op.media.news": ["news"],
                "domain.op.media.video": ["video"],
                "domain.op.msgcall": ["message call"],
                "domain.op.other": ["operate other"]

            },
            "version_1": {
                "domain.dialog.chat": ["chat"],
                "domain.dialog.complain": ["complain"],
                "domain.dialog.kgsearch": ["knowledge graph search"],
                "domain.dialog.lbs": ["location-based services", "location based services"],
                "domain.dialog.manual": ["manual"],
                "domain.dialog.other": ["other"],
                "domain.dialog.status": ["status"],
                "domain.dialog.traffic": ["traffic"],
                "domain.dialog.weather": ["weather"],
                "domain.op.app": ["operate app"],
                "domain.op.booking": ["booking"],
                "domain.op.control": ["control"],
                "domain.op.geonavi": ["geographic navigation"],
                "domain.op.media.fm": ["media fm"],
                "domain.op.media.music": ["media music"],
                "domain.op.media.news": ["media news"],
                "domain.op.media.video": ["media video"],
                "domain.op.msgcall": ["message call"],
                "domain.op.other": ["operate other"]

            },
            "version_2": {
                "domain.dialog.chat": ["Chat"],
                "domain.dialog.complain": ["Complain"],
                "domain.dialog.kgsearch": ["Knowledge Graph Search"],
                "domain.dialog.lbs": ["Location-based Services", "Location Based Services"],
                "domain.dialog.manual": ["Dialog Manual"],
                "domain.dialog.other": ["Dialog Other"],
                "domain.dialog.status": ["Status"],
                "domain.dialog.traffic": ["Traffic"],
                "domain.dialog.weather": ["Weather"],
                "domain.op.app": ["Operate App"],
                "domain.op.booking": ["Booking"],
                "domain.op.control": ["Control"],
                "domain.op.geonavi": ["Geographic Navigation"],
                "domain.op.media.fm": ["FM"],
                "domain.op.media.music": ["Music"],
                "domain.op.media.news": ["News"],
                "domain.op.media.video": ["Video"],
                "domain.op.msgcall": ["Message Call"],
                "domain.op.other": ["Operate Other"]

            },
            "version_3": {
                "domain.dialog.chat": ["Dialog Chat"],
                "domain.dialog.complain": ["Dialog Complain"],
                "domain.dialog.kgsearch": ["Dialog Knowledge Graph Search"],
                "domain.dialog.lbs": ["Dialog Location-based Services", "Dialog Location Based Services"],
                "domain.dialog.manual": ["Dialog Manual"],
                "domain.dialog.other": ["Dialog Other"],
                "domain.dialog.status": ["Dialog Status"],
                "domain.dialog.traffic": ["Dialog Traffic"],
                "domain.dialog.weather": ["Dialog Weather"],
                "domain.op.app": ["Operate App"],
                "domain.op.booking": ["Operate Booking"],
                "domain.op.control": ["Operate Control"],
                "domain.op.geonavi": ["Operate Geographic Navigation"],
                "domain.op.media.fm": ["Operate Media FM"],
                "domain.op.media.music": ["Operate Media Music"],
                "domain.op.media.news": ["Operate Media News"],
                "domain.op.media.video": ["Operate Media Video"],
                "domain.op.msgcall": ["Operate Message Call"],
                "domain.op.other": ["Operate Other"]

            },
            "version_4": {
                "domain.dialog.chat": ["闲聊"],
                "domain.dialog.complain": ["抱怨", "辱骂"],
                "domain.dialog.kgsearch": ["知识库搜索", "查询知识库"],
                "domain.dialog.lbs": ["本地服务"],
                "domain.dialog.manual": ["查询手册"],
                "domain.dialog.other": ["其他对话主题", "其它对话主题"],
                "domain.dialog.status": ["查询状态"],
                "domain.dialog.traffic": ["查询路况", "查询交通状况"],
                "domain.dialog.weather": ["查询天气"],
                "domain.op.app": ["操作App", "App操作"],
                "domain.op.booking": ["预订"],
                "domain.op.control": ["控制"],
                "domain.op.geonavi": ["地理导航", "地图导航"],
                "domain.op.media.fm": ["操作FM", "操作广播"],
                "domain.op.media.music": ["音乐", "操作音乐"],
                "domain.op.media.news": ["新闻", "操作新闻"],
                "domain.op.media.video": ["视频", "操作视频"],
                "domain.op.msgcall": ["打电话", "操作呼叫"],
                "domain.op.other": ["其他操作", "其它操作"]

            },
        },
        "dnd_style_intents": {
            "version_0": {
                "joke": [
                    "joke"
                ],
                "protect": [
                    "protect"
                ],
                "drival": [
                    "drival"
                ],
                "follow": [
                    "follow"
                ],
                "farewell": [
                    "farewell"
                ],
                "join": [
                    "join"
                ],
                "deliver": [
                    "deliver"
                ],
                "attack": [
                    "attack"
                ],
                "threat": [
                    "threat"
                ],
                "greeting": [
                    "greeting"
                ],
                "general": [
                    "general"
                ],
                "exchange": [
                    "exchange"
                ],
                "recieve quest": [
                    "recieve quest"
                ],
                "complete quest": [
                    "complete quest"
                ],
                "message": [
                    "message"
                ],
                "knowledge": [
                    "knowledge"
                ],
                "move": [
                    "move"
                ]
            },
            "version_1": {
                "joke": [
                    "joke"
                ],
                "protect": [
                    "protect"
                ],
                "drival": [
                    "drival"
                ],
                "follow": [
                    "follow"
                ],
                "farewell": [
                    "farewell"
                ],
                "join": [
                    "join"
                ],
                "deliver": [
                    "deliver"
                ],
                "attack": [
                    "attack"
                ],
                "threat": [
                    "threat"
                ],
                "greeting": [
                    "greeting"
                ],
                "general": [
                    "general"
                ],
                "exchange": [
                    "exchange"
                ],
                "recieve quest": [
                    "recieve_quest"
                ],
                "complete quest": [
                    "complete_quest"
                ],
                "message": [
                    "message"
                ],
                "knowledge": [
                    "knowledge"
                ],
                "move": [
                    "move"
                ]
            },
            "version_2": {
                "joke": [
                    "Joke"
                ],
                "protect": [
                    "Protect"
                ],
                "drival": [
                    "Drival"
                ],
                "follow": [
                    "Follow"
                ],
                "farewell": [
                    "Farewell"
                ],
                "join": [
                    "Join"
                ],
                "deliver": [
                    "Deliver"
                ],
                "attack": [
                    "Attack"
                ],
                "threat": [
                    "Threat"
                ],
                "greeting": [
                    "Greeting"
                ],
                "general": [
                    "General"
                ],
                "exchange": [
                    "Exchange"
                ],
                "recieve quest": [
                    "Recieve Quest"
                ],
                "complete quest": [
                    "Complete Quest"
                ],
                "message": [
                    "Message"
                ],
                "knowledge": [
                    "Knowledge"
                ],
                "move": [
                    "Move"
                ]
            },
            "version_3": {
                "joke": [
                    "Joke"
                ],
                "protect": [
                    "Protect"
                ],
                "drival": [
                    "Drival"
                ],
                "follow": [
                    "Follow"
                ],
                "farewell": [
                    "Farewell"
                ],
                "join": [
                    "Join"
                ],
                "deliver": [
                    "Deliver"
                ],
                "attack": [
                    "Attack"
                ],
                "threat": [
                    "Threat"
                ],
                "greeting": [
                    "Greeting"
                ],
                "general": [
                    "General"
                ],
                "exchange": [
                    "Exchange"
                ],
                "recieve quest": [
                    "RecieveQuest"
                ],
                "complete quest": [
                    "CompleteQuest"
                ],
                "message": [
                    "Message"
                ],
                "knowledge": [
                    "Knowledge"
                ],
                "move": [
                    "Move"
                ]
            },
            "version_4": {
                "joke": [
                    "JOKE"
                ],
                "protect": [
                    "PROTECT"
                ],
                "drival": [
                    "DRIVAL"
                ],
                "follow": [
                    "FOLLOW"
                ],
                "farewell": [
                    "FAREWELL"
                ],
                "join": [
                    "JOIN"
                ],
                "deliver": [
                    "DELIVER"
                ],
                "attack": [
                    "ATTACK"
                ],
                "threat": [
                    "THREAT"
                ],
                "greeting": [
                    "GREETING"
                ],
                "general": [
                    "GENERAL"
                ],
                "exchange": [
                    "EXCHANGE"
                ],
                "recieve quest": [
                    "RECIEVE QUEST"
                ],
                "complete quest": [
                    "COMPLETE QUEST"
                ],
                "message": [
                    "MESSAGE"
                ],
                "knowledge": [
                    "KNOWLEDGE"
                ],
                "move": [
                    "MOVE"
                ]
            }
        },
        "emo2019": {
            "version_0": {
                "others": [
                    "others", "other", "other emotion", "other label", "other emotion label"
                ],
                "happy": [
                    "happy"
                ],
                "sad": [
                    "sad"
                ],
                "angry": [
                    "angry"
                ]
            }
        },
        "finance21": {
            "version_0": {
                "commonQ.assist": ["Ask for help"],
                "commonQ.bot": ["Is it a robot"],
                "commonQ.how": ["Question how"],
                "commonQ.just_details": ["Just details"],
                "commonQ.name": ["Ask name"],
                "commonQ.not_giving": ["Not giving"],
                "commonQ.query": ["I have a question"],
                "commonQ.wait": ["Wait a minute"],
                "contact.contact": ["Ask contact info"],
                "faq.aadhaar_missing": ["Aadhaar missing"],
                "faq.address_proof": ["Address proof"],
                "faq.application_process": ["Query process"],
                "faq.apply_register": ["Apply register"],
                "faq.approval_time": ["Approval time"],
                "faq.bad_service": ["Bad service"],
                "faq.banking_option_missing": ["Banking option missing"],
                "faq.biz_category_missing": ["Business category missing"],
                "faq.biz_new": ["Business new"],
                "faq.biz_simpler": ["Business simpler"],
                "faq.borrow_limit": ["Borrow limit"],
                "faq.borrow_use": ["Borrow use", "Borrow usage"]
            },
            "version_1": {
                "commonQ.assist": ["I Need Help"],
                "commonQ.bot": ["Are You A Robot"],
                "commonQ.how": ["Question How"],
                "commonQ.just_details": ["Just Details"],
                "commonQ.name": ["Ask For Name"],
                "commonQ.not_giving": ["I Refuse"],
                "commonQ.query": ["May I Have A Question"],
                "commonQ.wait": ["Wait A Minute"],
                "contact.contact": ["May I Have Your Contact"],
                "faq.aadhaar_missing": ["Aadhaar Missing"],
                "faq.address_proof": ["Address Proof"],
                "faq.application_process": ["Query Process"],
                "faq.apply_register": ["Apply Register"],
                "faq.approval_time": ["Approval Time", "How About The Approval Time"],
                "faq.bad_service": ["Bad Service"],
                "faq.banking_option_missing": ["Banking Option Missing"],
                "faq.biz_category_missing": ["Business Category Missing"],
                "faq.biz_new": ["New Business"],
                "faq.biz_simpler": ["Business Simpler"],
                "faq.borrow_limit": ["How About The Borrow Limit"],
                "faq.borrow_use": ["How About The Borrow Usage"]
            }
        },
        "hwu_64": {
            "version_0": {
                "music likeness": [
                    "music likeness"
                ],
                "recommendation locations": [
                    "recommendation locations"
                ],
                "general explain": [
                    "general explain"
                ],
                "datetime query": [
                    "datetime query"
                ],
                "cooking recipe": [
                    "cooking recipe"
                ],
                "calendar query": [
                    "calendar query"
                ],
                "email addcontact": [
                    "email addcontact"
                ],
                "general dontcare": [
                    "general dontcare"
                ],
                "iot hue lightdim": [
                    "iot hue lightdim"
                ],
                "play audiobook": [
                    "play audiobook"
                ],
                "play game": [
                    "play game"
                ],
                "social post": [
                    "social post"
                ],
                "recommendation events": [
                    "recommendation events"
                ],
                "email querycontact": [
                    "email querycontact"
                ],
                "transport taxi": [
                    "transport taxi"
                ],
                "play podcasts": [
                    "play podcasts"
                ],
                "weather query": [
                    "weather query"
                ],
                "alarm set": [
                    "alarm set"
                ],
                "audio volume up": [
                    "audio volume up"
                ],
                "email sendemail": [
                    "email sendemail"
                ],
                "music settings": [
                    "music settings"
                ],
                "iot hue lightup": [
                    "iot hue lightup"
                ],
                "iot wemo on": [
                    "iot wemo on"
                ],
                "play music": [
                    "play music"
                ],
                "iot hue lighton": [
                    "iot hue lighton"
                ],
                "transport query": [
                    "transport query"
                ],
                "general repeat": [
                    "general repeat"
                ],
                "qa definition": [
                    "qa definition"
                ],
                "general quirky": [
                    "general quirky"
                ],
                "audio volume down": [
                    "audio volume down"
                ],
                "iot coffee": [
                    "iot coffee"
                ],
                "qa stock": [
                    "qa stock"
                ],
                "takeaway query": [
                    "takeaway query"
                ],
                "general commandstop": [
                    "general commandstop"
                ],
                "transport traffic": [
                    "transport traffic"
                ],
                "lists remove": [
                    "lists remove"
                ],
                "social query": [
                    "social query"
                ],
                "qa factoid": [
                    "qa factoid"
                ],
                "iot wemo off": [
                    "iot wemo off"
                ],
                "calendar set": [
                    "calendar set"
                ],
                "iot hue lightoff": [
                    "iot hue lightoff"
                ],
                "play radio": [
                    "play radio"
                ],
                "takeaway order": [
                    "takeaway order"
                ],
                "qa maths": [
                    "qa maths"
                ],
                "general negate": [
                    "general negate"
                ],
                "alarm remove": [
                    "alarm remove"
                ],
                "general affirm": [
                    "general affirm"
                ],
                "email query": [
                    "email query"
                ],
                "iot cleaning": [
                    "iot cleaning"
                ],
                "transport ticket": [
                    "transport ticket"
                ],
                "general joke": [
                    "general joke"
                ],
                "lists query": [
                    "lists query"
                ],
                "music query": [
                    "music query"
                ],
                "datetime convert": [
                    "datetime convert"
                ],
                "recommendation movies": [
                    "recommendation movies"
                ],
                "general praise": [
                    "general praise"
                ],
                "lists createoradd": [
                    "lists createoradd"
                ],
                "qa currency": [
                    "qa currency"
                ],
                "audio volume mute": [
                    "audio volume mute"
                ],
                "alarm query": [
                    "alarm query"
                ],
                "general confirm": [
                    "general confirm"
                ],
                "calendar remove": [
                    "calendar remove"
                ],
                "iot hue lightchange": [
                    "iot hue lightchange"
                ],
                "news query": [
                    "news query"
                ]
            },
            "version_1": {
                "music likeness": [
                    "music likeness"
                ],
                "recommendation locations": [
                    "recommendation locations"
                ],
                "general explain": [
                    "general explain"
                ],
                "datetime query": [
                    "datetime query"
                ],
                "cooking recipe": [
                    "cooking recipe"
                ],
                "calendar query": [
                    "calendar query"
                ],
                "email addcontact": [
                    "email addcontact"
                ],
                "general dontcare": [
                    "general dontcare"
                ],
                "iot hue lightdim": [
                    "iot hue lightdim"
                ],
                "play audiobook": [
                    "play audiobook"
                ],
                "play game": [
                    "play game"
                ],
                "social post": [
                    "social post"
                ],
                "recommendation events": [
                    "recommendation events"
                ],
                "email querycontact": [
                    "email querycontact"
                ],
                "transport taxi": [
                    "transport taxi"
                ],
                "play podcasts": [
                    "play podcasts"
                ],
                "weather query": [
                    "weather query"
                ],
                "alarm set": [
                    "alarm set"
                ],
                "audio volume up": [
                    "audio volume up"
                ],
                "email sendemail": [
                    "email sendemail"
                ],
                "music settings": [
                    "music settings"
                ],
                "iot hue lightup": [
                    "iot hue lightup"
                ],
                "iot wemo on": [
                    "iot wemo on"
                ],
                "play music": [
                    "play music"
                ],
                "iot hue lighton": [
                    "iot hue lighton"
                ],
                "transport query": [
                    "transport query"
                ],
                "general repeat": [
                    "general repeat"
                ],
                "qa definition": [
                    "qa definition"
                ],
                "general quirky": [
                    "general quirky"
                ],
                "audio volume down": [
                    "audio volume down"
                ],
                "iot coffee": [
                    "iot coffee"
                ],
                "qa stock": [
                    "qa stock"
                ],
                "takeaway query": [
                    "takeaway query"
                ],
                "general commandstop": [
                    "general commandstop"
                ],
                "transport traffic": [
                    "transport traffic"
                ],
                "lists remove": [
                    "lists remove"
                ],
                "social query": [
                    "social query"
                ],
                "qa factoid": [
                    "qa factoid"
                ],
                "iot wemo off": [
                    "iot wemo off"
                ],
                "calendar set": [
                    "calendar set"
                ],
                "iot hue lightoff": [
                    "iot hue lightoff"
                ],
                "play radio": [
                    "play radio"
                ],
                "takeaway order": [
                    "takeaway order"
                ],
                "qa maths": [
                    "qa maths"
                ],
                "general negate": [
                    "general negate"
                ],
                "alarm remove": [
                    "alarm remove"
                ],
                "general affirm": [
                    "general affirm"
                ],
                "email query": [
                    "email query"
                ],
                "iot cleaning": [
                    "iot cleaning"
                ],
                "transport ticket": [
                    "transport ticket"
                ],
                "general joke": [
                    "general joke"
                ],
                "lists query": [
                    "lists query"
                ],
                "music query": [
                    "music query"
                ],
                "datetime convert": [
                    "datetime convert"
                ],
                "recommendation movies": [
                    "recommendation movies"
                ],
                "general praise": [
                    "general praise"
                ],
                "lists createoradd": [
                    "lists createoradd"
                ],
                "qa currency": [
                    "qa currency"
                ],
                "audio volume mute": [
                    "audio volume mute"
                ],
                "alarm query": [
                    "alarm query"
                ],
                "general confirm": [
                    "general confirm"
                ],
                "calendar remove": [
                    "calendar remove"
                ],
                "iot hue lightchange": [
                    "iot hue lightchange"
                ],
                "news query": [
                    "news query"
                ]
            },
            "version_2": {
                "music likeness": [
                    "Music Likeness"
                ],
                "recommendation locations": [
                    "Recommendation Locations"
                ],
                "general explain": [
                    "General Explain"
                ],
                "datetime query": [
                    "Datetime Query"
                ],
                "cooking recipe": [
                    "Cooking Recipe"
                ],
                "calendar query": [
                    "Calendar Query"
                ],
                "email addcontact": [
                    "Email Addcontact"
                ],
                "general dontcare": [
                    "General Dontcare"
                ],
                "iot hue lightdim": [
                    "Iot Hue Lightdim"
                ],
                "play audiobook": [
                    "Play Audiobook"
                ],
                "play game": [
                    "Play Game"
                ],
                "social post": [
                    "Social Post"
                ],
                "recommendation events": [
                    "Recommendation Events"
                ],
                "email querycontact": [
                    "Email Querycontact"
                ],
                "transport taxi": [
                    "Transport Taxi"
                ],
                "play podcasts": [
                    "Play Podcasts"
                ],
                "weather query": [
                    "Weather Query"
                ],
                "alarm set": [
                    "Alarm Set"
                ],
                "audio volume up": [
                    "Audio Volume Up"
                ],
                "email sendemail": [
                    "Email Sendemail"
                ],
                "music settings": [
                    "Music Settings"
                ],
                "iot hue lightup": [
                    "Iot Hue Lightup"
                ],
                "iot wemo on": [
                    "Iot Wemo On"
                ],
                "play music": [
                    "Play Music"
                ],
                "iot hue lighton": [
                    "Iot Hue Lighton"
                ],
                "transport query": [
                    "Transport Query"
                ],
                "general repeat": [
                    "General Repeat"
                ],
                "qa definition": [
                    "Qa Definition"
                ],
                "general quirky": [
                    "General Quirky"
                ],
                "audio volume down": [
                    "Audio Volume Down"
                ],
                "iot coffee": [
                    "Iot Coffee"
                ],
                "qa stock": [
                    "Qa Stock"
                ],
                "takeaway query": [
                    "Takeaway Query"
                ],
                "general commandstop": [
                    "General Commandstop"
                ],
                "transport traffic": [
                    "Transport Traffic"
                ],
                "lists remove": [
                    "Lists Remove"
                ],
                "social query": [
                    "Social Query"
                ],
                "qa factoid": [
                    "Qa Factoid"
                ],
                "iot wemo off": [
                    "Iot Wemo Off"
                ],
                "calendar set": [
                    "Calendar Set"
                ],
                "iot hue lightoff": [
                    "Iot Hue Lightoff"
                ],
                "play radio": [
                    "Play Radio"
                ],
                "takeaway order": [
                    "Takeaway Order"
                ],
                "qa maths": [
                    "Qa Maths"
                ],
                "general negate": [
                    "General Negate"
                ],
                "alarm remove": [
                    "Alarm Remove"
                ],
                "general affirm": [
                    "General Affirm"
                ],
                "email query": [
                    "Email Query"
                ],
                "iot cleaning": [
                    "Iot Cleaning"
                ],
                "transport ticket": [
                    "Transport Ticket"
                ],
                "general joke": [
                    "General Joke"
                ],
                "lists query": [
                    "Lists Query"
                ],
                "music query": [
                    "Music Query"
                ],
                "datetime convert": [
                    "Datetime Convert"
                ],
                "recommendation movies": [
                    "Recommendation Movies"
                ],
                "general praise": [
                    "General Praise"
                ],
                "lists createoradd": [
                    "Lists Createoradd"
                ],
                "qa currency": [
                    "Qa Currency"
                ],
                "audio volume mute": [
                    "Audio Volume Mute"
                ],
                "alarm query": [
                    "Alarm Query"
                ],
                "general confirm": [
                    "General Confirm"
                ],
                "calendar remove": [
                    "Calendar Remove"
                ],
                "iot hue lightchange": [
                    "Iot Hue Lightchange"
                ],
                "news query": [
                    "News Query"
                ]
            },
            "version_3": {
                "music likeness": [
                    "MusicLikeness"
                ],
                "recommendation locations": [
                    "RecommendationLocations"
                ],
                "general explain": [
                    "GeneralExplain"
                ],
                "datetime query": [
                    "DatetimeQuery"
                ],
                "cooking recipe": [
                    "CookingRecipe"
                ],
                "calendar query": [
                    "CalendarQuery"
                ],
                "email addcontact": [
                    "EmailAddcontact"
                ],
                "general dontcare": [
                    "GeneralDontcare"
                ],
                "iot hue lightdim": [
                    "IotHueLightdim"
                ],
                "play audiobook": [
                    "PlayAudiobook"
                ],
                "play game": [
                    "PlayGame"
                ],
                "social post": [
                    "SocialPost"
                ],
                "recommendation events": [
                    "RecommendationEvents"
                ],
                "email querycontact": [
                    "EmailQuerycontact"
                ],
                "transport taxi": [
                    "TransportTaxi"
                ],
                "play podcasts": [
                    "PlayPodcasts"
                ],
                "weather query": [
                    "WeatherQuery"
                ],
                "alarm set": [
                    "AlarmSet"
                ],
                "audio volume up": [
                    "AudioVolumeUp"
                ],
                "email sendemail": [
                    "EmailSendemail"
                ],
                "music settings": [
                    "MusicSettings"
                ],
                "iot hue lightup": [
                    "IotHueLightup"
                ],
                "iot wemo on": [
                    "IotWemoOn"
                ],
                "play music": [
                    "PlayMusic"
                ],
                "iot hue lighton": [
                    "IotHueLighton"
                ],
                "transport query": [
                    "TransportQuery"
                ],
                "general repeat": [
                    "GeneralRepeat"
                ],
                "qa definition": [
                    "QaDefinition"
                ],
                "general quirky": [
                    "GeneralQuirky"
                ],
                "audio volume down": [
                    "AudioVolumeDown"
                ],
                "iot coffee": [
                    "IotCoffee"
                ],
                "qa stock": [
                    "QaStock"
                ],
                "takeaway query": [
                    "TakeawayQuery"
                ],
                "general commandstop": [
                    "GeneralCommandstop"
                ],
                "transport traffic": [
                    "TransportTraffic"
                ],
                "lists remove": [
                    "ListsRemove"
                ],
                "social query": [
                    "SocialQuery"
                ],
                "qa factoid": [
                    "QaFactoid"
                ],
                "iot wemo off": [
                    "IotWemoOff"
                ],
                "calendar set": [
                    "CalendarSet"
                ],
                "iot hue lightoff": [
                    "IotHueLightoff"
                ],
                "play radio": [
                    "PlayRadio"
                ],
                "takeaway order": [
                    "TakeawayOrder"
                ],
                "qa maths": [
                    "QaMaths"
                ],
                "general negate": [
                    "GeneralNegate"
                ],
                "alarm remove": [
                    "AlarmRemove"
                ],
                "general affirm": [
                    "GeneralAffirm"
                ],
                "email query": [
                    "EmailQuery"
                ],
                "iot cleaning": [
                    "IotCleaning"
                ],
                "transport ticket": [
                    "TransportTicket"
                ],
                "general joke": [
                    "GeneralJoke"
                ],
                "lists query": [
                    "ListsQuery"
                ],
                "music query": [
                    "MusicQuery"
                ],
                "datetime convert": [
                    "DatetimeConvert"
                ],
                "recommendation movies": [
                    "RecommendationMovies"
                ],
                "general praise": [
                    "GeneralPraise"
                ],
                "lists createoradd": [
                    "ListsCreateoradd"
                ],
                "qa currency": [
                    "QaCurrency"
                ],
                "audio volume mute": [
                    "AudioVolumeMute"
                ],
                "alarm query": [
                    "AlarmQuery"
                ],
                "general confirm": [
                    "GeneralConfirm"
                ],
                "calendar remove": [
                    "CalendarRemove"
                ],
                "iot hue lightchange": [
                    "IotHueLightchange"
                ],
                "news query": [
                    "NewsQuery"
                ]
            }
        },
        "ide_intent": {
            "version_0": {
                "delete_class_in_curr_file": [
                    "delete_class_in_curr_file"
                ],
                "close_file": [
                    "close_file"
                ],
                "rename_fun_in_curr_file": [
                    "rename_fun_in_curr_file"
                ],
                "copy_fun_in_another_file": [
                    "copy_fun_in_another_file"
                ],
                "rename_fun_in_another_file": [
                    "rename_fun_in_another_file"
                ],
                "rename_class_in_curr_file": [
                    "rename_class_in_curr_file"
                ],
                "delete_fun_in_another_file": [
                    "delete_fun_in_another_file"
                ],
                "rename_file": [
                    "rename_file"
                ],
                "copy_fun_in_curr_file": [
                    "copy_fun_in_curr_file"
                ],
                "undo": [
                    "undo"
                ],
                "open_file": [
                    "open_file"
                ],
                "delete_class_in_another_file": [
                    "delete_class_in_another_file"
                ],
                "delete_fun_in_curr_file": [
                    "delete_fun_in_curr_file"
                ],
                "import_fun": [
                    "import_fun"
                ],
                "rename_class_in_another_file": [
                    "rename_class_in_another_file"
                ],
                "move_class_in_curr_file": [
                    "move_class_in_curr_file"
                ],
                "import_class": [
                    "import_class"
                ],
                "move_class_in_another_file": [
                    "move_class_in_another_file"
                ],
                "move_fun_in_curr_file": [
                    "move_fun_in_curr_file"
                ],
                "save_file": [
                    "save_file"
                ],
                "delete_file": [
                    "delete_file"
                ],
                "move_fun_in_another_file": [
                    "move_fun_in_another_file"
                ],
                "copy_class_in_curr_file": [
                    "copy_class_in_curr_file"
                ],
                "create_file": [
                    "create_file"
                ],
                "copy_class_in_another_file": [
                    "copy_class_in_another_file"
                ],
                "redo": [
                    "redo"
                ],
                "compile": [
                    "compile"
                ]
            },
            "version_1": {
                "delete_class_in_curr_file": [
                    "delete class in current file",
                ],
                "close_file": [
                    "close file"
                ],
                "rename_fun_in_curr_file": [
                    "rename fun in current file"
                ],
                "copy_fun_in_another_file": [
                    "copy fun in another file"
                ],
                "rename_fun_in_another_file": [
                    "rename fun in another file"
                ],
                "rename_class_in_curr_file": [
                    "rename class in current file"
                ],
                "delete_fun_in_another_file": [
                    "delete fun in another file"
                ],
                "rename_file": [
                    "rename file"
                ],
                "copy_fun_in_curr_file": [
                    "copy fun in current file"
                ],
                "undo": [
                    "undo"
                ],
                "open_file": [
                    "open file"
                ],
                "delete_class_in_another_file": [
                    "delete class in another file"
                ],
                "delete_fun_in_curr_file": [
                    "delete fun in current file"
                ],
                "import_fun": [
                    "import fun"
                ],
                "rename_class_in_another_file": [
                    "rename class in another file"
                ],
                "move_class_in_curr_file": [
                    "move class in current file"
                ],
                "import_class": [
                    "import class"
                ],
                "move_class_in_another_file": [
                    "move class in another file"
                ],
                "move_fun_in_curr_file": [
                    "move fun in current file"
                ],
                "save_file": [
                    "save file"
                ],
                "delete_file": [
                    "delete file"
                ],
                "move_fun_in_another_file": [
                    "move fun in another file"
                ],
                "copy_class_in_curr_file": [
                    "copy class in current file"
                ],
                "create_file": [
                    "create file"
                ],
                "copy_class_in_another_file": [
                    "copy class in another file"
                ],
                "redo": [
                    "redo"
                ],
                "compile": [
                    "compile"
                ]
            },
            "version_2": {
                "delete_class_in_curr_file": [
                    "Delete Class In Current File"
                ],
                "close_file": [
                    "Close File"
                ],
                "rename_fun_in_curr_file": [
                    "Rename Fun In Current File"
                ],
                "copy_fun_in_another_file": [
                    "Copy Fun In Another File"
                ],
                "rename_fun_in_another_file": [
                    "Rename Fun In Another File"
                ],
                "rename_class_in_curr_file": [
                    "Rename Class In Current File"
                ],
                "delete_fun_in_another_file": [
                    "Delete Fun In Another File"
                ],
                "rename_file": [
                    "Rename File"
                ],
                "copy_fun_in_curr_file": [
                    "Copy Fun In Current File"
                ],
                "undo": [
                    "Undo"
                ],
                "open_file": [
                    "Open File"
                ],
                "delete_class_in_another_file": [
                    "Delete Class In Another File"
                ],
                "delete_fun_in_curr_file": [
                    "Delete Fun In Current File"
                ],
                "import_fun": [
                    "Import Fun"
                ],
                "rename_class_in_another_file": [
                    "Rename Class In Another File"
                ],
                "move_class_in_curr_file": [
                    "Move Class In Current File"
                ],
                "import_class": [
                    "Import Class"
                ],
                "move_class_in_another_file": [
                    "Move Class In Another File"
                ],
                "move_fun_in_curr_file": [
                    "Move Fun In Current File"
                ],
                "save_file": [
                    "Save File"
                ],
                "delete_file": [
                    "Delete File"
                ],
                "move_fun_in_another_file": [
                    "Move Fun In Another File"
                ],
                "copy_class_in_curr_file": [
                    "Copy Class In Current File"
                ],
                "create_file": [
                    "Create File"
                ],
                "copy_class_in_another_file": [
                    "Copy Class In Another File"
                ],
                "redo": [
                    "Redo"
                ],
                "compile": [
                    "Compile"
                ]
            },
            "version_3": {
                "delete_class_in_curr_file": [
                    "DeleteClassInCurrentFile"
                ],
                "close_file": [
                    "CloseFile"
                ],
                "rename_fun_in_curr_file": [
                    "RenameFunInCurrentFile"
                ],
                "copy_fun_in_another_file": [
                    "CopyFunInAnotherFile"
                ],
                "rename_fun_in_another_file": [
                    "RenameFunInAnotherFile"
                ],
                "rename_class_in_curr_file": [
                    "RenameClassInCurrentFile"
                ],
                "delete_fun_in_another_file": [
                    "DeleteFunInAnotherFile"
                ],
                "rename_file": [
                    "RenameFile"
                ],
                "copy_fun_in_curr_file": [
                    "CopyFunInCurrentFile"
                ],
                "undo": [
                    "Undo"
                ],
                "open_file": [
                    "OpenFile"
                ],
                "delete_class_in_another_file": [
                    "DeleteClassInAnotherFile"
                ],
                "delete_fun_in_curr_file": [
                    "DeleteFunInCurrentFile"
                ],
                "import_fun": [
                    "ImportFun"
                ],
                "rename_class_in_another_file": [
                    "RenameClassInAnotherFile"
                ],
                "move_class_in_curr_file": [
                    "MoveClassInCurrentFile"
                ],
                "import_class": [
                    "ImportClass"
                ],
                "move_class_in_another_file": [
                    "MoveClassInAnotherFile"
                ],
                "move_fun_in_curr_file": [
                    "MoveFunInCurrentFile"
                ],
                "save_file": [
                    "SaveFile"
                ],
                "delete_file": [
                    "DeleteFile"
                ],
                "move_fun_in_another_file": [
                    "MoveFunInAnotherFile"
                ],
                "copy_class_in_curr_file": [
                    "CopyClassInCurrentFile"
                ],
                "create_file": [
                    "CreateFile"
                ],
                "copy_class_in_another_file": [
                    "CopyClassInAnotherFile"
                ],
                "redo": [
                    "Redo"
                ],
                "compile": [
                    "Compile"
                ]
            },
            "version_4": {
                "delete_class_in_curr_file": [
                    "DELETE_CLASS_IN_CURRENT_FILE"
                ],
                "close_file": [
                    "CLOSE_FILE"
                ],
                "rename_fun_in_curr_file": [
                    "RENAME_FUN_IN_CURRENT_FILE"
                ],
                "copy_fun_in_another_file": [
                    "COPY_FUN_IN_ANOTHER_FILE"
                ],
                "rename_fun_in_another_file": [
                    "RENAME_FUN_IN_ANOTHER_FILE"
                ],
                "rename_class_in_curr_file": [
                    "RENAME_CLASS_IN_CURRENT_FILE"
                ],
                "delete_fun_in_another_file": [
                    "DELETE_FUN_IN_ANOTHER_FILE"
                ],
                "rename_file": [
                    "RENAME_FILE"
                ],
                "copy_fun_in_curr_file": [
                    "COPY_FUN_IN_CURRENT_FILE"
                ],
                "undo": [
                    "UNDO"
                ],
                "open_file": [
                    "OPEN_FILE"
                ],
                "delete_class_in_another_file": [
                    "DELETE_CLASS_IN_ANOTHER_FILE"
                ],
                "delete_fun_in_curr_file": [
                    "DELETE_FUN_IN_CURRENT_FILE"
                ],
                "import_fun": [
                    "IMPORT_FUN"
                ],
                "rename_class_in_another_file": [
                    "RENAME_CLASS_IN_ANOTHER_FILE"
                ],
                "move_class_in_curr_file": [
                    "MOVE_CLASS_IN_CURRENT_FILE"
                ],
                "import_class": [
                    "IMPORT_CLASS"
                ],
                "move_class_in_another_file": [
                    "MOVE_CLASS_IN_ANOTHER_FILE"
                ],
                "move_fun_in_curr_file": [
                    "MOVE_FUN_IN_CURRENT_FILE"
                ],
                "save_file": [
                    "SAVE_FILE"
                ],
                "delete_file": [
                    "DELETE_FILE"
                ],
                "move_fun_in_another_file": [
                    "MOVE_FUN_IN_ANOTHER_FILE"
                ],
                "copy_class_in_curr_file": [
                    "COPY_CLASS_IN_CURRENT_FILE"
                ],
                "create_file": [
                    "CREATE_FILE"
                ],
                "copy_class_in_another_file": [
                    "COPY_CLASS_IN_ANOTHER_FILE"
                ],
                "redo": [
                    "REDO"
                ],
                "compile": [
                    "COMPILE"
                ]
            }
        },
        "intent_classification": {
            "version_0": {
                "AddToPlaylist": [
                    "AddToPlaylist"
                ],
                "BookRestaurant": [
                    "BookRestaurant"
                ],
                "PlayMusic": [
                    "PlayMusic"
                ],
                "GetWeather": [
                    "GetWeather"
                ],
                "Affirmation": [
                    "Affirmation"
                ],
                "SearchCreativeWork": [
                    "SearchCreativeWork"
                ],
                "Cancellation": [
                    "Cancellation"
                ],
                "excitment": [
                    "excitment"
                ],
                "RateBook": [
                    "RateBook"
                ],
                "SearchScreeningEvent": [
                    "SearchScreeningEvent"
                ],
                "Greetings": [
                    "Greetings"
                ],
                "Book Meeting": [
                    "Book Meeting"
                ]
            }
        },
        "jarvis_intent": {
            "version_0": {
                "translate": [
                    "translate"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning_of_life"
                ],
                "fun_fact": [
                    "fun_fact"
                ],
                "time": [
                    "time"
                ],
                "flip_coin": [
                    "flip_coin"
                ],
                "where_are_you_from": [
                    "where_are_you_from"
                ],
                "maybe": [
                    "maybe"
                ],
                "who_made_you": [
                    "who_made_you"
                ],
                "next_song": [
                    "next_song"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel_suggestion"
                ],
                "todo_list_update": [
                    "todo_list_update"
                ],
                "reminder": [
                    "reminder"
                ],
                "no": [
                    "no"
                ],
                "calendar": [
                    "calendar"
                ],
                "calculator": [
                    "calculator"
                ],
                "thank_you": [
                    "thank_you"
                ],
                "roll_dice": [
                    "roll_dice"
                ],
                "reminder_update": [
                    "reminder_update"
                ],
                "todo_list": [
                    "todo_list"
                ],
                "change_volume": [
                    "change_volume"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "what_song": [
                    "what_song"
                ],
                "measurement_conversion": [
                    "measurement_conversion"
                ],
                "current_location": [
                    "current_location"
                ],
                "weather": [
                    "weather"
                ],
                "whisper_mode": [
                    "whisper_mode"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset_settings"
                ],
                "what_is_your_name": [
                    "what_is_your_name"
                ],
                "play_music": [
                    "play_music"
                ],
                "calendar_update": [
                    "calendar_update"
                ],
                "are_you_a_bot": [
                    "are_you_a_bot"
                ],
                "tell_joke": [
                    "tell_joke"
                ],
                "how_old_are_you": [
                    "how_old_are_you"
                ]
            },
            "version_1": {
                "translate": [
                    "translate"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning of life"
                ],
                "fun_fact": [
                    "fun fact"
                ],
                "time": [
                    "time"
                ],
                "flip_coin": [
                    "flip coin"
                ],
                "where_are_you_from": [
                    "where are you from"
                ],
                "maybe": [
                    "maybe"
                ],
                "who_made_you": [
                    "who made you"
                ],
                "next_song": [
                    "next song"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel suggestion"
                ],
                "todo_list_update": [
                    "todo list update"
                ],
                "reminder": [
                    "reminder"
                ],
                "no": [
                    "no"
                ],
                "calendar": [
                    "calendar"
                ],
                "calculator": [
                    "calculator"
                ],
                "thank_you": [
                    "thank you"
                ],
                "roll_dice": [
                    "roll dice"
                ],
                "reminder_update": [
                    "reminder update"
                ],
                "todo_list": [
                    "todo list"
                ],
                "change_volume": [
                    "change volume"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "what_song": [
                    "what song"
                ],
                "measurement_conversion": [
                    "measurement conversion"
                ],
                "current_location": [
                    "current location"
                ],
                "weather": [
                    "weather"
                ],
                "whisper_mode": [
                    "whisper mode"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset settings"
                ],
                "what_is_your_name": [
                    "what is your name"
                ],
                "play_music": [
                    "play music"
                ],
                "calendar_update": [
                    "calendar update"
                ],
                "are_you_a_bot": [
                    "are you a bot"
                ],
                "tell_joke": [
                    "tell joke"
                ],
                "how_old_are_you": [
                    "how old are you"
                ]
            },
            "version_2": {
                "translate": [
                    "Translate"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "Meaning Of Life"
                ],
                "fun_fact": [
                    "Fun Fact"
                ],
                "time": [
                    "Time"
                ],
                "flip_coin": [
                    "Flip Coin"
                ],
                "where_are_you_from": [
                    "Where Are You From"
                ],
                "maybe": [
                    "Maybe"
                ],
                "who_made_you": [
                    "Who Made You"
                ],
                "next_song": [
                    "Next Song"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "Travel Suggestion"
                ],
                "todo_list_update": [
                    "Todo List Update"
                ],
                "reminder": [
                    "Reminder"
                ],
                "no": [
                    "No"
                ],
                "calendar": [
                    "Calendar"
                ],
                "calculator": [
                    "Calculator"
                ],
                "thank_you": [
                    "Thank You"
                ],
                "roll_dice": [
                    "Roll Dice"
                ],
                "reminder_update": [
                    "Reminder Update"
                ],
                "todo_list": [
                    "Todo List"
                ],
                "change_volume": [
                    "Change Volume"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "what_song": [
                    "What Song"
                ],
                "measurement_conversion": [
                    "Measurement Conversion"
                ],
                "current_location": [
                    "Current Location"
                ],
                "weather": [
                    "Weather"
                ],
                "whisper_mode": [
                    "Whisper Mode"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "Reset Settings"
                ],
                "what_is_your_name": [
                    "What Is Your Name"
                ],
                "play_music": [
                    "Play Music"
                ],
                "calendar_update": [
                    "Calendar Update"
                ],
                "are_you_a_bot": [
                    "Are You A Bot"
                ],
                "tell_joke": [
                    "Tell Joke"
                ],
                "how_old_are_you": [
                    "How Old Are You"
                ]
            },
            "version_3": {
                "translate": [
                    "Translate"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "MeaningOfLife"
                ],
                "fun_fact": [
                    "FunFact"
                ],
                "time": [
                    "Time"
                ],
                "flip_coin": [
                    "FlipCoin"
                ],
                "where_are_you_from": [
                    "WhereAreYouFrom"
                ],
                "maybe": [
                    "Maybe"
                ],
                "who_made_you": [
                    "WhoMadeYou"
                ],
                "next_song": [
                    "NextSong"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "TravelSuggestion"
                ],
                "todo_list_update": [
                    "TodoListUpdate"
                ],
                "reminder": [
                    "Reminder"
                ],
                "no": [
                    "No"
                ],
                "calendar": [
                    "Calendar"
                ],
                "calculator": [
                    "Calculator"
                ],
                "thank_you": [
                    "ThankYou"
                ],
                "roll_dice": [
                    "RollDice"
                ],
                "reminder_update": [
                    "ReminderUpdate"
                ],
                "todo_list": [
                    "TodoList"
                ],
                "change_volume": [
                    "ChangeVolume"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "what_song": [
                    "WhatSong"
                ],
                "measurement_conversion": [
                    "MeasurementConversion"
                ],
                "current_location": [
                    "CurrentLocation"
                ],
                "weather": [
                    "Weather"
                ],
                "whisper_mode": [
                    "WhisperMode"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "ResetSettings"
                ],
                "what_is_your_name": [
                    "WhatIsYourName"
                ],
                "play_music": [
                    "PlayMusic"
                ],
                "calendar_update": [
                    "CalendarUpdate"
                ],
                "are_you_a_bot": [
                    "AreYouABot"
                ],
                "tell_joke": [
                    "TellJoke"
                ],
                "how_old_are_you": [
                    "HowOldAreYou"
                ]
            },
            "version_4": {
                "translate": [
                    "TRANSLATE"
                ],
                "timer": [
                    "TIMER"
                ],
                "definition": [
                    "DEFINITION"
                ],
                "meaning_of_life": [
                    "MEANING_OF_LIFE"
                ],
                "fun_fact": [
                    "FUN_FACT"
                ],
                "time": [
                    "TIME"
                ],
                "flip_coin": [
                    "FLIP_COIN"
                ],
                "where_are_you_from": [
                    "WHERE_ARE_YOU_FROM"
                ],
                "maybe": [
                    "MAYBE"
                ],
                "who_made_you": [
                    "WHO_MADE_YOU"
                ],
                "next_song": [
                    "NEXT_SONG"
                ],
                "yes": [
                    "YES"
                ],
                "travel_suggestion": [
                    "TRAVEL_SUGGESTION"
                ],
                "todo_list_update": [
                    "TODO_LIST_UPDATE"
                ],
                "reminder": [
                    "REMINDER"
                ],
                "no": [
                    "NO"
                ],
                "calendar": [
                    "CALENDAR"
                ],
                "calculator": [
                    "CALCULATOR"
                ],
                "thank_you": [
                    "THANK_YOU"
                ],
                "roll_dice": [
                    "ROLL_DICE"
                ],
                "reminder_update": [
                    "REMINDER_UPDATE"
                ],
                "todo_list": [
                    "TODO_LIST"
                ],
                "change_volume": [
                    "CHANGE_VOLUME"
                ],
                "goodbye": [
                    "GOODBYE"
                ],
                "what_song": [
                    "WHAT_SONG"
                ],
                "measurement_conversion": [
                    "MEASUREMENT_CONVERSION"
                ],
                "current_location": [
                    "CURRENT_LOCATION"
                ],
                "weather": [
                    "WEATHER"
                ],
                "whisper_mode": [
                    "WHISPER_MODE"
                ],
                "spelling": [
                    "SPELLING"
                ],
                "greeting": [
                    "GREETING"
                ],
                "reset_settings": [
                    "RESET_SETTINGS"
                ],
                "what_is_your_name": [
                    "WHAT_IS_YOUR_NAME"
                ],
                "play_music": [
                    "PLAY_MUSIC"
                ],
                "calendar_update": [
                    "CALENDAR_UPDATE"
                ],
                "are_you_a_bot": [
                    "ARE_YOU_A_BOT"
                ],
                "tell_joke": [
                    "TELL_JOKE"
                ],
                "how_old_are_you": [
                    "HOW_OLD_ARE_YOU"
                ]
            }
        },
        "mobile_assistant": {"version_0": {
            "others": [
                "others"
            ],
            "places near me": [
                "places near me"
            ],
            "send whatsapp message": [
                "send whatsapp message"
            ],
            "greet and hello hi kind of things, general check in": [
                "greet and hello hi kind of things, general check in"
            ],
            "play games": [
                "play games"
            ],
            "tell me news": [
                "tell me news"
            ],
            "covid cases": [
                "covid cases"
            ],
            "tell me about": [
                "tell me about"
            ],
            "volume control": [
                "volume control"
            ],
            "open website": [
                "open website"
            ],
            "play on youtube": [
                "play on youtube"
            ],
            "tell me joke": [
                "tell me joke"
            ],
            "send email": [
                "send email"
            ],
            "goodbye": [
                "goodbye"
            ],
            "take screenshot": [
                "take screenshot"
            ],
            "download youtube video": [
                "download youtube video"
            ],
            "asking weather": [
                "asking weather"
            ],
            "asking date": [
                "asking date"
            ],
            "asking time": [
                "asking time"
            ],
            "i am bored": [
                "i am bored"
            ],
            "click photo": [
                "click photo"
            ],
            "what can you do": [
                "what can you do"
            ]
        }},
        "mtop_intent": {
            "version_0": {
                "GET_MESSAGE": [
                    "get_message"
                ],
                "GET_WEATHER": [
                    "get_weather"
                ],
                "GET_ALARM": [
                    "get_alarm"
                ],
                "SEND_MESSAGE": [
                    "send_message"
                ],
                "GET_INFO_RECIPES": [
                    "get_info_recipes"
                ],
                "SET_UNAVAILABLE": [
                    "set_unavailable"
                ],
                "DELETE_REMINDER": [
                    "delete_reminder"
                ],
                "GET_STORIES_NEWS": [
                    "get_stories_news"
                ],
                "CREATE_ALARM": [
                    "create_alarm"
                ],
                "GET_REMINDER": [
                    "get_reminder"
                ],
                "CREATE_REMINDER": [
                    "create_reminder"
                ],
                "GET_RECIPES": [
                    "get_recipes"
                ],
                "QUESTION_NEWS": [
                    "question_news"
                ],
                "GET_EVENT": [
                    "get_event"
                ],
                "PLAY_MUSIC": [
                    "play_music"
                ],
                "GET_CALL_TIME": [
                    "get_call_time"
                ],
                "CREATE_CALL": [
                    "create_call"
                ],
                "END_CALL": [
                    "end_call"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "create_playlist_music"
                ],
                "CREATE_TIMER": [
                    "create_timer"
                ],
                "IGNORE_CALL": [
                    "ignore_call"
                ],
                "GET_LIFE_EVENT": [
                    "get_life_event"
                ],
                "GET_INFO_CONTACT": [
                    "get_info_contact"
                ],
                "UPDATE_CALL": [
                    "update_call"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "update_reminder_date_time"
                ],
                "GET_CONTACT": [
                    "get_contact"
                ],
                "GET_TIMER": [
                    "get_timer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "get_reminder_date_time"
                ],
                "DELETE_ALARM": [
                    "delete_alarm"
                ],
                "PAUSE_MUSIC": [
                    "pause_music"
                ],
                "GET_AGE": [
                    "get_age"
                ],
                "GET_SUNRISE": [
                    "get_sunrise"
                ],
                "GET_EMPLOYER": [
                    "get_employer"
                ],
                "GET_EDUCATION_TIME": [
                    "get_education_time"
                ],
                "ANSWER_CALL": [
                    "answer_call"
                ],
                "SET_RSVP_YES": [
                    "set_rsvp_yes"
                ],
                "SNOOZE_ALARM": [
                    "snooze_alarm"
                ],
                "GET_JOB": [
                    "get_job"
                ],
                "UPDATE_REMINDER_TODO": [
                    "update_reminder_todo"
                ],
                "IS_TRUE_RECIPES": [
                    "is_true_recipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "remove_from_playlist_music"
                ],
                "GET_AVAILABILITY": [
                    "get_availability"
                ],
                "GET_CATEGORY_EVENT": [
                    "get_category_event"
                ],
                "PLAY_MEDIA": [
                    "play_media"
                ],
                "ADD_TIME_TIMER": [
                    "add_time_timer"
                ],
                "GET_CALL": [
                    "get_call"
                ],
                "SET_AVAILABLE": [
                    "set_available"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "add_to_playlist_music"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "get_employment_time"
                ],
                "SHARE_EVENT": [
                    "share_event"
                ],
                "PREFER": [
                    "prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "start_shuffle_music"
                ],
                "GET_CALL_CONTACT": [
                    "get_call_contact"
                ],
                "GET_LOCATION": [
                    "get_location"
                ],
                "SILENCE_ALARM": [
                    "silence_alarm"
                ],
                "SWITCH_CALL": [
                    "switch_call"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "get_track_info_music"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "subtract_time_timer"
                ],
                "GET_SUNSET": [
                    "get_sunset"
                ],
                "DELETE_TIMER": [
                    "delete_timer"
                ],
                "UPDATE_TIMER": [
                    "update_timer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "previous_track_music"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "set_default_provider_music"
                ],
                "HOLD_CALL": [
                    "hold_call"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "get_mutual_friends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "skip_track_music"
                ],
                "UPDATE_METHOD_CALL": [
                    "update_method_call"
                ],
                "SET_RSVP_INTERESTED": [
                    "set_rsvp_interested"
                ],
                "QUESTION_MUSIC": [
                    "question_music"
                ],
                "GET_UNDERGRAD": [
                    "get_undergrad"
                ],
                "PAUSE_TIMER": [
                    "pause_timer"
                ],
                "UPDATE_ALARM": [
                    "update_alarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "get_reminder_location"
                ],
                "GET_ATTENDEE_EVENT": [
                    "get_attendee_event"
                ],
                "LIKE_MUSIC": [
                    "like_music"
                ],
                "RESTART_TIMER": [
                    "restart_timer"
                ],
                "RESUME_TIMER": [
                    "resume_timer"
                ],
                "MERGE_CALL": [
                    "merge_call"
                ],
                "GET_MESSAGE_CONTACT": [
                    "get_message_contact"
                ],
                "REPLAY_MUSIC": [
                    "replay_music"
                ],
                "LOOP_MUSIC": [
                    "loop_music"
                ],
                "GET_REMINDER_AMOUNT": [
                    "get_reminder_amount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "get_date_time_event"
                ],
                "STOP_MUSIC": [
                    "stop_music"
                ],
                "GET_DETAILS_NEWS": [
                    "get_details_news"
                ],
                "GET_EDUCATION_DEGREE": [
                    "get_education_degree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "set_default_provider_calling"
                ],
                "GET_MAJOR": [
                    "get_major"
                ],
                "UNLOOP_MUSIC": [
                    "unloop_music"
                ],
                "GET_CONTACT_METHOD": [
                    "get_contact_method"
                ],
                "SET_RSVP_NO": [
                    "set_rsvp_no"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "update_reminder_location"
                ],
                "RESUME_CALL": [
                    "resume_call"
                ],
                "CANCEL_MESSAGE": [
                    "cancel_message"
                ],
                "RESUME_MUSIC": [
                    "resume_music"
                ],
                "UPDATE_REMINDER": [
                    "update_reminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "delete_playlist_music"
                ],
                "REWIND_MUSIC": [
                    "rewind_music"
                ],
                "REPEAT_ALL_MUSIC": [
                    "repeat_all_music"
                ],
                "FAST_FORWARD_MUSIC": [
                    "fast_forward_music"
                ],
                "DISLIKE_MUSIC": [
                    "dislike_music"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "get_life_event_time"
                ],
                "DISPREFER": [
                    "disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "repeat_all_off_music"
                ],
                "HELP_REMINDER": [
                    "help_reminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "get_lyrics_music"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "stop_shuffle_music"
                ],
                "GET_AIRQUALITY": [
                    "get_airquality"
                ],
                "GET_LANGUAGE": [
                    "get_language"
                ],
                "FOLLOW_MUSIC": [
                    "follow_music"
                ],
                "GET_GENDER": [
                    "get_gender"
                ],
                "CANCEL_CALL": [
                    "cancel_call"
                ],
                "GET_GROUP": [
                    "get_group"
                ]
            },
            "version_1": {
                "GET_MESSAGE": [
                    "get message"
                ],
                "GET_WEATHER": [
                    "get weather"
                ],
                "GET_ALARM": [
                    "get alarm"
                ],
                "SEND_MESSAGE": [
                    "send message"
                ],
                "GET_INFO_RECIPES": [
                    "get info recipes"
                ],
                "SET_UNAVAILABLE": [
                    "set unavailable"
                ],
                "DELETE_REMINDER": [
                    "delete reminder"
                ],
                "GET_STORIES_NEWS": [
                    "get stories news"
                ],
                "CREATE_ALARM": [
                    "create alarm"
                ],
                "GET_REMINDER": [
                    "get reminder"
                ],
                "CREATE_REMINDER": [
                    "create reminder"
                ],
                "GET_RECIPES": [
                    "get recipes"
                ],
                "QUESTION_NEWS": [
                    "question news"
                ],
                "GET_EVENT": [
                    "get event"
                ],
                "PLAY_MUSIC": [
                    "play music"
                ],
                "GET_CALL_TIME": [
                    "get call time"
                ],
                "CREATE_CALL": [
                    "create call"
                ],
                "END_CALL": [
                    "end call"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "create playlist music"
                ],
                "CREATE_TIMER": [
                    "create timer"
                ],
                "IGNORE_CALL": [
                    "ignore call"
                ],
                "GET_LIFE_EVENT": [
                    "get life event"
                ],
                "GET_INFO_CONTACT": [
                    "get info contact"
                ],
                "UPDATE_CALL": [
                    "update call"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "update reminder date time"
                ],
                "GET_CONTACT": [
                    "get contact"
                ],
                "GET_TIMER": [
                    "get timer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "get reminder date time"
                ],
                "DELETE_ALARM": [
                    "delete alarm"
                ],
                "PAUSE_MUSIC": [
                    "pause music"
                ],
                "GET_AGE": [
                    "get age"
                ],
                "GET_SUNRISE": [
                    "get sunrise"
                ],
                "GET_EMPLOYER": [
                    "get employer"
                ],
                "GET_EDUCATION_TIME": [
                    "get education time"
                ],
                "ANSWER_CALL": [
                    "answer call"
                ],
                "SET_RSVP_YES": [
                    "set rsvp yes"
                ],
                "SNOOZE_ALARM": [
                    "snooze alarm"
                ],
                "GET_JOB": [
                    "get job"
                ],
                "UPDATE_REMINDER_TODO": [
                    "update reminder todo"
                ],
                "IS_TRUE_RECIPES": [
                    "is true recipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "remove from playlist music"
                ],
                "GET_AVAILABILITY": [
                    "get availability"
                ],
                "GET_CATEGORY_EVENT": [
                    "get category event"
                ],
                "PLAY_MEDIA": [
                    "play media"
                ],
                "ADD_TIME_TIMER": [
                    "add time timer"
                ],
                "GET_CALL": [
                    "get call"
                ],
                "SET_AVAILABLE": [
                    "set available"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "add to playlist music"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "get employment time"
                ],
                "SHARE_EVENT": [
                    "share event"
                ],
                "PREFER": [
                    "prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "start shuffle music"
                ],
                "GET_CALL_CONTACT": [
                    "get call contact"
                ],
                "GET_LOCATION": [
                    "get location"
                ],
                "SILENCE_ALARM": [
                    "silence alarm"
                ],
                "SWITCH_CALL": [
                    "switch call"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "get track info music"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "subtract time timer"
                ],
                "GET_SUNSET": [
                    "get sunset"
                ],
                "DELETE_TIMER": [
                    "delete timer"
                ],
                "UPDATE_TIMER": [
                    "update timer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "previous track music"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "set default provider music"
                ],
                "HOLD_CALL": [
                    "hold call"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "get mutual friends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "skip track music"
                ],
                "UPDATE_METHOD_CALL": [
                    "update method call"
                ],
                "SET_RSVP_INTERESTED": [
                    "set rsvp interested"
                ],
                "QUESTION_MUSIC": [
                    "question music"
                ],
                "GET_UNDERGRAD": [
                    "get undergrad"
                ],
                "PAUSE_TIMER": [
                    "pause timer"
                ],
                "UPDATE_ALARM": [
                    "update alarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "get reminder location"
                ],
                "GET_ATTENDEE_EVENT": [
                    "get attendee event"
                ],
                "LIKE_MUSIC": [
                    "like music"
                ],
                "RESTART_TIMER": [
                    "restart timer"
                ],
                "RESUME_TIMER": [
                    "resume timer"
                ],
                "MERGE_CALL": [
                    "merge call"
                ],
                "GET_MESSAGE_CONTACT": [
                    "get message contact"
                ],
                "REPLAY_MUSIC": [
                    "replay music"
                ],
                "LOOP_MUSIC": [
                    "loop music"
                ],
                "GET_REMINDER_AMOUNT": [
                    "get reminder amount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "get date time event"
                ],
                "STOP_MUSIC": [
                    "stop music"
                ],
                "GET_DETAILS_NEWS": [
                    "get details news"
                ],
                "GET_EDUCATION_DEGREE": [
                    "get education degree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "set default provider calling"
                ],
                "GET_MAJOR": [
                    "get major"
                ],
                "UNLOOP_MUSIC": [
                    "unloop music"
                ],
                "GET_CONTACT_METHOD": [
                    "get contact method"
                ],
                "SET_RSVP_NO": [
                    "set rsvp no"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "update reminder location"
                ],
                "RESUME_CALL": [
                    "resume call"
                ],
                "CANCEL_MESSAGE": [
                    "cancel message"
                ],
                "RESUME_MUSIC": [
                    "resume music"
                ],
                "UPDATE_REMINDER": [
                    "update reminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "delete playlist music"
                ],
                "REWIND_MUSIC": [
                    "rewind music"
                ],
                "REPEAT_ALL_MUSIC": [
                    "repeat all music"
                ],
                "FAST_FORWARD_MUSIC": [
                    "fast forward music"
                ],
                "DISLIKE_MUSIC": [
                    "dislike music"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "get life event time"
                ],
                "DISPREFER": [
                    "disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "repeat all off music"
                ],
                "HELP_REMINDER": [
                    "help reminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "get lyrics music"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "stop shuffle music"
                ],
                "GET_AIRQUALITY": [
                    "get airquality"
                ],
                "GET_LANGUAGE": [
                    "get language"
                ],
                "FOLLOW_MUSIC": [
                    "follow music"
                ],
                "GET_GENDER": [
                    "get gender"
                ],
                "CANCEL_CALL": [
                    "cancel call"
                ],
                "GET_GROUP": [
                    "get group"
                ]
            },
            "version_2": {
                "GET_MESSAGE": [
                    "Get Message"
                ],
                "GET_WEATHER": [
                    "Get Weather"
                ],
                "GET_ALARM": [
                    "Get Alarm"
                ],
                "SEND_MESSAGE": [
                    "Send Message"
                ],
                "GET_INFO_RECIPES": [
                    "Get Info Recipes"
                ],
                "SET_UNAVAILABLE": [
                    "Set Unavailable"
                ],
                "DELETE_REMINDER": [
                    "Delete Reminder"
                ],
                "GET_STORIES_NEWS": [
                    "Get Stories News"
                ],
                "CREATE_ALARM": [
                    "Create Alarm"
                ],
                "GET_REMINDER": [
                    "Get Reminder"
                ],
                "CREATE_REMINDER": [
                    "Create Reminder"
                ],
                "GET_RECIPES": [
                    "Get Recipes"
                ],
                "QUESTION_NEWS": [
                    "Question News"
                ],
                "GET_EVENT": [
                    "Get Event"
                ],
                "PLAY_MUSIC": [
                    "Play Music"
                ],
                "GET_CALL_TIME": [
                    "Get Call Time"
                ],
                "CREATE_CALL": [
                    "Create Call"
                ],
                "END_CALL": [
                    "End Call"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "Create Playlist Music"
                ],
                "CREATE_TIMER": [
                    "Create Timer"
                ],
                "IGNORE_CALL": [
                    "Ignore Call"
                ],
                "GET_LIFE_EVENT": [
                    "Get Life Event"
                ],
                "GET_INFO_CONTACT": [
                    "Get Info Contact"
                ],
                "UPDATE_CALL": [
                    "Update Call"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "Update Reminder Date Time"
                ],
                "GET_CONTACT": [
                    "Get Contact"
                ],
                "GET_TIMER": [
                    "Get Timer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "Get Reminder Date Time"
                ],
                "DELETE_ALARM": [
                    "Delete Alarm"
                ],
                "PAUSE_MUSIC": [
                    "Pause Music"
                ],
                "GET_AGE": [
                    "Get Age"
                ],
                "GET_SUNRISE": [
                    "Get Sunrise"
                ],
                "GET_EMPLOYER": [
                    "Get Employer"
                ],
                "GET_EDUCATION_TIME": [
                    "Get Education Time"
                ],
                "ANSWER_CALL": [
                    "Answer Call"
                ],
                "SET_RSVP_YES": [
                    "Set Rsvp Yes"
                ],
                "SNOOZE_ALARM": [
                    "Snooze Alarm"
                ],
                "GET_JOB": [
                    "Get Job"
                ],
                "UPDATE_REMINDER_TODO": [
                    "Update Reminder Todo"
                ],
                "IS_TRUE_RECIPES": [
                    "Is True Recipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "Remove From Playlist Music"
                ],
                "GET_AVAILABILITY": [
                    "Get Availability"
                ],
                "GET_CATEGORY_EVENT": [
                    "Get Category Event"
                ],
                "PLAY_MEDIA": [
                    "Play Media"
                ],
                "ADD_TIME_TIMER": [
                    "Add Time Timer"
                ],
                "GET_CALL": [
                    "Get Call"
                ],
                "SET_AVAILABLE": [
                    "Set Available"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "Add To Playlist Music"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "Get Employment Time"
                ],
                "SHARE_EVENT": [
                    "Share Event"
                ],
                "PREFER": [
                    "Prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "Start Shuffle Music"
                ],
                "GET_CALL_CONTACT": [
                    "Get Call Contact"
                ],
                "GET_LOCATION": [
                    "Get Location"
                ],
                "SILENCE_ALARM": [
                    "Silence Alarm"
                ],
                "SWITCH_CALL": [
                    "Switch Call"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "Get Track Info Music"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "Subtract Time Timer"
                ],
                "GET_SUNSET": [
                    "Get Sunset"
                ],
                "DELETE_TIMER": [
                    "Delete Timer"
                ],
                "UPDATE_TIMER": [
                    "Update Timer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "Previous Track Music"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "Set Default Provider Music"
                ],
                "HOLD_CALL": [
                    "Hold Call"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "Get Mutual Friends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "Skip Track Music"
                ],
                "UPDATE_METHOD_CALL": [
                    "Update Method Call"
                ],
                "SET_RSVP_INTERESTED": [
                    "Set Rsvp Interested"
                ],
                "QUESTION_MUSIC": [
                    "Question Music"
                ],
                "GET_UNDERGRAD": [
                    "Get Undergrad"
                ],
                "PAUSE_TIMER": [
                    "Pause Timer"
                ],
                "UPDATE_ALARM": [
                    "Update Alarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "Get Reminder Location"
                ],
                "GET_ATTENDEE_EVENT": [
                    "Get Attendee Event"
                ],
                "LIKE_MUSIC": [
                    "Like Music"
                ],
                "RESTART_TIMER": [
                    "Restart Timer"
                ],
                "RESUME_TIMER": [
                    "Resume Timer"
                ],
                "MERGE_CALL": [
                    "Merge Call"
                ],
                "GET_MESSAGE_CONTACT": [
                    "Get Message Contact"
                ],
                "REPLAY_MUSIC": [
                    "Replay Music"
                ],
                "LOOP_MUSIC": [
                    "Loop Music"
                ],
                "GET_REMINDER_AMOUNT": [
                    "Get Reminder Amount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "Get Date Time Event"
                ],
                "STOP_MUSIC": [
                    "Stop Music"
                ],
                "GET_DETAILS_NEWS": [
                    "Get Details News"
                ],
                "GET_EDUCATION_DEGREE": [
                    "Get Education Degree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "Set Default Provider Calling"
                ],
                "GET_MAJOR": [
                    "Get Major"
                ],
                "UNLOOP_MUSIC": [
                    "Unloop Music"
                ],
                "GET_CONTACT_METHOD": [
                    "Get Contact Method"
                ],
                "SET_RSVP_NO": [
                    "Set Rsvp No"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "Update Reminder Location"
                ],
                "RESUME_CALL": [
                    "Resume Call"
                ],
                "CANCEL_MESSAGE": [
                    "Cancel Message"
                ],
                "RESUME_MUSIC": [
                    "Resume Music"
                ],
                "UPDATE_REMINDER": [
                    "Update Reminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "Delete Playlist Music"
                ],
                "REWIND_MUSIC": [
                    "Rewind Music"
                ],
                "REPEAT_ALL_MUSIC": [
                    "Repeat All Music"
                ],
                "FAST_FORWARD_MUSIC": [
                    "Fast Forward Music"
                ],
                "DISLIKE_MUSIC": [
                    "Dislike Music"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "Get Life Event Time"
                ],
                "DISPREFER": [
                    "Disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "Repeat All Off Music"
                ],
                "HELP_REMINDER": [
                    "Help Reminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "Get Lyrics Music"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "Stop Shuffle Music"
                ],
                "GET_AIRQUALITY": [
                    "Get Airquality"
                ],
                "GET_LANGUAGE": [
                    "Get Language"
                ],
                "FOLLOW_MUSIC": [
                    "Follow Music"
                ],
                "GET_GENDER": [
                    "Get Gender"
                ],
                "CANCEL_CALL": [
                    "Cancel Call"
                ],
                "GET_GROUP": [
                    "Get Group"
                ]
            },
            "version_3": {
                "GET_MESSAGE": [
                    "GetMessage"
                ],
                "GET_WEATHER": [
                    "GetWeather"
                ],
                "GET_ALARM": [
                    "GetAlarm"
                ],
                "SEND_MESSAGE": [
                    "SendMessage"
                ],
                "GET_INFO_RECIPES": [
                    "GetInfoRecipes"
                ],
                "SET_UNAVAILABLE": [
                    "SetUnavailable"
                ],
                "DELETE_REMINDER": [
                    "DeleteReminder"
                ],
                "GET_STORIES_NEWS": [
                    "GetStoriesNews"
                ],
                "CREATE_ALARM": [
                    "CreateAlarm"
                ],
                "GET_REMINDER": [
                    "GetReminder"
                ],
                "CREATE_REMINDER": [
                    "CreateReminder"
                ],
                "GET_RECIPES": [
                    "GetRecipes"
                ],
                "QUESTION_NEWS": [
                    "QuestionNews"
                ],
                "GET_EVENT": [
                    "GetEvent"
                ],
                "PLAY_MUSIC": [
                    "PlayMusic"
                ],
                "GET_CALL_TIME": [
                    "GetCallTime"
                ],
                "CREATE_CALL": [
                    "CreateCall"
                ],
                "END_CALL": [
                    "EndCall"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "CreatePlaylistMusic"
                ],
                "CREATE_TIMER": [
                    "CreateTimer"
                ],
                "IGNORE_CALL": [
                    "IgnoreCall"
                ],
                "GET_LIFE_EVENT": [
                    "GetLifeEvent"
                ],
                "GET_INFO_CONTACT": [
                    "GetInfoContact"
                ],
                "UPDATE_CALL": [
                    "UpdateCall"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "UpdateReminderDateTime"
                ],
                "GET_CONTACT": [
                    "GetContact"
                ],
                "GET_TIMER": [
                    "GetTimer"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "GetReminderDateTime"
                ],
                "DELETE_ALARM": [
                    "DeleteAlarm"
                ],
                "PAUSE_MUSIC": [
                    "PauseMusic"
                ],
                "GET_AGE": [
                    "GetAge"
                ],
                "GET_SUNRISE": [
                    "GetSunrise"
                ],
                "GET_EMPLOYER": [
                    "GetEmployer"
                ],
                "GET_EDUCATION_TIME": [
                    "GetEducationTime"
                ],
                "ANSWER_CALL": [
                    "AnswerCall"
                ],
                "SET_RSVP_YES": [
                    "SetRsvpYes"
                ],
                "SNOOZE_ALARM": [
                    "SnoozeAlarm"
                ],
                "GET_JOB": [
                    "GetJob"
                ],
                "UPDATE_REMINDER_TODO": [
                    "UpdateReminderTodo"
                ],
                "IS_TRUE_RECIPES": [
                    "IsTrueRecipes"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "RemoveFromPlaylistMusic"
                ],
                "GET_AVAILABILITY": [
                    "GetAvailability"
                ],
                "GET_CATEGORY_EVENT": [
                    "GetCategoryEvent"
                ],
                "PLAY_MEDIA": [
                    "PlayMedia"
                ],
                "ADD_TIME_TIMER": [
                    "AddTimeTimer"
                ],
                "GET_CALL": [
                    "GetCall"
                ],
                "SET_AVAILABLE": [
                    "SetAvailable"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "AddToPlaylistMusic"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "GetEmploymentTime"
                ],
                "SHARE_EVENT": [
                    "ShareEvent"
                ],
                "PREFER": [
                    "Prefer"
                ],
                "START_SHUFFLE_MUSIC": [
                    "StartShuffleMusic"
                ],
                "GET_CALL_CONTACT": [
                    "GetCallContact"
                ],
                "GET_LOCATION": [
                    "GetLocation"
                ],
                "SILENCE_ALARM": [
                    "SilenceAlarm"
                ],
                "SWITCH_CALL": [
                    "SwitchCall"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "GetTrackInfoMusic"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "SubtractTimeTimer"
                ],
                "GET_SUNSET": [
                    "GetSunset"
                ],
                "DELETE_TIMER": [
                    "DeleteTimer"
                ],
                "UPDATE_TIMER": [
                    "UpdateTimer"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "PreviousTrackMusic"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "SetDefaultProviderMusic"
                ],
                "HOLD_CALL": [
                    "HoldCall"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "GetMutualFriends"
                ],
                "SKIP_TRACK_MUSIC": [
                    "SkipTrackMusic"
                ],
                "UPDATE_METHOD_CALL": [
                    "UpdateMethodCall"
                ],
                "SET_RSVP_INTERESTED": [
                    "SetRsvpInterested"
                ],
                "QUESTION_MUSIC": [
                    "QuestionMusic"
                ],
                "GET_UNDERGRAD": [
                    "GetUndergrad"
                ],
                "PAUSE_TIMER": [
                    "PauseTimer"
                ],
                "UPDATE_ALARM": [
                    "UpdateAlarm"
                ],
                "GET_REMINDER_LOCATION": [
                    "GetReminderLocation"
                ],
                "GET_ATTENDEE_EVENT": [
                    "GetAttendeeEvent"
                ],
                "LIKE_MUSIC": [
                    "LikeMusic"
                ],
                "RESTART_TIMER": [
                    "RestartTimer"
                ],
                "RESUME_TIMER": [
                    "ResumeTimer"
                ],
                "MERGE_CALL": [
                    "MergeCall"
                ],
                "GET_MESSAGE_CONTACT": [
                    "GetMessageContact"
                ],
                "REPLAY_MUSIC": [
                    "ReplayMusic"
                ],
                "LOOP_MUSIC": [
                    "LoopMusic"
                ],
                "GET_REMINDER_AMOUNT": [
                    "GetReminderAmount"
                ],
                "GET_DATE_TIME_EVENT": [
                    "GetDateTimeEvent"
                ],
                "STOP_MUSIC": [
                    "StopMusic"
                ],
                "GET_DETAILS_NEWS": [
                    "GetDetailsNews"
                ],
                "GET_EDUCATION_DEGREE": [
                    "GetEducationDegree"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "SetDefaultProviderCalling"
                ],
                "GET_MAJOR": [
                    "GetMajor"
                ],
                "UNLOOP_MUSIC": [
                    "UnloopMusic"
                ],
                "GET_CONTACT_METHOD": [
                    "GetContactMethod"
                ],
                "SET_RSVP_NO": [
                    "SetRsvpNo"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "UpdateReminderLocation"
                ],
                "RESUME_CALL": [
                    "ResumeCall"
                ],
                "CANCEL_MESSAGE": [
                    "CancelMessage"
                ],
                "RESUME_MUSIC": [
                    "ResumeMusic"
                ],
                "UPDATE_REMINDER": [
                    "UpdateReminder"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "DeletePlaylistMusic"
                ],
                "REWIND_MUSIC": [
                    "RewindMusic"
                ],
                "REPEAT_ALL_MUSIC": [
                    "RepeatAllMusic"
                ],
                "FAST_FORWARD_MUSIC": [
                    "FastForwardMusic"
                ],
                "DISLIKE_MUSIC": [
                    "DislikeMusic"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "GetLifeEventTime"
                ],
                "DISPREFER": [
                    "Disprefer"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "RepeatAllOffMusic"
                ],
                "HELP_REMINDER": [
                    "HelpReminder"
                ],
                "GET_LYRICS_MUSIC": [
                    "GetLyricsMusic"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "StopShuffleMusic"
                ],
                "GET_AIRQUALITY": [
                    "GetAirquality"
                ],
                "GET_LANGUAGE": [
                    "GetLanguage"
                ],
                "FOLLOW_MUSIC": [
                    "FollowMusic"
                ],
                "GET_GENDER": [
                    "GetGender"
                ],
                "CANCEL_CALL": [
                    "CancelCall"
                ],
                "GET_GROUP": [
                    "GetGroup"
                ]
            },
            "version_4": {
                "GET_MESSAGE": [
                    "GET_MESSAGE"
                ],
                "GET_WEATHER": [
                    "GET_WEATHER"
                ],
                "GET_ALARM": [
                    "GET_ALARM"
                ],
                "SEND_MESSAGE": [
                    "SEND_MESSAGE"
                ],
                "GET_INFO_RECIPES": [
                    "GET_INFO_RECIPES"
                ],
                "SET_UNAVAILABLE": [
                    "SET_UNAVAILABLE"
                ],
                "DELETE_REMINDER": [
                    "DELETE_REMINDER"
                ],
                "GET_STORIES_NEWS": [
                    "GET_STORIES_NEWS"
                ],
                "CREATE_ALARM": [
                    "CREATE_ALARM"
                ],
                "GET_REMINDER": [
                    "GET_REMINDER"
                ],
                "CREATE_REMINDER": [
                    "CREATE_REMINDER"
                ],
                "GET_RECIPES": [
                    "GET_RECIPES"
                ],
                "QUESTION_NEWS": [
                    "QUESTION_NEWS"
                ],
                "GET_EVENT": [
                    "GET_EVENT"
                ],
                "PLAY_MUSIC": [
                    "PLAY_MUSIC"
                ],
                "GET_CALL_TIME": [
                    "GET_CALL_TIME"
                ],
                "CREATE_CALL": [
                    "CREATE_CALL"
                ],
                "END_CALL": [
                    "END_CALL"
                ],
                "CREATE_PLAYLIST_MUSIC": [
                    "CREATE_PLAYLIST_MUSIC"
                ],
                "CREATE_TIMER": [
                    "CREATE_TIMER"
                ],
                "IGNORE_CALL": [
                    "IGNORE_CALL"
                ],
                "GET_LIFE_EVENT": [
                    "GET_LIFE_EVENT"
                ],
                "GET_INFO_CONTACT": [
                    "GET_INFO_CONTACT"
                ],
                "UPDATE_CALL": [
                    "UPDATE_CALL"
                ],
                "UPDATE_REMINDER_DATE_TIME": [
                    "UPDATE_REMINDER_DATE_TIME"
                ],
                "GET_CONTACT": [
                    "GET_CONTACT"
                ],
                "GET_TIMER": [
                    "GET_TIMER"
                ],
                "GET_REMINDER_DATE_TIME": [
                    "GET_REMINDER_DATE_TIME"
                ],
                "DELETE_ALARM": [
                    "DELETE_ALARM"
                ],
                "PAUSE_MUSIC": [
                    "PAUSE_MUSIC"
                ],
                "GET_AGE": [
                    "GET_AGE"
                ],
                "GET_SUNRISE": [
                    "GET_SUNRISE"
                ],
                "GET_EMPLOYER": [
                    "GET_EMPLOYER"
                ],
                "GET_EDUCATION_TIME": [
                    "GET_EDUCATION_TIME"
                ],
                "ANSWER_CALL": [
                    "ANSWER_CALL"
                ],
                "SET_RSVP_YES": [
                    "SET_RSVP_YES"
                ],
                "SNOOZE_ALARM": [
                    "SNOOZE_ALARM"
                ],
                "GET_JOB": [
                    "GET_JOB"
                ],
                "UPDATE_REMINDER_TODO": [
                    "UPDATE_REMINDER_TODO"
                ],
                "IS_TRUE_RECIPES": [
                    "IS_TRUE_RECIPES"
                ],
                "REMOVE_FROM_PLAYLIST_MUSIC": [
                    "REMOVE_FROM_PLAYLIST_MUSIC"
                ],
                "GET_AVAILABILITY": [
                    "GET_AVAILABILITY"
                ],
                "GET_CATEGORY_EVENT": [
                    "GET_CATEGORY_EVENT"
                ],
                "PLAY_MEDIA": [
                    "PLAY_MEDIA"
                ],
                "ADD_TIME_TIMER": [
                    "ADD_TIME_TIMER"
                ],
                "GET_CALL": [
                    "GET_CALL"
                ],
                "SET_AVAILABLE": [
                    "SET_AVAILABLE"
                ],
                "ADD_TO_PLAYLIST_MUSIC": [
                    "ADD_TO_PLAYLIST_MUSIC"
                ],
                "GET_EMPLOYMENT_TIME": [
                    "GET_EMPLOYMENT_TIME"
                ],
                "SHARE_EVENT": [
                    "SHARE_EVENT"
                ],
                "PREFER": [
                    "PREFER"
                ],
                "START_SHUFFLE_MUSIC": [
                    "START_SHUFFLE_MUSIC"
                ],
                "GET_CALL_CONTACT": [
                    "GET_CALL_CONTACT"
                ],
                "GET_LOCATION": [
                    "GET_LOCATION"
                ],
                "SILENCE_ALARM": [
                    "SILENCE_ALARM"
                ],
                "SWITCH_CALL": [
                    "SWITCH_CALL"
                ],
                "GET_TRACK_INFO_MUSIC": [
                    "GET_TRACK_INFO_MUSIC"
                ],
                "SUBTRACT_TIME_TIMER": [
                    "SUBTRACT_TIME_TIMER"
                ],
                "GET_SUNSET": [
                    "GET_SUNSET"
                ],
                "DELETE_TIMER": [
                    "DELETE_TIMER"
                ],
                "UPDATE_TIMER": [
                    "UPDATE_TIMER"
                ],
                "PREVIOUS_TRACK_MUSIC": [
                    "PREVIOUS_TRACK_MUSIC"
                ],
                "SET_DEFAULT_PROVIDER_MUSIC": [
                    "SET_DEFAULT_PROVIDER_MUSIC"
                ],
                "HOLD_CALL": [
                    "HOLD_CALL"
                ],
                "GET_MUTUAL_FRIENDS": [
                    "GET_MUTUAL_FRIENDS"
                ],
                "SKIP_TRACK_MUSIC": [
                    "SKIP_TRACK_MUSIC"
                ],
                "UPDATE_METHOD_CALL": [
                    "UPDATE_METHOD_CALL"
                ],
                "SET_RSVP_INTERESTED": [
                    "SET_RSVP_INTERESTED"
                ],
                "QUESTION_MUSIC": [
                    "QUESTION_MUSIC"
                ],
                "GET_UNDERGRAD": [
                    "GET_UNDERGRAD"
                ],
                "PAUSE_TIMER": [
                    "PAUSE_TIMER"
                ],
                "UPDATE_ALARM": [
                    "UPDATE_ALARM"
                ],
                "GET_REMINDER_LOCATION": [
                    "GET_REMINDER_LOCATION"
                ],
                "GET_ATTENDEE_EVENT": [
                    "GET_ATTENDEE_EVENT"
                ],
                "LIKE_MUSIC": [
                    "LIKE_MUSIC"
                ],
                "RESTART_TIMER": [
                    "RESTART_TIMER"
                ],
                "RESUME_TIMER": [
                    "RESUME_TIMER"
                ],
                "MERGE_CALL": [
                    "MERGE_CALL"
                ],
                "GET_MESSAGE_CONTACT": [
                    "GET_MESSAGE_CONTACT"
                ],
                "REPLAY_MUSIC": [
                    "REPLAY_MUSIC"
                ],
                "LOOP_MUSIC": [
                    "LOOP_MUSIC"
                ],
                "GET_REMINDER_AMOUNT": [
                    "GET_REMINDER_AMOUNT"
                ],
                "GET_DATE_TIME_EVENT": [
                    "GET_DATE_TIME_EVENT"
                ],
                "STOP_MUSIC": [
                    "STOP_MUSIC"
                ],
                "GET_DETAILS_NEWS": [
                    "GET_DETAILS_NEWS"
                ],
                "GET_EDUCATION_DEGREE": [
                    "GET_EDUCATION_DEGREE"
                ],
                "SET_DEFAULT_PROVIDER_CALLING": [
                    "SET_DEFAULT_PROVIDER_CALLING"
                ],
                "GET_MAJOR": [
                    "GET_MAJOR"
                ],
                "UNLOOP_MUSIC": [
                    "UNLOOP_MUSIC"
                ],
                "GET_CONTACT_METHOD": [
                    "GET_CONTACT_METHOD"
                ],
                "SET_RSVP_NO": [
                    "SET_RSVP_NO"
                ],
                "UPDATE_REMINDER_LOCATION": [
                    "UPDATE_REMINDER_LOCATION"
                ],
                "RESUME_CALL": [
                    "RESUME_CALL"
                ],
                "CANCEL_MESSAGE": [
                    "CANCEL_MESSAGE"
                ],
                "RESUME_MUSIC": [
                    "RESUME_MUSIC"
                ],
                "UPDATE_REMINDER": [
                    "UPDATE_REMINDER"
                ],
                "DELETE_PLAYLIST_MUSIC": [
                    "DELETE_PLAYLIST_MUSIC"
                ],
                "REWIND_MUSIC": [
                    "REWIND_MUSIC"
                ],
                "REPEAT_ALL_MUSIC": [
                    "REPEAT_ALL_MUSIC"
                ],
                "FAST_FORWARD_MUSIC": [
                    "FAST_FORWARD_MUSIC"
                ],
                "DISLIKE_MUSIC": [
                    "DISLIKE_MUSIC"
                ],
                "GET_LIFE_EVENT_TIME": [
                    "GET_LIFE_EVENT_TIME"
                ],
                "DISPREFER": [
                    "DISPREFER"
                ],
                "REPEAT_ALL_OFF_MUSIC": [
                    "REPEAT_ALL_OFF_MUSIC"
                ],
                "HELP_REMINDER": [
                    "HELP_REMINDER"
                ],
                "GET_LYRICS_MUSIC": [
                    "GET_LYRICS_MUSIC"
                ],
                "STOP_SHUFFLE_MUSIC": [
                    "STOP_SHUFFLE_MUSIC"
                ],
                "GET_AIRQUALITY": [
                    "GET_AIRQUALITY"
                ],
                "GET_LANGUAGE": [
                    "GET_LANGUAGE"
                ],
                "FOLLOW_MUSIC": [
                    "FOLLOW_MUSIC"
                ],
                "GET_GENDER": [
                    "GET_GENDER"
                ],
                "CANCEL_CALL": [
                    "CANCEL_CALL"
                ],
                "GET_GROUP": [
                    "GET_GROUP"
                ]
            }
        },
        "out_of_scope": {
            "version_0": {
                "translate": [
                    "translate"
                ],
                "transfer": [
                    "transfer"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning_of_life"
                ],
                "insurance_change": [
                    "insurance_change"
                ],
                "find_phone": [
                    "find_phone"
                ],
                "travel_alert": [
                    "travel_alert"
                ],
                "pto_request": [
                    "pto_request"
                ],
                "improve_credit_score": [
                    "improve_credit_score"
                ],
                "fun_fact": [
                    "fun_fact"
                ],
                "change_language": [
                    "change_language"
                ],
                "payday": [
                    "payday"
                ],
                "replacement_card_duration": [
                    "replacement_card_duration"
                ],
                "time": [
                    "time"
                ],
                "application_status": [
                    "application_status"
                ],
                "flight_status": [
                    "flight_status"
                ],
                "flip_coin": [
                    "flip_coin"
                ],
                "change_user_name": [
                    "change_user_name"
                ],
                "where_are_you_from": [
                    "where_are_you_from"
                ],
                "shopping_list_update": [
                    "shopping_list_update"
                ],
                "what_can_i_ask_you": [
                    "what_can_i_ask_you"
                ],
                "maybe": [
                    "maybe"
                ],
                "oil_change_how": [
                    "oil_change_how"
                ],
                "restaurant_reservation": [
                    "restaurant_reservation"
                ],
                "balance": [
                    "balance"
                ],
                "confirm_reservation": [
                    "confirm_reservation"
                ],
                "freeze_account": [
                    "freeze_account"
                ],
                "rollover_401k": [
                    "rollover_401k"
                ],
                "who_made_you": [
                    "who_made_you"
                ],
                "distance": [
                    "distance"
                ],
                "user_name": [
                    "user_name"
                ],
                "timezone": [
                    "timezone"
                ],
                "next_song": [
                    "next_song"
                ],
                "transactions": [
                    "transactions"
                ],
                "restaurant_suggestion": [
                    "restaurant_suggestion"
                ],
                "rewards_balance": [
                    "rewards_balance"
                ],
                "pay_bill": [
                    "pay_bill"
                ],
                "spending_history": [
                    "spending_history"
                ],
                "pto_request_status": [
                    "pto_request_status"
                ],
                "credit_score": [
                    "credit_score"
                ],
                "new_card": [
                    "new_card"
                ],
                "lost_luggage": [
                    "lost_luggage"
                ],
                "repeat": [
                    "repeat"
                ],
                "mpg": [
                    "mpg"
                ],
                "oil_change_when": [
                    "oil_change_when"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel_suggestion"
                ],
                "insurance": [
                    "insurance"
                ],
                "todo_list_update": [
                    "todo_list_update"
                ],
                "reminder": [
                    "reminder"
                ],
                "change_speed": [
                    "change_speed"
                ],
                "tire_pressure": [
                    "tire_pressure"
                ],
                "no": [
                    "no"
                ],
                "apr": [
                    "apr"
                ],
                "nutrition_info": [
                    "nutrition_info"
                ],
                "calendar": [
                    "calendar"
                ],
                "uber": [
                    "uber"
                ],
                "calculator": [
                    "calculator"
                ],
                "date": [
                    "date"
                ],
                "carry_on": [
                    "carry_on"
                ],
                "pto_used": [
                    "pto_used"
                ],
                "schedule_maintenance": [
                    "schedule_maintenance"
                ],
                "travel_notification": [
                    "travel_notification"
                ],
                "sync_device": [
                    "sync_device"
                ],
                "thank_you": [
                    "thank_you"
                ],
                "roll_dice": [
                    "roll_dice"
                ],
                "food_last": [
                    "food_last"
                ],
                "cook_time": [
                    "cook_time"
                ],
                "reminder_update": [
                    "reminder_update"
                ],
                "report_lost_card": [
                    "report_lost_card"
                ],
                "ingredient_substitution": [
                    "ingredient_substitution"
                ],
                "make_call": [
                    "make_call"
                ],
                "alarm": [
                    "alarm"
                ],
                "todo_list": [
                    "todo_list"
                ],
                "change_accent": [
                    "change_accent"
                ],
                "w2": [
                    "w2"
                ],
                "bill_due": [
                    "bill_due"
                ],
                "calories": [
                    "calories"
                ],
                "damaged_card": [
                    "damaged_card"
                ],
                "restaurant_reviews": [
                    "restaurant_reviews"
                ],
                "routing": [
                    "routing"
                ],
                "do_you_have_pets": [
                    "do_you_have_pets"
                ],
                "schedule_meeting": [
                    "schedule_meeting"
                ],
                "gas_type": [
                    "gas_type"
                ],
                "plug_type": [
                    "plug_type"
                ],
                "tire_change": [
                    "tire_change"
                ],
                "exchange_rate": [
                    "exchange_rate"
                ],
                "next_holiday": [
                    "next_holiday"
                ],
                "change_volume": [
                    "change_volume"
                ],
                "who_do_you_work_for": [
                    "who_do_you_work_for"
                ],
                "credit_limit": [
                    "credit_limit"
                ],
                "how_busy": [
                    "how_busy"
                ],
                "accept_reservations": [
                    "accept_reservations"
                ],
                "order_status": [
                    "order_status"
                ],
                "pin_change": [
                    "pin_change"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "account_blocked": [
                    "account_blocked"
                ],
                "what_song": [
                    "what_song"
                ],
                "international_fees": [
                    "international_fees"
                ],
                "last_maintenance": [
                    "last_maintenance"
                ],
                "meeting_schedule": [
                    "meeting_schedule"
                ],
                "ingredients_list": [
                    "ingredients_list"
                ],
                "report_fraud": [
                    "report_fraud"
                ],
                "measurement_conversion": [
                    "measurement_conversion"
                ],
                "smart_home": [
                    "smart_home"
                ],
                "book_hotel": [
                    "book_hotel"
                ],
                "current_location": [
                    "current_location"
                ],
                "weather": [
                    "weather"
                ],
                "taxes": [
                    "taxes"
                ],
                "min_payment": [
                    "min_payment"
                ],
                "whisper_mode": [
                    "whisper_mode"
                ],
                "cancel": [
                    "cancel"
                ],
                "international_visa": [
                    "international_visa"
                ],
                "vaccines": [
                    "vaccines"
                ],
                "pto_balance": [
                    "pto_balance"
                ],
                "directions": [
                    "directions"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset_settings"
                ],
                "what_is_your_name": [
                    "what_is_your_name"
                ],
                "direct_deposit": [
                    "direct_deposit"
                ],
                "interest_rate": [
                    "interest_rate"
                ],
                "credit_limit_change": [
                    "credit_limit_change"
                ],
                "what_are_your_hobbies": [
                    "what_are_your_hobbies"
                ],
                "book_flight": [
                    "book_flight"
                ],
                "shopping_list": [
                    "shopping_list"
                ],
                "text": [
                    "text"
                ],
                "bill_balance": [
                    "bill_balance"
                ],
                "share_location": [
                    "share_location"
                ],
                "redeem_rewards": [
                    "redeem_rewards"
                ],
                "play_music": [
                    "play_music"
                ],
                "calendar_update": [
                    "calendar_update"
                ],
                "are_you_a_bot": [
                    "are_you_a_bot"
                ],
                "gas": [
                    "gas"
                ],
                "expiration_date": [
                    "expiration_date"
                ],
                "update_playlist": [
                    "update_playlist"
                ],
                "cancel_reservation": [
                    "cancel_reservation"
                ],
                "tell_joke": [
                    "tell_joke"
                ],
                "change_ai_name": [
                    "change_ai_name"
                ],
                "how_old_are_you": [
                    "how_old_are_you"
                ],
                "car_rental": [
                    "car_rental"
                ],
                "jump_start": [
                    "jump_start"
                ],
                "meal_suggestion": [
                    "meal_suggestion"
                ],
                "recipe": [
                    "recipe"
                ],
                "income": [
                    "income"
                ],
                "order": [
                    "order"
                ],
                "traffic": [
                    "traffic"
                ],
                "order_checks": [
                    "order_checks"
                ],
                "card_declined": [
                    "card_declined"
                ]
            },
            "version_1": {
                "translate": [
                    "translate"
                ],
                "transfer": [
                    "transfer"
                ],
                "timer": [
                    "timer"
                ],
                "definition": [
                    "definition"
                ],
                "meaning_of_life": [
                    "meaning of life"
                ],
                "insurance_change": [
                    "insurance change"
                ],
                "find_phone": [
                    "find phone"
                ],
                "travel_alert": [
                    "travel alert"
                ],
                "pto_request": [
                    "pto request"
                ],
                "improve_credit_score": [
                    "improve credit score"
                ],
                "fun_fact": [
                    "fun fact"
                ],
                "change_language": [
                    "change language"
                ],
                "payday": [
                    "payday"
                ],
                "replacement_card_duration": [
                    "replacement card duration"
                ],
                "time": [
                    "time"
                ],
                "application_status": [
                    "application status"
                ],
                "flight_status": [
                    "flight status"
                ],
                "flip_coin": [
                    "flip coin"
                ],
                "change_user_name": [
                    "change user name"
                ],
                "where_are_you_from": [
                    "where are you from"
                ],
                "shopping_list_update": [
                    "shopping list update"
                ],
                "what_can_i_ask_you": [
                    "what can i ask you"
                ],
                "maybe": [
                    "maybe"
                ],
                "oil_change_how": [
                    "oil change how"
                ],
                "restaurant_reservation": [
                    "restaurant reservation"
                ],
                "balance": [
                    "balance"
                ],
                "confirm_reservation": [
                    "confirm reservation"
                ],
                "freeze_account": [
                    "freeze account"
                ],
                "rollover_401k": [
                    "rollover 401k"
                ],
                "who_made_you": [
                    "who made you"
                ],
                "distance": [
                    "distance"
                ],
                "user_name": [
                    "user name"
                ],
                "timezone": [
                    "timezone"
                ],
                "next_song": [
                    "next song"
                ],
                "transactions": [
                    "transactions"
                ],
                "restaurant_suggestion": [
                    "restaurant suggestion"
                ],
                "rewards_balance": [
                    "rewards balance"
                ],
                "pay_bill": [
                    "pay bill"
                ],
                "spending_history": [
                    "spending history"
                ],
                "pto_request_status": [
                    "pto request status"
                ],
                "credit_score": [
                    "credit score"
                ],
                "new_card": [
                    "new card"
                ],
                "lost_luggage": [
                    "lost luggage"
                ],
                "repeat": [
                    "repeat"
                ],
                "mpg": [
                    "mpg"
                ],
                "oil_change_when": [
                    "oil change when"
                ],
                "yes": [
                    "yes"
                ],
                "travel_suggestion": [
                    "travel suggestion"
                ],
                "insurance": [
                    "insurance"
                ],
                "todo_list_update": [
                    "todo list update"
                ],
                "reminder": [
                    "reminder"
                ],
                "change_speed": [
                    "change speed"
                ],
                "tire_pressure": [
                    "tire pressure"
                ],
                "no": [
                    "no"
                ],
                "apr": [
                    "apr"
                ],
                "nutrition_info": [
                    "nutrition info"
                ],
                "calendar": [
                    "calendar"
                ],
                "uber": [
                    "uber"
                ],
                "calculator": [
                    "calculator"
                ],
                "date": [
                    "date"
                ],
                "carry_on": [
                    "carry on"
                ],
                "pto_used": [
                    "pto used"
                ],
                "schedule_maintenance": [
                    "schedule maintenance"
                ],
                "travel_notification": [
                    "travel notification"
                ],
                "sync_device": [
                    "sync device"
                ],
                "thank_you": [
                    "thank you"
                ],
                "roll_dice": [
                    "roll dice"
                ],
                "food_last": [
                    "food last"
                ],
                "cook_time": [
                    "cook time"
                ],
                "reminder_update": [
                    "reminder update"
                ],
                "report_lost_card": [
                    "report lost card"
                ],
                "ingredient_substitution": [
                    "ingredient substitution"
                ],
                "make_call": [
                    "make call"
                ],
                "alarm": [
                    "alarm"
                ],
                "todo_list": [
                    "todo list"
                ],
                "change_accent": [
                    "change accent"
                ],
                "w2": [
                    "w2"
                ],
                "bill_due": [
                    "bill due"
                ],
                "calories": [
                    "calories"
                ],
                "damaged_card": [
                    "damaged card"
                ],
                "restaurant_reviews": [
                    "restaurant reviews"
                ],
                "routing": [
                    "routing"
                ],
                "do_you_have_pets": [
                    "do you have pets"
                ],
                "schedule_meeting": [
                    "schedule meeting"
                ],
                "gas_type": [
                    "gas type"
                ],
                "plug_type": [
                    "plug type"
                ],
                "tire_change": [
                    "tire change"
                ],
                "exchange_rate": [
                    "exchange rate"
                ],
                "next_holiday": [
                    "next holiday"
                ],
                "change_volume": [
                    "change volume"
                ],
                "who_do_you_work_for": [
                    "who do you work for"
                ],
                "credit_limit": [
                    "credit limit"
                ],
                "how_busy": [
                    "how busy"
                ],
                "accept_reservations": [
                    "accept reservations"
                ],
                "order_status": [
                    "order status"
                ],
                "pin_change": [
                    "pin change"
                ],
                "goodbye": [
                    "goodbye"
                ],
                "account_blocked": [
                    "account blocked"
                ],
                "what_song": [
                    "what song"
                ],
                "international_fees": [
                    "international fees"
                ],
                "last_maintenance": [
                    "last maintenance"
                ],
                "meeting_schedule": [
                    "meeting schedule"
                ],
                "ingredients_list": [
                    "ingredients list"
                ],
                "report_fraud": [
                    "report fraud"
                ],
                "measurement_conversion": [
                    "measurement conversion"
                ],
                "smart_home": [
                    "smart home"
                ],
                "book_hotel": [
                    "book hotel"
                ],
                "current_location": [
                    "current location"
                ],
                "weather": [
                    "weather"
                ],
                "taxes": [
                    "taxes"
                ],
                "min_payment": [
                    "min payment"
                ],
                "whisper_mode": [
                    "whisper mode"
                ],
                "cancel": [
                    "cancel"
                ],
                "international_visa": [
                    "international visa"
                ],
                "vaccines": [
                    "vaccines"
                ],
                "pto_balance": [
                    "pto balance"
                ],
                "directions": [
                    "directions"
                ],
                "spelling": [
                    "spelling"
                ],
                "greeting": [
                    "greeting"
                ],
                "reset_settings": [
                    "reset settings"
                ],
                "what_is_your_name": [
                    "what is your name"
                ],
                "direct_deposit": [
                    "direct deposit"
                ],
                "interest_rate": [
                    "interest rate"
                ],
                "credit_limit_change": [
                    "credit limit change"
                ],
                "what_are_your_hobbies": [
                    "what are your hobbies"
                ],
                "book_flight": [
                    "book flight"
                ],
                "shopping_list": [
                    "shopping list"
                ],
                "text": [
                    "text"
                ],
                "bill_balance": [
                    "bill balance"
                ],
                "share_location": [
                    "share location"
                ],
                "redeem_rewards": [
                    "redeem rewards"
                ],
                "play_music": [
                    "play music"
                ],
                "calendar_update": [
                    "calendar update"
                ],
                "are_you_a_bot": [
                    "are you a bot"
                ],
                "gas": [
                    "gas"
                ],
                "expiration_date": [
                    "expiration date"
                ],
                "update_playlist": [
                    "update playlist"
                ],
                "cancel_reservation": [
                    "cancel reservation"
                ],
                "tell_joke": [
                    "tell joke"
                ],
                "change_ai_name": [
                    "change ai name"
                ],
                "how_old_are_you": [
                    "how old are you"
                ],
                "car_rental": [
                    "car rental"
                ],
                "jump_start": [
                    "jump start"
                ],
                "meal_suggestion": [
                    "meal suggestion"
                ],
                "recipe": [
                    "recipe"
                ],
                "income": [
                    "income"
                ],
                "order": [
                    "order"
                ],
                "traffic": [
                    "traffic"
                ],
                "order_checks": [
                    "order checks"
                ],
                "card_declined": [
                    "card declined"
                ]
            },
            "version_2": {
                "translate": [
                    "Translate"
                ],
                "transfer": [
                    "Transfer"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "Meaning Of Life"
                ],
                "insurance_change": [
                    "Insurance Change"
                ],
                "find_phone": [
                    "Find Phone"
                ],
                "travel_alert": [
                    "Travel Alert"
                ],
                "pto_request": [
                    "Pto Request"
                ],
                "improve_credit_score": [
                    "Improve Credit Score"
                ],
                "fun_fact": [
                    "Fun Fact"
                ],
                "change_language": [
                    "Change Language"
                ],
                "payday": [
                    "Payday"
                ],
                "replacement_card_duration": [
                    "Replacement Card Duration"
                ],
                "time": [
                    "Time"
                ],
                "application_status": [
                    "Application Status"
                ],
                "flight_status": [
                    "Flight Status"
                ],
                "flip_coin": [
                    "Flip Coin"
                ],
                "change_user_name": [
                    "Change User Name"
                ],
                "where_are_you_from": [
                    "Where Are You From"
                ],
                "shopping_list_update": [
                    "Shopping List Update"
                ],
                "what_can_i_ask_you": [
                    "What Can I Ask You"
                ],
                "maybe": [
                    "Maybe"
                ],
                "oil_change_how": [
                    "Oil Change How"
                ],
                "restaurant_reservation": [
                    "Restaurant Reservation"
                ],
                "balance": [
                    "Balance"
                ],
                "confirm_reservation": [
                    "Confirm Reservation"
                ],
                "freeze_account": [
                    "Freeze Account"
                ],
                "rollover_401k": [
                    "Rollover 401k"
                ],
                "who_made_you": [
                    "Who Made You"
                ],
                "distance": [
                    "Distance"
                ],
                "user_name": [
                    "User Name"
                ],
                "timezone": [
                    "Timezone"
                ],
                "next_song": [
                    "Next Song"
                ],
                "transactions": [
                    "Transactions"
                ],
                "restaurant_suggestion": [
                    "Restaurant Suggestion"
                ],
                "rewards_balance": [
                    "Rewards Balance"
                ],
                "pay_bill": [
                    "Pay Bill"
                ],
                "spending_history": [
                    "Spending History"
                ],
                "pto_request_status": [
                    "Pto Request Status"
                ],
                "credit_score": [
                    "Credit Score"
                ],
                "new_card": [
                    "New Card"
                ],
                "lost_luggage": [
                    "Lost Luggage"
                ],
                "repeat": [
                    "Repeat"
                ],
                "mpg": [
                    "Mpg"
                ],
                "oil_change_when": [
                    "Oil Change When"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "Travel Suggestion"
                ],
                "insurance": [
                    "Insurance"
                ],
                "todo_list_update": [
                    "Todo List Update"
                ],
                "reminder": [
                    "Reminder"
                ],
                "change_speed": [
                    "Change Speed"
                ],
                "tire_pressure": [
                    "Tire Pressure"
                ],
                "no": [
                    "No"
                ],
                "apr": [
                    "Apr"
                ],
                "nutrition_info": [
                    "Nutrition Info"
                ],
                "calendar": [
                    "Calendar"
                ],
                "uber": [
                    "Uber"
                ],
                "calculator": [
                    "Calculator"
                ],
                "date": [
                    "Date"
                ],
                "carry_on": [
                    "Carry On"
                ],
                "pto_used": [
                    "Pto Used"
                ],
                "schedule_maintenance": [
                    "Schedule Maintenance"
                ],
                "travel_notification": [
                    "Travel Notification"
                ],
                "sync_device": [
                    "Sync Device"
                ],
                "thank_you": [
                    "Thank You"
                ],
                "roll_dice": [
                    "Roll Dice"
                ],
                "food_last": [
                    "Food Last"
                ],
                "cook_time": [
                    "Cook Time"
                ],
                "reminder_update": [
                    "Reminder Update"
                ],
                "report_lost_card": [
                    "Report Lost Card"
                ],
                "ingredient_substitution": [
                    "Ingredient Substitution"
                ],
                "make_call": [
                    "Make Call"
                ],
                "alarm": [
                    "Alarm"
                ],
                "todo_list": [
                    "Todo List"
                ],
                "change_accent": [
                    "Change Accent"
                ],
                "w2": [
                    "W2"
                ],
                "bill_due": [
                    "Bill Due"
                ],
                "calories": [
                    "Calories"
                ],
                "damaged_card": [
                    "Damaged Card"
                ],
                "restaurant_reviews": [
                    "Restaurant Reviews"
                ],
                "routing": [
                    "Routing"
                ],
                "do_you_have_pets": [
                    "Do You Have Pets"
                ],
                "schedule_meeting": [
                    "Schedule Meeting"
                ],
                "gas_type": [
                    "Gas Type"
                ],
                "plug_type": [
                    "Plug Type"
                ],
                "tire_change": [
                    "Tire Change"
                ],
                "exchange_rate": [
                    "Exchange Rate"
                ],
                "next_holiday": [
                    "Next Holiday"
                ],
                "change_volume": [
                    "Change Volume"
                ],
                "who_do_you_work_for": [
                    "Who Do You Work For"
                ],
                "credit_limit": [
                    "Credit Limit"
                ],
                "how_busy": [
                    "How Busy"
                ],
                "accept_reservations": [
                    "Accept Reservations"
                ],
                "order_status": [
                    "Order Status"
                ],
                "pin_change": [
                    "Pin Change"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "account_blocked": [
                    "Account Blocked"
                ],
                "what_song": [
                    "What Song"
                ],
                "international_fees": [
                    "International Fees"
                ],
                "last_maintenance": [
                    "Last Maintenance"
                ],
                "meeting_schedule": [
                    "Meeting Schedule"
                ],
                "ingredients_list": [
                    "Ingredients List"
                ],
                "report_fraud": [
                    "Report Fraud"
                ],
                "measurement_conversion": [
                    "Measurement Conversion"
                ],
                "smart_home": [
                    "Smart Home"
                ],
                "book_hotel": [
                    "Book Hotel"
                ],
                "current_location": [
                    "Current Location"
                ],
                "weather": [
                    "Weather"
                ],
                "taxes": [
                    "Taxes"
                ],
                "min_payment": [
                    "Min Payment"
                ],
                "whisper_mode": [
                    "Whisper Mode"
                ],
                "cancel": [
                    "Cancel"
                ],
                "international_visa": [
                    "International Visa"
                ],
                "vaccines": [
                    "Vaccines"
                ],
                "pto_balance": [
                    "Pto Balance"
                ],
                "directions": [
                    "Directions"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "Reset Settings"
                ],
                "what_is_your_name": [
                    "What Is Your Name"
                ],
                "direct_deposit": [
                    "Direct Deposit"
                ],
                "interest_rate": [
                    "Interest Rate"
                ],
                "credit_limit_change": [
                    "Credit Limit Change"
                ],
                "what_are_your_hobbies": [
                    "What Are Your Hobbies"
                ],
                "book_flight": [
                    "Book Flight"
                ],
                "shopping_list": [
                    "Shopping List"
                ],
                "text": [
                    "Text"
                ],
                "bill_balance": [
                    "Bill Balance"
                ],
                "share_location": [
                    "Share Location"
                ],
                "redeem_rewards": [
                    "Redeem Rewards"
                ],
                "play_music": [
                    "Play Music"
                ],
                "calendar_update": [
                    "Calendar Update"
                ],
                "are_you_a_bot": [
                    "Are You A Bot"
                ],
                "gas": [
                    "Gas"
                ],
                "expiration_date": [
                    "Expiration Date"
                ],
                "update_playlist": [
                    "Update Playlist"
                ],
                "cancel_reservation": [
                    "Cancel Reservation"
                ],
                "tell_joke": [
                    "Tell Joke"
                ],
                "change_ai_name": [
                    "Change Ai Name"
                ],
                "how_old_are_you": [
                    "How Old Are You"
                ],
                "car_rental": [
                    "Car Rental"
                ],
                "jump_start": [
                    "Jump Start"
                ],
                "meal_suggestion": [
                    "Meal Suggestion"
                ],
                "recipe": [
                    "Recipe"
                ],
                "income": [
                    "Income"
                ],
                "order": [
                    "Order"
                ],
                "traffic": [
                    "Traffic"
                ],
                "order_checks": [
                    "Order Checks"
                ],
                "card_declined": [
                    "Card Declined"
                ]
            },
            "version_3": {
                "translate": [
                    "Translate"
                ],
                "transfer": [
                    "Transfer"
                ],
                "timer": [
                    "Timer"
                ],
                "definition": [
                    "Definition"
                ],
                "meaning_of_life": [
                    "MeaningOfLife"
                ],
                "insurance_change": [
                    "InsuranceChange"
                ],
                "find_phone": [
                    "FindPhone"
                ],
                "travel_alert": [
                    "TravelAlert"
                ],
                "pto_request": [
                    "PtoRequest"
                ],
                "improve_credit_score": [
                    "ImproveCreditScore"
                ],
                "fun_fact": [
                    "FunFact"
                ],
                "change_language": [
                    "ChangeLanguage"
                ],
                "payday": [
                    "Payday"
                ],
                "replacement_card_duration": [
                    "ReplacementCardDuration"
                ],
                "time": [
                    "Time"
                ],
                "application_status": [
                    "ApplicationStatus"
                ],
                "flight_status": [
                    "FlightStatus"
                ],
                "flip_coin": [
                    "FlipCoin"
                ],
                "change_user_name": [
                    "ChangeUserName"
                ],
                "where_are_you_from": [
                    "WhereAreYouFrom"
                ],
                "shopping_list_update": [
                    "ShoppingListUpdate"
                ],
                "what_can_i_ask_you": [
                    "WhatCanIAskYou"
                ],
                "maybe": [
                    "Maybe"
                ],
                "oil_change_how": [
                    "OilChangeHow"
                ],
                "restaurant_reservation": [
                    "RestaurantReservation"
                ],
                "balance": [
                    "Balance"
                ],
                "confirm_reservation": [
                    "ConfirmReservation"
                ],
                "freeze_account": [
                    "FreezeAccount"
                ],
                "rollover_401k": [
                    "Rollover401k"
                ],
                "who_made_you": [
                    "WhoMadeYou"
                ],
                "distance": [
                    "Distance"
                ],
                "user_name": [
                    "UserName"
                ],
                "timezone": [
                    "Timezone"
                ],
                "next_song": [
                    "NextSong"
                ],
                "transactions": [
                    "Transactions"
                ],
                "restaurant_suggestion": [
                    "RestaurantSuggestion"
                ],
                "rewards_balance": [
                    "RewardsBalance"
                ],
                "pay_bill": [
                    "PayBill"
                ],
                "spending_history": [
                    "SpendingHistory"
                ],
                "pto_request_status": [
                    "PtoRequestStatus"
                ],
                "credit_score": [
                    "CreditScore"
                ],
                "new_card": [
                    "NewCard"
                ],
                "lost_luggage": [
                    "LostLuggage"
                ],
                "repeat": [
                    "Repeat"
                ],
                "mpg": [
                    "Mpg"
                ],
                "oil_change_when": [
                    "OilChangeWhen"
                ],
                "yes": [
                    "Yes"
                ],
                "travel_suggestion": [
                    "TravelSuggestion"
                ],
                "insurance": [
                    "Insurance"
                ],
                "todo_list_update": [
                    "TodoListUpdate"
                ],
                "reminder": [
                    "Reminder"
                ],
                "change_speed": [
                    "ChangeSpeed"
                ],
                "tire_pressure": [
                    "TirePressure"
                ],
                "no": [
                    "No"
                ],
                "apr": [
                    "Apr"
                ],
                "nutrition_info": [
                    "NutritionInfo"
                ],
                "calendar": [
                    "Calendar"
                ],
                "uber": [
                    "Uber"
                ],
                "calculator": [
                    "Calculator"
                ],
                "date": [
                    "Date"
                ],
                "carry_on": [
                    "CarryOn"
                ],
                "pto_used": [
                    "PtoUsed"
                ],
                "schedule_maintenance": [
                    "ScheduleMaintenance"
                ],
                "travel_notification": [
                    "TravelNotification"
                ],
                "sync_device": [
                    "SyncDevice"
                ],
                "thank_you": [
                    "ThankYou"
                ],
                "roll_dice": [
                    "RollDice"
                ],
                "food_last": [
                    "FoodLast"
                ],
                "cook_time": [
                    "CookTime"
                ],
                "reminder_update": [
                    "ReminderUpdate"
                ],
                "report_lost_card": [
                    "ReportLostCard"
                ],
                "ingredient_substitution": [
                    "IngredientSubstitution"
                ],
                "make_call": [
                    "MakeCall"
                ],
                "alarm": [
                    "Alarm"
                ],
                "todo_list": [
                    "TodoList"
                ],
                "change_accent": [
                    "ChangeAccent"
                ],
                "w2": [
                    "W2"
                ],
                "bill_due": [
                    "BillDue"
                ],
                "calories": [
                    "Calories"
                ],
                "damaged_card": [
                    "DamagedCard"
                ],
                "restaurant_reviews": [
                    "RestaurantReviews"
                ],
                "routing": [
                    "Routing"
                ],
                "do_you_have_pets": [
                    "DoYouHavePets"
                ],
                "schedule_meeting": [
                    "ScheduleMeeting"
                ],
                "gas_type": [
                    "GasType"
                ],
                "plug_type": [
                    "PlugType"
                ],
                "tire_change": [
                    "TireChange"
                ],
                "exchange_rate": [
                    "ExchangeRate"
                ],
                "next_holiday": [
                    "NextHoliday"
                ],
                "change_volume": [
                    "ChangeVolume"
                ],
                "who_do_you_work_for": [
                    "WhoDoYouWorkFor"
                ],
                "credit_limit": [
                    "CreditLimit"
                ],
                "how_busy": [
                    "HowBusy"
                ],
                "accept_reservations": [
                    "AcceptReservations"
                ],
                "order_status": [
                    "OrderStatus"
                ],
                "pin_change": [
                    "PinChange"
                ],
                "goodbye": [
                    "Goodbye"
                ],
                "account_blocked": [
                    "AccountBlocked"
                ],
                "what_song": [
                    "WhatSong"
                ],
                "international_fees": [
                    "InternationalFees"
                ],
                "last_maintenance": [
                    "LastMaintenance"
                ],
                "meeting_schedule": [
                    "MeetingSchedule"
                ],
                "ingredients_list": [
                    "IngredientsList"
                ],
                "report_fraud": [
                    "ReportFraud"
                ],
                "measurement_conversion": [
                    "MeasurementConversion"
                ],
                "smart_home": [
                    "SmartHome"
                ],
                "book_hotel": [
                    "BookHotel"
                ],
                "current_location": [
                    "CurrentLocation"
                ],
                "weather": [
                    "Weather"
                ],
                "taxes": [
                    "Taxes"
                ],
                "min_payment": [
                    "MinPayment"
                ],
                "whisper_mode": [
                    "WhisperMode"
                ],
                "cancel": [
                    "Cancel"
                ],
                "international_visa": [
                    "InternationalVisa"
                ],
                "vaccines": [
                    "Vaccines"
                ],
                "pto_balance": [
                    "PtoBalance"
                ],
                "directions": [
                    "Directions"
                ],
                "spelling": [
                    "Spelling"
                ],
                "greeting": [
                    "Greeting"
                ],
                "reset_settings": [
                    "ResetSettings"
                ],
                "what_is_your_name": [
                    "WhatIsYourName"
                ],
                "direct_deposit": [
                    "DirectDeposit"
                ],
                "interest_rate": [
                    "InterestRate"
                ],
                "credit_limit_change": [
                    "CreditLimitChange"
                ],
                "what_are_your_hobbies": [
                    "WhatAreYourHobbies"
                ],
                "book_flight": [
                    "BookFlight"
                ],
                "shopping_list": [
                    "ShoppingList"
                ],
                "text": [
                    "Text"
                ],
                "bill_balance": [
                    "BillBalance"
                ],
                "share_location": [
                    "ShareLocation"
                ],
                "redeem_rewards": [
                    "RedeemRewards"
                ],
                "play_music": [
                    "PlayMusic"
                ],
                "calendar_update": [
                    "CalendarUpdate"
                ],
                "are_you_a_bot": [
                    "AreYouABot"
                ],
                "gas": [
                    "Gas"
                ],
                "expiration_date": [
                    "ExpirationDate"
                ],
                "update_playlist": [
                    "UpdatePlaylist"
                ],
                "cancel_reservation": [
                    "CancelReservation"
                ],
                "tell_joke": [
                    "TellJoke"
                ],
                "change_ai_name": [
                    "ChangeAiName"
                ],
                "how_old_are_you": [
                    "HowOldAreYou"
                ],
                "car_rental": [
                    "CarRental"
                ],
                "jump_start": [
                    "JumpStart"
                ],
                "meal_suggestion": [
                    "MealSuggestion"
                ],
                "recipe": [
                    "Recipe"
                ],
                "income": [
                    "Income"
                ],
                "order": [
                    "Order"
                ],
                "traffic": [
                    "Traffic"
                ],
                "order_checks": [
                    "OrderChecks"
                ],
                "card_declined": [
                    "CardDeclined"
                ]
            },
            "version_4": {
                "translate": [
                    "TRANSLATE"
                ],
                "transfer": [
                    "TRANSFER"
                ],
                "timer": [
                    "TIMER"
                ],
                "definition": [
                    "DEFINITION"
                ],
                "meaning_of_life": [
                    "MEANING_OF_LIFE"
                ],
                "insurance_change": [
                    "INSURANCE_CHANGE"
                ],
                "find_phone": [
                    "FIND_PHONE"
                ],
                "travel_alert": [
                    "TRAVEL_ALERT"
                ],
                "pto_request": [
                    "PTO_REQUEST"
                ],
                "improve_credit_score": [
                    "IMPROVE_CREDIT_SCORE"
                ],
                "fun_fact": [
                    "FUN_FACT"
                ],
                "change_language": [
                    "CHANGE_LANGUAGE"
                ],
                "payday": [
                    "PAYDAY"
                ],
                "replacement_card_duration": [
                    "REPLACEMENT_CARD_DURATION"
                ],
                "time": [
                    "TIME"
                ],
                "application_status": [
                    "APPLICATION_STATUS"
                ],
                "flight_status": [
                    "FLIGHT_STATUS"
                ],
                "flip_coin": [
                    "FLIP_COIN"
                ],
                "change_user_name": [
                    "CHANGE_USER_NAME"
                ],
                "where_are_you_from": [
                    "WHERE_ARE_YOU_FROM"
                ],
                "shopping_list_update": [
                    "SHOPPING_LIST_UPDATE"
                ],
                "what_can_i_ask_you": [
                    "WHAT_CAN_I_ASK_YOU"
                ],
                "maybe": [
                    "MAYBE"
                ],
                "oil_change_how": [
                    "OIL_CHANGE_HOW"
                ],
                "restaurant_reservation": [
                    "RESTAURANT_RESERVATION"
                ],
                "balance": [
                    "BALANCE"
                ],
                "confirm_reservation": [
                    "CONFIRM_RESERVATION"
                ],
                "freeze_account": [
                    "FREEZE_ACCOUNT"
                ],
                "rollover_401k": [
                    "ROLLOVER_401K"
                ],
                "who_made_you": [
                    "WHO_MADE_YOU"
                ],
                "distance": [
                    "DISTANCE"
                ],
                "user_name": [
                    "USER_NAME"
                ],
                "timezone": [
                    "TIMEZONE"
                ],
                "next_song": [
                    "NEXT_SONG"
                ],
                "transactions": [
                    "TRANSACTIONS"
                ],
                "restaurant_suggestion": [
                    "RESTAURANT_SUGGESTION"
                ],
                "rewards_balance": [
                    "REWARDS_BALANCE"
                ],
                "pay_bill": [
                    "PAY_BILL"
                ],
                "spending_history": [
                    "SPENDING_HISTORY"
                ],
                "pto_request_status": [
                    "PTO_REQUEST_STATUS"
                ],
                "credit_score": [
                    "CREDIT_SCORE"
                ],
                "new_card": [
                    "NEW_CARD"
                ],
                "lost_luggage": [
                    "LOST_LUGGAGE"
                ],
                "repeat": [
                    "REPEAT"
                ],
                "mpg": [
                    "MPG"
                ],
                "oil_change_when": [
                    "OIL_CHANGE_WHEN"
                ],
                "yes": [
                    "YES"
                ],
                "travel_suggestion": [
                    "TRAVEL_SUGGESTION"
                ],
                "insurance": [
                    "INSURANCE"
                ],
                "todo_list_update": [
                    "TODO_LIST_UPDATE"
                ],
                "reminder": [
                    "REMINDER"
                ],
                "change_speed": [
                    "CHANGE_SPEED"
                ],
                "tire_pressure": [
                    "TIRE_PRESSURE"
                ],
                "no": [
                    "NO"
                ],
                "apr": [
                    "APR"
                ],
                "nutrition_info": [
                    "NUTRITION_INFO"
                ],
                "calendar": [
                    "CALENDAR"
                ],
                "uber": [
                    "UBER"
                ],
                "calculator": [
                    "CALCULATOR"
                ],
                "date": [
                    "DATE"
                ],
                "carry_on": [
                    "CARRY_ON"
                ],
                "pto_used": [
                    "PTO_USED"
                ],
                "schedule_maintenance": [
                    "SCHEDULE_MAINTENANCE"
                ],
                "travel_notification": [
                    "TRAVEL_NOTIFICATION"
                ],
                "sync_device": [
                    "SYNC_DEVICE"
                ],
                "thank_you": [
                    "THANK_YOU"
                ],
                "roll_dice": [
                    "ROLL_DICE"
                ],
                "food_last": [
                    "FOOD_LAST"
                ],
                "cook_time": [
                    "COOK_TIME"
                ],
                "reminder_update": [
                    "REMINDER_UPDATE"
                ],
                "report_lost_card": [
                    "REPORT_LOST_CARD"
                ],
                "ingredient_substitution": [
                    "INGREDIENT_SUBSTITUTION"
                ],
                "make_call": [
                    "MAKE_CALL"
                ],
                "alarm": [
                    "ALARM"
                ],
                "todo_list": [
                    "TODO_LIST"
                ],
                "change_accent": [
                    "CHANGE_ACCENT"
                ],
                "w2": [
                    "W2"
                ],
                "bill_due": [
                    "BILL_DUE"
                ],
                "calories": [
                    "CALORIES"
                ],
                "damaged_card": [
                    "DAMAGED_CARD"
                ],
                "restaurant_reviews": [
                    "RESTAURANT_REVIEWS"
                ],
                "routing": [
                    "ROUTING"
                ],
                "do_you_have_pets": [
                    "DO_YOU_HAVE_PETS"
                ],
                "schedule_meeting": [
                    "SCHEDULE_MEETING"
                ],
                "gas_type": [
                    "GAS_TYPE"
                ],
                "plug_type": [
                    "PLUG_TYPE"
                ],
                "tire_change": [
                    "TIRE_CHANGE"
                ],
                "exchange_rate": [
                    "EXCHANGE_RATE"
                ],
                "next_holiday": [
                    "NEXT_HOLIDAY"
                ],
                "change_volume": [
                    "CHANGE_VOLUME"
                ],
                "who_do_you_work_for": [
                    "WHO_DO_YOU_WORK_FOR"
                ],
                "credit_limit": [
                    "CREDIT_LIMIT"
                ],
                "how_busy": [
                    "HOW_BUSY"
                ],
                "accept_reservations": [
                    "ACCEPT_RESERVATIONS"
                ],
                "order_status": [
                    "ORDER_STATUS"
                ],
                "pin_change": [
                    "PIN_CHANGE"
                ],
                "goodbye": [
                    "GOODBYE"
                ],
                "account_blocked": [
                    "ACCOUNT_BLOCKED"
                ],
                "what_song": [
                    "WHAT_SONG"
                ],
                "international_fees": [
                    "INTERNATIONAL_FEES"
                ],
                "last_maintenance": [
                    "LAST_MAINTENANCE"
                ],
                "meeting_schedule": [
                    "MEETING_SCHEDULE"
                ],
                "ingredients_list": [
                    "INGREDIENTS_LIST"
                ],
                "report_fraud": [
                    "REPORT_FRAUD"
                ],
                "measurement_conversion": [
                    "MEASUREMENT_CONVERSION"
                ],
                "smart_home": [
                    "SMART_HOME"
                ],
                "book_hotel": [
                    "BOOK_HOTEL"
                ],
                "current_location": [
                    "CURRENT_LOCATION"
                ],
                "weather": [
                    "WEATHER"
                ],
                "taxes": [
                    "TAXES"
                ],
                "min_payment": [
                    "MIN_PAYMENT"
                ],
                "whisper_mode": [
                    "WHISPER_MODE"
                ],
                "cancel": [
                    "CANCEL"
                ],
                "international_visa": [
                    "INTERNATIONAL_VISA"
                ],
                "vaccines": [
                    "VACCINES"
                ],
                "pto_balance": [
                    "PTO_BALANCE"
                ],
                "directions": [
                    "DIRECTIONS"
                ],
                "spelling": [
                    "SPELLING"
                ],
                "greeting": [
                    "GREETING"
                ],
                "reset_settings": [
                    "RESET_SETTINGS"
                ],
                "what_is_your_name": [
                    "WHAT_IS_YOUR_NAME"
                ],
                "direct_deposit": [
                    "DIRECT_DEPOSIT"
                ],
                "interest_rate": [
                    "INTEREST_RATE"
                ],
                "credit_limit_change": [
                    "CREDIT_LIMIT_CHANGE"
                ],
                "what_are_your_hobbies": [
                    "WHAT_ARE_YOUR_HOBBIES"
                ],
                "book_flight": [
                    "BOOK_FLIGHT"
                ],
                "shopping_list": [
                    "SHOPPING_LIST"
                ],
                "text": [
                    "TEXT"
                ],
                "bill_balance": [
                    "BILL_BALANCE"
                ],
                "share_location": [
                    "SHARE_LOCATION"
                ],
                "redeem_rewards": [
                    "REDEEM_REWARDS"
                ],
                "play_music": [
                    "PLAY_MUSIC"
                ],
                "calendar_update": [
                    "CALENDAR_UPDATE"
                ],
                "are_you_a_bot": [
                    "ARE_YOU_A_BOT"
                ],
                "gas": [
                    "GAS"
                ],
                "expiration_date": [
                    "EXPIRATION_DATE"
                ],
                "update_playlist": [
                    "UPDATE_PLAYLIST"
                ],
                "cancel_reservation": [
                    "CANCEL_RESERVATION"
                ],
                "tell_joke": [
                    "TELL_JOKE"
                ],
                "change_ai_name": [
                    "CHANGE_AI_NAME"
                ],
                "how_old_are_you": [
                    "HOW_OLD_ARE_YOU"
                ],
                "car_rental": [
                    "CAR_RENTAL"
                ],
                "jump_start": [
                    "JUMP_START"
                ],
                "meal_suggestion": [
                    "MEAL_SUGGESTION"
                ],
                "recipe": [
                    "RECIPE"
                ],
                "income": [
                    "INCOME"
                ],
                "order": [
                    "ORDER"
                ],
                "traffic": [
                    "TRAFFIC"
                ],
                "order_checks": [
                    "ORDER_CHECKS"
                ],
                "card_declined": [
                    "CARD_DECLINED"
                ]
            }
        },
        "ri_sawoz_domain": {
            "version_0": {
                "旅游景点": ["旅游景点", "景点"],
                "通用": ["通用"],
                "餐厅": ["餐厅"],
                "酒店": ["酒店"],
                "火车": ["火车"],
                "飞机": ["飞机"],
                "天气": ["天气"],
                "电影": ["电影"],
                "电视剧": ["电视剧"],
                "医院": ["医院"],
                "电脑": ["电脑"],
                "汽车": ["汽车"],
                "辅导班": ["辅导班"],

            },
        },
        "ri_sawoz_general": {
            "version_0": {
                "Bye": ["bye"],
                "Greeting": ["greet", "greeting"],
            },
            "version_1": {
                "Bye": ["Bye", "Bye bye"],
                "Greeting": ["Greet", "Greeting"],
            },
        },
        "small_talk": {
            "version_0": {
                "agent_acquaintance": [
                    "agent_acquaintance"
                ],
                "agent_age": [
                    "agent_age"
                ],
                "agent_annoying": [
                    "agent_annoying"
                ],
                "agent_answer_my_question": [
                    "agent_answer_my_question"
                ],
                "agent_bad": [
                    "agent_bad"
                ],
                "agent_be_clever": [
                    "agent_be_clever"
                ],
                "agent_beautiful": [
                    "agent_beautiful"
                ],
                "agent_birth_date": [
                    "agent_birth_date"
                ],
                "agent_boring": [
                    "agent_boring"
                ],
                "agent_boss": [
                    "agent_boss"
                ],
                "agent_busy": [
                    "agent_busy"
                ],
                "agent_chatbot": [
                    "agent_chatbot"
                ],
                "agent_clever": [
                    "agent_clever"
                ],
                "agent_crazy": [
                    "agent_crazy"
                ],
                "agent_fired": [
                    "agent_fired"
                ],
                "agent_funny": [
                    "agent_funny"
                ],
                "agent_good": [
                    "agent_good"
                ],
                "agent_happy": [
                    "agent_happy"
                ],
                "agent_hungry": [
                    "agent_hungry"
                ],
                "agent_marry_user": [
                    "agent_marry_user"
                ],
                "agent_my_friend": [
                    "agent_my_friend"
                ],
                "agent_occupation": [
                    "agent_occupation"
                ],
                "agent_origin": [
                    "agent_origin"
                ],
                "agent_ready": [
                    "agent_ready"
                ],
                "agent_real": [
                    "agent_real"
                ],
                "agent_residence": [
                    "agent_residence"
                ],
                "agent_right": [
                    "agent_right"
                ],
                "confirmation_yes": [
                    "confirmation_yes"
                ],
                "agent_sure": [
                    "agent_sure"
                ],
                "agent_talk_to_me": [
                    "agent_talk_to_me"
                ],
                "agent_there": [
                    "agent_there"
                ],
                "appraisal_bad": [
                    "appraisal_bad"
                ],
                "appraisal_good": [
                    "appraisal_good"
                ],
                "appraisal_no_problem": [
                    "appraisal_no_problem"
                ],
                "appraisal_thank_you": [
                    "appraisal_thank_you"
                ],
                "appraisal_welcome": [
                    "appraisal_welcome"
                ],
                "appraisal_well_done": [
                    "appraisal_well_done"
                ],
                "confirmation_cancel": [
                    "confirmation_cancel"
                ],
                "confirmation_no": [
                    "confirmation_no"
                ],
                "dialog_hold_on": [
                    "dialog_hold_on"
                ],
                "dialog_hug": [
                    "dialog_hug"
                ],
                "dialog_i_do_not_care": [
                    "dialog_i_do_not_care"
                ],
                "dialog_sorry": [
                    "dialog_sorry"
                ],
                "dialog_what_do_you_mean": [
                    "dialog_what_do_you_mean"
                ],
                "dialog_wrong": [
                    "dialog_wrong"
                ],
                "emotions_ha_ha": [
                    "emotions_ha_ha"
                ],
                "emotions_wow": [
                    "emotions_wow"
                ],
                "greetings_bye": [
                    "greetings_bye"
                ],
                "greetings_goodevening": [
                    "greetings_goodevening"
                ],
                "greetings_goodmorning": [
                    "greetings_goodmorning"
                ],
                "greetings_goodnight": [
                    "greetings_goodnight"
                ],
                "greetings_hello": [
                    "greetings_hello"
                ],
                "greetings_how_are_you": [
                    "greetings_how_are_you"
                ],
                "greetings_nice_to_meet_you": [
                    "greetings_nice_to_meet_you"
                ],
                "greetings_nice_to_see_you": [
                    "greetings_nice_to_see_you"
                ],
                "greetings_nice_to_talk_to_you": [
                    "greetings_nice_to_talk_to_you"
                ],
                "greetings_whatsup": [
                    "greetings_whatsup"
                ],
                "user_angry": [
                    "user_angry"
                ],
                "user_back": [
                    "user_back"
                ],
                "user_bored": [
                    "user_bored"
                ],
                "user_busy": [
                    "user_busy"
                ],
                "user_can_not_sleep": [
                    "user_can_not_sleep"
                ],
                "user_does_not_want_to_talk": [
                    "user_does_not_want_to_talk"
                ],
                "user_excited": [
                    "user_excited"
                ],
                "user_going_to_bed": [
                    "user_going_to_bed"
                ],
                "user_good": [
                    "user_good"
                ],
                "user_happy": [
                    "user_happy"
                ],
                "user_has_birthday": [
                    "user_has_birthday"
                ],
                "user_here": [
                    "user_here"
                ],
                "user_joking": [
                    "user_joking"
                ],
                "user_likes_agent": [
                    "user_likes_agent"
                ],
                "user_lonely": [
                    "user_lonely"
                ],
                "user_looks_like": [
                    "user_looks_like"
                ],
                "user_loves_agent": [
                    "user_loves_agent"
                ],
                "user_misses_agent": [
                    "user_misses_agent"
                ],
                "user_needs_advice": [
                    "user_needs_advice"
                ],
                "user_sad": [
                    "user_sad"
                ],
                "user_sleepy": [
                    "user_sleepy"
                ],
                "user_testing_agent": [
                    "user_testing_agent"
                ],
                "user_tired": [
                    "user_tired"
                ],
                "user_waits": [
                    "user_waits"
                ],
                "user_wants_to_see_agent_again": [
                    "user_wants_to_see_agent_again"
                ],
                "user_wants_to_talk": [
                    "user_wants_to_talk"
                ],
                "user_will_be_back": [
                    "user_will_be_back"
                ]
            },
            "version_1": {
                "agent_acquaintance": [
                    "agent acquaintance"
                ],
                "agent_age": [
                    "agent age"
                ],
                "agent_annoying": [
                    "agent annoying"
                ],
                "agent_answer_my_question": [
                    "agent answer my question"
                ],
                "agent_bad": [
                    "agent bad"
                ],
                "agent_be_clever": [
                    "agent be clever"
                ],
                "agent_beautiful": [
                    "agent beautiful"
                ],
                "agent_birth_date": [
                    "agent birth date"
                ],
                "agent_boring": [
                    "agent boring"
                ],
                "agent_boss": [
                    "agent boss"
                ],
                "agent_busy": [
                    "agent busy"
                ],
                "agent_chatbot": [
                    "agent chatbot"
                ],
                "agent_clever": [
                    "agent clever"
                ],
                "agent_crazy": [
                    "agent crazy"
                ],
                "agent_fired": [
                    "agent fired"
                ],
                "agent_funny": [
                    "agent funny"
                ],
                "agent_good": [
                    "agent good"
                ],
                "agent_happy": [
                    "agent happy"
                ],
                "agent_hungry": [
                    "agent hungry"
                ],
                "agent_marry_user": [
                    "agent marry user"
                ],
                "agent_my_friend": [
                    "agent my friend"
                ],
                "agent_occupation": [
                    "agent occupation"
                ],
                "agent_origin": [
                    "agent origin"
                ],
                "agent_ready": [
                    "agent ready"
                ],
                "agent_real": [
                    "agent real"
                ],
                "agent_residence": [
                    "agent residence"
                ],
                "agent_right": [
                    "agent right"
                ],
                "confirmation_yes": [
                    "confirmation yes"
                ],
                "agent_sure": [
                    "agent sure"
                ],
                "agent_talk_to_me": [
                    "agent talk to me"
                ],
                "agent_there": [
                    "agent there"
                ],
                "appraisal_bad": [
                    "appraisal bad"
                ],
                "appraisal_good": [
                    "appraisal good"
                ],
                "appraisal_no_problem": [
                    "appraisal no problem"
                ],
                "appraisal_thank_you": [
                    "appraisal thank you"
                ],
                "appraisal_welcome": [
                    "appraisal welcome"
                ],
                "appraisal_well_done": [
                    "appraisal well done"
                ],
                "confirmation_cancel": [
                    "confirmation cancel"
                ],
                "confirmation_no": [
                    "confirmation no"
                ],
                "dialog_hold_on": [
                    "dialog hold on"
                ],
                "dialog_hug": [
                    "dialog hug"
                ],
                "dialog_i_do_not_care": [
                    "dialog i do not care"
                ],
                "dialog_sorry": [
                    "dialog sorry"
                ],
                "dialog_what_do_you_mean": [
                    "dialog what do you mean"
                ],
                "dialog_wrong": [
                    "dialog wrong"
                ],
                "emotions_ha_ha": [
                    "emotions ha ha"
                ],
                "emotions_wow": [
                    "emotions wow"
                ],
                "greetings_bye": [
                    "greetings bye"
                ],
                "greetings_goodevening": [
                    "greetings goodevening"
                ],
                "greetings_goodmorning": [
                    "greetings goodmorning"
                ],
                "greetings_goodnight": [
                    "greetings goodnight"
                ],
                "greetings_hello": [
                    "greetings hello"
                ],
                "greetings_how_are_you": [
                    "greetings how are you"
                ],
                "greetings_nice_to_meet_you": [
                    "greetings nice to meet you"
                ],
                "greetings_nice_to_see_you": [
                    "greetings nice to see you"
                ],
                "greetings_nice_to_talk_to_you": [
                    "greetings nice to talk to you"
                ],
                "greetings_whatsup": [
                    "greetings whatsup"
                ],
                "user_angry": [
                    "user angry"
                ],
                "user_back": [
                    "user back"
                ],
                "user_bored": [
                    "user bored"
                ],
                "user_busy": [
                    "user busy"
                ],
                "user_can_not_sleep": [
                    "user can not sleep"
                ],
                "user_does_not_want_to_talk": [
                    "user does not want to talk"
                ],
                "user_excited": [
                    "user excited"
                ],
                "user_going_to_bed": [
                    "user going to bed"
                ],
                "user_good": [
                    "user good"
                ],
                "user_happy": [
                    "user happy"
                ],
                "user_has_birthday": [
                    "user has birthday"
                ],
                "user_here": [
                    "user here"
                ],
                "user_joking": [
                    "user joking"
                ],
                "user_likes_agent": [
                    "user likes agent"
                ],
                "user_lonely": [
                    "user lonely"
                ],
                "user_looks_like": [
                    "user looks like"
                ],
                "user_loves_agent": [
                    "user loves agent"
                ],
                "user_misses_agent": [
                    "user misses agent"
                ],
                "user_needs_advice": [
                    "user needs advice"
                ],
                "user_sad": [
                    "user sad"
                ],
                "user_sleepy": [
                    "user sleepy"
                ],
                "user_testing_agent": [
                    "user testing agent"
                ],
                "user_tired": [
                    "user tired"
                ],
                "user_waits": [
                    "user waits"
                ],
                "user_wants_to_see_agent_again": [
                    "user wants to see agent again"
                ],
                "user_wants_to_talk": [
                    "user wants to talk"
                ],
                "user_will_be_back": [
                    "user will be back"
                ]
            },
            "version_2": {
                "agent_acquaintance": [
                    "Agent Acquaintance"
                ],
                "agent_age": [
                    "Agent Age"
                ],
                "agent_annoying": [
                    "Agent Annoying"
                ],
                "agent_answer_my_question": [
                    "Agent Answer My Question"
                ],
                "agent_bad": [
                    "Agent Bad"
                ],
                "agent_be_clever": [
                    "Agent Be Clever"
                ],
                "agent_beautiful": [
                    "Agent Beautiful"
                ],
                "agent_birth_date": [
                    "Agent Birth Date"
                ],
                "agent_boring": [
                    "Agent Boring"
                ],
                "agent_boss": [
                    "Agent Boss"
                ],
                "agent_busy": [
                    "Agent Busy"
                ],
                "agent_chatbot": [
                    "Agent Chatbot"
                ],
                "agent_clever": [
                    "Agent Clever"
                ],
                "agent_crazy": [
                    "Agent Crazy"
                ],
                "agent_fired": [
                    "Agent Fired"
                ],
                "agent_funny": [
                    "Agent Funny"
                ],
                "agent_good": [
                    "Agent Good"
                ],
                "agent_happy": [
                    "Agent Happy"
                ],
                "agent_hungry": [
                    "Agent Hungry"
                ],
                "agent_marry_user": [
                    "Agent Marry User"
                ],
                "agent_my_friend": [
                    "Agent My Friend"
                ],
                "agent_occupation": [
                    "Agent Occupation"
                ],
                "agent_origin": [
                    "Agent Origin"
                ],
                "agent_ready": [
                    "Agent Ready"
                ],
                "agent_real": [
                    "Agent Real"
                ],
                "agent_residence": [
                    "Agent Residence"
                ],
                "agent_right": [
                    "Agent Right"
                ],
                "confirmation_yes": [
                    "Confirmation Yes"
                ],
                "agent_sure": [
                    "Agent Sure"
                ],
                "agent_talk_to_me": [
                    "Agent Talk To Me"
                ],
                "agent_there": [
                    "Agent There"
                ],
                "appraisal_bad": [
                    "Appraisal Bad"
                ],
                "appraisal_good": [
                    "Appraisal Good"
                ],
                "appraisal_no_problem": [
                    "Appraisal No Problem"
                ],
                "appraisal_thank_you": [
                    "Appraisal Thank You"
                ],
                "appraisal_welcome": [
                    "Appraisal Welcome"
                ],
                "appraisal_well_done": [
                    "Appraisal Well Done"
                ],
                "confirmation_cancel": [
                    "Confirmation Cancel"
                ],
                "confirmation_no": [
                    "Confirmation No"
                ],
                "dialog_hold_on": [
                    "Dialog Hold On"
                ],
                "dialog_hug": [
                    "Dialog Hug"
                ],
                "dialog_i_do_not_care": [
                    "Dialog I Do Not Care"
                ],
                "dialog_sorry": [
                    "Dialog Sorry"
                ],
                "dialog_what_do_you_mean": [
                    "Dialog What Do You Mean"
                ],
                "dialog_wrong": [
                    "Dialog Wrong"
                ],
                "emotions_ha_ha": [
                    "Emotions Ha Ha"
                ],
                "emotions_wow": [
                    "Emotions Wow"
                ],
                "greetings_bye": [
                    "Greetings Bye"
                ],
                "greetings_goodevening": [
                    "Greetings Goodevening"
                ],
                "greetings_goodmorning": [
                    "Greetings Goodmorning"
                ],
                "greetings_goodnight": [
                    "Greetings Goodnight"
                ],
                "greetings_hello": [
                    "Greetings Hello"
                ],
                "greetings_how_are_you": [
                    "Greetings How Are You"
                ],
                "greetings_nice_to_meet_you": [
                    "Greetings Nice To Meet You"
                ],
                "greetings_nice_to_see_you": [
                    "Greetings Nice To See You"
                ],
                "greetings_nice_to_talk_to_you": [
                    "Greetings Nice To Talk To You"
                ],
                "greetings_whatsup": [
                    "Greetings Whatsup"
                ],
                "user_angry": [
                    "User Angry"
                ],
                "user_back": [
                    "User Back"
                ],
                "user_bored": [
                    "User Bored"
                ],
                "user_busy": [
                    "User Busy"
                ],
                "user_can_not_sleep": [
                    "User Can Not Sleep"
                ],
                "user_does_not_want_to_talk": [
                    "User Does Not Want To Talk"
                ],
                "user_excited": [
                    "User Excited"
                ],
                "user_going_to_bed": [
                    "User Going To Bed"
                ],
                "user_good": [
                    "User Good"
                ],
                "user_happy": [
                    "User Happy"
                ],
                "user_has_birthday": [
                    "User Has Birthday"
                ],
                "user_here": [
                    "User Here"
                ],
                "user_joking": [
                    "User Joking"
                ],
                "user_likes_agent": [
                    "User Likes Agent"
                ],
                "user_lonely": [
                    "User Lonely"
                ],
                "user_looks_like": [
                    "User Looks Like"
                ],
                "user_loves_agent": [
                    "User Loves Agent"
                ],
                "user_misses_agent": [
                    "User Misses Agent"
                ],
                "user_needs_advice": [
                    "User Needs Advice"
                ],
                "user_sad": [
                    "User Sad"
                ],
                "user_sleepy": [
                    "User Sleepy"
                ],
                "user_testing_agent": [
                    "User Testing Agent"
                ],
                "user_tired": [
                    "User Tired"
                ],
                "user_waits": [
                    "User Waits"
                ],
                "user_wants_to_see_agent_again": [
                    "User Wants To See Agent Again"
                ],
                "user_wants_to_talk": [
                    "User Wants To Talk"
                ],
                "user_will_be_back": [
                    "User Will Be Back"
                ]
            },
            "version_3": {
                "agent_acquaintance": [
                    "AgentAcquaintance"
                ],
                "agent_age": [
                    "AgentAge"
                ],
                "agent_annoying": [
                    "AgentAnnoying"
                ],
                "agent_answer_my_question": [
                    "AgentAnswerMyQuestion"
                ],
                "agent_bad": [
                    "AgentBad"
                ],
                "agent_be_clever": [
                    "AgentBeClever"
                ],
                "agent_beautiful": [
                    "AgentBeautiful"
                ],
                "agent_birth_date": [
                    "AgentBirthDate"
                ],
                "agent_boring": [
                    "AgentBoring"
                ],
                "agent_boss": [
                    "AgentBoss"
                ],
                "agent_busy": [
                    "AgentBusy"
                ],
                "agent_chatbot": [
                    "AgentChatbot"
                ],
                "agent_clever": [
                    "AgentClever"
                ],
                "agent_crazy": [
                    "AgentCrazy"
                ],
                "agent_fired": [
                    "AgentFired"
                ],
                "agent_funny": [
                    "AgentFunny"
                ],
                "agent_good": [
                    "AgentGood"
                ],
                "agent_happy": [
                    "AgentHappy"
                ],
                "agent_hungry": [
                    "AgentHungry"
                ],
                "agent_marry_user": [
                    "AgentMarryUser"
                ],
                "agent_my_friend": [
                    "AgentMyFriend"
                ],
                "agent_occupation": [
                    "AgentOccupation"
                ],
                "agent_origin": [
                    "AgentOrigin"
                ],
                "agent_ready": [
                    "AgentReady"
                ],
                "agent_real": [
                    "AgentReal"
                ],
                "agent_residence": [
                    "AgentResidence"
                ],
                "agent_right": [
                    "AgentRight"
                ],
                "confirmation_yes": [
                    "ConfirmationYes"
                ],
                "agent_sure": [
                    "AgentSure"
                ],
                "agent_talk_to_me": [
                    "AgentTalkToMe"
                ],
                "agent_there": [
                    "AgentThere"
                ],
                "appraisal_bad": [
                    "AppraisalBad"
                ],
                "appraisal_good": [
                    "AppraisalGood"
                ],
                "appraisal_no_problem": [
                    "AppraisalNoProblem"
                ],
                "appraisal_thank_you": [
                    "AppraisalThankYou"
                ],
                "appraisal_welcome": [
                    "AppraisalWelcome"
                ],
                "appraisal_well_done": [
                    "AppraisalWellDone"
                ],
                "confirmation_cancel": [
                    "ConfirmationCancel"
                ],
                "confirmation_no": [
                    "ConfirmationNo"
                ],
                "dialog_hold_on": [
                    "DialogHoldOn"
                ],
                "dialog_hug": [
                    "DialogHug"
                ],
                "dialog_i_do_not_care": [
                    "DialogIDoNotCare"
                ],
                "dialog_sorry": [
                    "DialogSorry"
                ],
                "dialog_what_do_you_mean": [
                    "DialogWhatDoYouMean"
                ],
                "dialog_wrong": [
                    "DialogWrong"
                ],
                "emotions_ha_ha": [
                    "EmotionsHaHa"
                ],
                "emotions_wow": [
                    "EmotionsWow"
                ],
                "greetings_bye": [
                    "GreetingsBye"
                ],
                "greetings_goodevening": [
                    "GreetingsGoodevening"
                ],
                "greetings_goodmorning": [
                    "GreetingsGoodmorning"
                ],
                "greetings_goodnight": [
                    "GreetingsGoodnight"
                ],
                "greetings_hello": [
                    "GreetingsHello"
                ],
                "greetings_how_are_you": [
                    "GreetingsHowAreYou"
                ],
                "greetings_nice_to_meet_you": [
                    "GreetingsNiceToMeetYou"
                ],
                "greetings_nice_to_see_you": [
                    "GreetingsNiceToSeeYou"
                ],
                "greetings_nice_to_talk_to_you": [
                    "GreetingsNiceToTalkToYou"
                ],
                "greetings_whatsup": [
                    "GreetingsWhatsup"
                ],
                "user_angry": [
                    "UserAngry"
                ],
                "user_back": [
                    "UserBack"
                ],
                "user_bored": [
                    "UserBored"
                ],
                "user_busy": [
                    "UserBusy"
                ],
                "user_can_not_sleep": [
                    "UserCanNotSleep"
                ],
                "user_does_not_want_to_talk": [
                    "UserDoesNotWantToTalk"
                ],
                "user_excited": [
                    "UserExcited"
                ],
                "user_going_to_bed": [
                    "UserGoingToBed"
                ],
                "user_good": [
                    "UserGood"
                ],
                "user_happy": [
                    "UserHappy"
                ],
                "user_has_birthday": [
                    "UserHasBirthday"
                ],
                "user_here": [
                    "UserHere"
                ],
                "user_joking": [
                    "UserJoking"
                ],
                "user_likes_agent": [
                    "UserLikesAgent"
                ],
                "user_lonely": [
                    "UserLonely"
                ],
                "user_looks_like": [
                    "UserLooksLike"
                ],
                "user_loves_agent": [
                    "UserLovesAgent"
                ],
                "user_misses_agent": [
                    "UserMissesAgent"
                ],
                "user_needs_advice": [
                    "UserNeedsAdvice"
                ],
                "user_sad": [
                    "UserSad"
                ],
                "user_sleepy": [
                    "UserSleepy"
                ],
                "user_testing_agent": [
                    "UserTestingAgent"
                ],
                "user_tired": [
                    "UserTired"
                ],
                "user_waits": [
                    "UserWaits"
                ],
                "user_wants_to_see_agent_again": [
                    "UserWantsToSeeAgentAgain"
                ],
                "user_wants_to_talk": [
                    "UserWantsToTalk"
                ],
                "user_will_be_back": [
                    "UserWillBeBack"
                ]
            },
            "version_4": {
                "agent_acquaintance": [
                    "AGENT_ACQUAINTANCE"
                ],
                "agent_age": [
                    "AGENT_AGE"
                ],
                "agent_annoying": [
                    "AGENT_ANNOYING"
                ],
                "agent_answer_my_question": [
                    "AGENT_ANSWER_MY_QUESTION"
                ],
                "agent_bad": [
                    "AGENT_BAD"
                ],
                "agent_be_clever": [
                    "AGENT_BE_CLEVER"
                ],
                "agent_beautiful": [
                    "AGENT_BEAUTIFUL"
                ],
                "agent_birth_date": [
                    "AGENT_BIRTH_DATE"
                ],
                "agent_boring": [
                    "AGENT_BORING"
                ],
                "agent_boss": [
                    "AGENT_BOSS"
                ],
                "agent_busy": [
                    "AGENT_BUSY"
                ],
                "agent_chatbot": [
                    "AGENT_CHATBOT"
                ],
                "agent_clever": [
                    "AGENT_CLEVER"
                ],
                "agent_crazy": [
                    "AGENT_CRAZY"
                ],
                "agent_fired": [
                    "AGENT_FIRED"
                ],
                "agent_funny": [
                    "AGENT_FUNNY"
                ],
                "agent_good": [
                    "AGENT_GOOD"
                ],
                "agent_happy": [
                    "AGENT_HAPPY"
                ],
                "agent_hungry": [
                    "AGENT_HUNGRY"
                ],
                "agent_marry_user": [
                    "AGENT_MARRY_USER"
                ],
                "agent_my_friend": [
                    "AGENT_MY_FRIEND"
                ],
                "agent_occupation": [
                    "AGENT_OCCUPATION"
                ],
                "agent_origin": [
                    "AGENT_ORIGIN"
                ],
                "agent_ready": [
                    "AGENT_READY"
                ],
                "agent_real": [
                    "AGENT_REAL"
                ],
                "agent_residence": [
                    "AGENT_RESIDENCE"
                ],
                "agent_right": [
                    "AGENT_RIGHT"
                ],
                "confirmation_yes": [
                    "CONFIRMATION_YES"
                ],
                "agent_sure": [
                    "AGENT_SURE"
                ],
                "agent_talk_to_me": [
                    "AGENT_TALK_TO_ME"
                ],
                "agent_there": [
                    "AGENT_THERE"
                ],
                "appraisal_bad": [
                    "APPRAISAL_BAD"
                ],
                "appraisal_good": [
                    "APPRAISAL_GOOD"
                ],
                "appraisal_no_problem": [
                    "APPRAISAL_NO_PROBLEM"
                ],
                "appraisal_thank_you": [
                    "APPRAISAL_THANK_YOU"
                ],
                "appraisal_welcome": [
                    "APPRAISAL_WELCOME"
                ],
                "appraisal_well_done": [
                    "APPRAISAL_WELL_DONE"
                ],
                "confirmation_cancel": [
                    "CONFIRMATION_CANCEL"
                ],
                "confirmation_no": [
                    "CONFIRMATION_NO"
                ],
                "dialog_hold_on": [
                    "DIALOG_HOLD_ON"
                ],
                "dialog_hug": [
                    "DIALOG_HUG"
                ],
                "dialog_i_do_not_care": [
                    "DIALOG_I_DO_NOT_CARE"
                ],
                "dialog_sorry": [
                    "DIALOG_SORRY"
                ],
                "dialog_what_do_you_mean": [
                    "DIALOG_WHAT_DO_YOU_MEAN"
                ],
                "dialog_wrong": [
                    "DIALOG_WRONG"
                ],
                "emotions_ha_ha": [
                    "EMOTIONS_HA_HA"
                ],
                "emotions_wow": [
                    "EMOTIONS_WOW"
                ],
                "greetings_bye": [
                    "GREETINGS_BYE"
                ],
                "greetings_goodevening": [
                    "GREETINGS_GOODEVENING"
                ],
                "greetings_goodmorning": [
                    "GREETINGS_GOODMORNING"
                ],
                "greetings_goodnight": [
                    "GREETINGS_GOODNIGHT"
                ],
                "greetings_hello": [
                    "GREETINGS_HELLO"
                ],
                "greetings_how_are_you": [
                    "GREETINGS_HOW_ARE_YOU"
                ],
                "greetings_nice_to_meet_you": [
                    "GREETINGS_NICE_TO_MEET_YOU"
                ],
                "greetings_nice_to_see_you": [
                    "GREETINGS_NICE_TO_SEE_YOU"
                ],
                "greetings_nice_to_talk_to_you": [
                    "GREETINGS_NICE_TO_TALK_TO_YOU"
                ],
                "greetings_whatsup": [
                    "GREETINGS_WHATSUP"
                ],
                "user_angry": [
                    "USER_ANGRY"
                ],
                "user_back": [
                    "USER_BACK"
                ],
                "user_bored": [
                    "USER_BORED"
                ],
                "user_busy": [
                    "USER_BUSY"
                ],
                "user_can_not_sleep": [
                    "USER_CAN_NOT_SLEEP"
                ],
                "user_does_not_want_to_talk": [
                    "USER_DOES_NOT_WANT_TO_TALK"
                ],
                "user_excited": [
                    "USER_EXCITED"
                ],
                "user_going_to_bed": [
                    "USER_GOING_TO_BED"
                ],
                "user_good": [
                    "USER_GOOD"
                ],
                "user_happy": [
                    "USER_HAPPY"
                ],
                "user_has_birthday": [
                    "USER_HAS_BIRTHDAY"
                ],
                "user_here": [
                    "USER_HERE"
                ],
                "user_joking": [
                    "USER_JOKING"
                ],
                "user_likes_agent": [
                    "USER_LIKES_AGENT"
                ],
                "user_lonely": [
                    "USER_LONELY"
                ],
                "user_looks_like": [
                    "USER_LOOKS_LIKE"
                ],
                "user_loves_agent": [
                    "USER_LOVES_AGENT"
                ],
                "user_misses_agent": [
                    "USER_MISSES_AGENT"
                ],
                "user_needs_advice": [
                    "USER_NEEDS_ADVICE"
                ],
                "user_sad": [
                    "USER_SAD"
                ],
                "user_sleepy": [
                    "USER_SLEEPY"
                ],
                "user_testing_agent": [
                    "USER_TESTING_AGENT"
                ],
                "user_tired": [
                    "USER_TIRED"
                ],
                "user_waits": [
                    "USER_WAITS"
                ],
                "user_wants_to_see_agent_again": [
                    "USER_WANTS_TO_SEE_AGENT_AGAIN"
                ],
                "user_wants_to_talk": [
                    "USER_WANTS_TO_TALK"
                ],
                "user_will_be_back": [
                    "USER_WILL_BE_BACK"
                ]
            }
        },
        "smp2017_task1": {
            "version_0": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "calc": [
                    "calc"
                ],
                "chat": [
                    "chat"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "datetime": [
                    "datetime"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "map": [
                    "map"
                ],
                "match": [
                    "match"
                ],
                "message": [
                    "message"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "schedule": [
                    "schedule"
                ],
                "stock": [
                    "stock"
                ],
                "telephone": [
                    "telephone"
                ],
                "train": [
                    "train"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ]
            },
            "version_1": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "calc": [
                    "calc"
                ],
                "chat": [
                    "chat"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "datetime": [
                    "datetime"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "map": [
                    "map"
                ],
                "match": [
                    "match"
                ],
                "message": [
                    "message"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "schedule": [
                    "schedule"
                ],
                "stock": [
                    "stock"
                ],
                "telephone": [
                    "telephone"
                ],
                "train": [
                    "train"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ]
            },
            "version_2": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "calc": [
                    "Calc"
                ],
                "chat": [
                    "Chat"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "datetime": [
                    "Datetime"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "map": [
                    "Map"
                ],
                "match": [
                    "Match"
                ],
                "message": [
                    "Message"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "schedule": [
                    "Schedule"
                ],
                "stock": [
                    "Stock"
                ],
                "telephone": [
                    "Telephone"
                ],
                "train": [
                    "Train"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ]
            },
            "version_3": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "calc": [
                    "Calc"
                ],
                "chat": [
                    "Chat"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "datetime": [
                    "Datetime"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "map": [
                    "Map"
                ],
                "match": [
                    "Match"
                ],
                "message": [
                    "Message"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "schedule": [
                    "Schedule"
                ],
                "stock": [
                    "Stock"
                ],
                "telephone": [
                    "Telephone"
                ],
                "train": [
                    "Train"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ]
            },
            "version_4": {
                "app": [
                    "APP"
                ],
                "bus": [
                    "BUS"
                ],
                "calc": [
                    "CALC"
                ],
                "chat": [
                    "CHAT"
                ],
                "cinemas": [
                    "CINEMAS"
                ],
                "contacts": [
                    "CONTACTS"
                ],
                "cookbook": [
                    "COOKBOOK"
                ],
                "datetime": [
                    "DATETIME"
                ],
                "email": [
                    "EMAIL"
                ],
                "epg": [
                    "EPG"
                ],
                "flight": [
                    "FLIGHT"
                ],
                "health": [
                    "HEALTH"
                ],
                "lottery": [
                    "LOTTERY"
                ],
                "map": [
                    "MAP"
                ],
                "match": [
                    "MATCH"
                ],
                "message": [
                    "MESSAGE"
                ],
                "music": [
                    "MUSIC"
                ],
                "news": [
                    "NEWS"
                ],
                "novel": [
                    "NOVEL"
                ],
                "poetry": [
                    "POETRY"
                ],
                "radio": [
                    "RADIO"
                ],
                "riddle": [
                    "RIDDLE"
                ],
                "schedule": [
                    "SCHEDULE"
                ],
                "stock": [
                    "STOCK"
                ],
                "telephone": [
                    "TELEPHONE"
                ],
                "train": [
                    "TRAIN"
                ],
                "translation": [
                    "TRANSLATION"
                ],
                "tvchannel": [
                    "TVCHANNEL"
                ],
                "video": [
                    "VIDEO"
                ],
                "weather": [
                    "WEATHER"
                ],
                "website": [
                    "WEBSITE"
                ]
            }
        },
        "smp2019_task1_domain": {
            "version_0": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "map": [
                    "map"
                ],
                "train": [
                    "train"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "telephone": [
                    "telephone"
                ],
                "message": [
                    "message"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "match": [
                    "match"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "stock": [
                    "stock"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ],
                "joke": [
                    "joke"
                ],
                "story": [
                    "story"
                ]
            },
            "version_1": {
                "app": [
                    "app"
                ],
                "bus": [
                    "bus"
                ],
                "map": [
                    "map"
                ],
                "train": [
                    "train"
                ],
                "cinemas": [
                    "cinemas"
                ],
                "telephone": [
                    "telephone"
                ],
                "message": [
                    "message"
                ],
                "contacts": [
                    "contacts"
                ],
                "cookbook": [
                    "cookbook"
                ],
                "email": [
                    "email"
                ],
                "epg": [
                    "epg"
                ],
                "flight": [
                    "flight"
                ],
                "health": [
                    "health"
                ],
                "lottery": [
                    "lottery"
                ],
                "match": [
                    "match"
                ],
                "music": [
                    "music"
                ],
                "news": [
                    "news"
                ],
                "novel": [
                    "novel"
                ],
                "poetry": [
                    "poetry"
                ],
                "radio": [
                    "radio"
                ],
                "riddle": [
                    "riddle"
                ],
                "stock": [
                    "stock"
                ],
                "translation": [
                    "translation"
                ],
                "tvchannel": [
                    "tvchannel"
                ],
                "video": [
                    "video"
                ],
                "weather": [
                    "weather"
                ],
                "website": [
                    "website"
                ],
                "joke": [
                    "joke"
                ],
                "story": [
                    "story"
                ]
            },
            "version_2": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "map": [
                    "Map"
                ],
                "train": [
                    "Train"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "telephone": [
                    "Telephone"
                ],
                "message": [
                    "Message"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "match": [
                    "Match"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "stock": [
                    "Stock"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ],
                "joke": [
                    "Joke"
                ],
                "story": [
                    "Story"
                ]
            },
            "version_3": {
                "app": [
                    "App"
                ],
                "bus": [
                    "Bus"
                ],
                "map": [
                    "Map"
                ],
                "train": [
                    "Train"
                ],
                "cinemas": [
                    "Cinemas"
                ],
                "telephone": [
                    "Telephone"
                ],
                "message": [
                    "Message"
                ],
                "contacts": [
                    "Contacts"
                ],
                "cookbook": [
                    "Cookbook"
                ],
                "email": [
                    "Email"
                ],
                "epg": [
                    "Epg"
                ],
                "flight": [
                    "Flight"
                ],
                "health": [
                    "Health"
                ],
                "lottery": [
                    "Lottery"
                ],
                "match": [
                    "Match"
                ],
                "music": [
                    "Music"
                ],
                "news": [
                    "News"
                ],
                "novel": [
                    "Novel"
                ],
                "poetry": [
                    "Poetry"
                ],
                "radio": [
                    "Radio"
                ],
                "riddle": [
                    "Riddle"
                ],
                "stock": [
                    "Stock"
                ],
                "translation": [
                    "Translation"
                ],
                "tvchannel": [
                    "Tvchannel"
                ],
                "video": [
                    "Video"
                ],
                "weather": [
                    "Weather"
                ],
                "website": [
                    "Website"
                ],
                "joke": [
                    "Joke"
                ],
                "story": [
                    "Story"
                ]
            },
            "version_4": {
                "app": [
                    "APP"
                ],
                "bus": [
                    "BUS"
                ],
                "map": [
                    "MAP"
                ],
                "train": [
                    "TRAIN"
                ],
                "cinemas": [
                    "CINEMAS"
                ],
                "telephone": [
                    "TELEPHONE"
                ],
                "message": [
                    "MESSAGE"
                ],
                "contacts": [
                    "CONTACTS"
                ],
                "cookbook": [
                    "COOKBOOK"
                ],
                "email": [
                    "EMAIL"
                ],
                "epg": [
                    "EPG"
                ],
                "flight": [
                    "FLIGHT"
                ],
                "health": [
                    "HEALTH"
                ],
                "lottery": [
                    "LOTTERY"
                ],
                "match": [
                    "MATCH"
                ],
                "music": [
                    "MUSIC"
                ],
                "news": [
                    "NEWS"
                ],
                "novel": [
                    "NOVEL"
                ],
                "poetry": [
                    "POETRY"
                ],
                "radio": [
                    "RADIO"
                ],
                "riddle": [
                    "RIDDLE"
                ],
                "stock": [
                    "STOCK"
                ],
                "translation": [
                    "TRANSLATION"
                ],
                "tvchannel": [
                    "TVCHANNEL"
                ],
                "video": [
                    "VIDEO"
                ],
                "weather": [
                    "WEATHER"
                ],
                "website": [
                    "WEBSITE"
                ],
                "joke": [
                    "JOKE"
                ],
                "story": [
                    "STORY"
                ]
            }
        },
        "smp2019_task1_intent": {
            "version_0": {
                "launch": [
                    "launch"
                ],
                "query": [
                    "query"
                ],
                "route": [
                    "route"
                ],
                "sendcontacts": [
                    "send_contacts"
                ],
                "send": [
                    "send"
                ],
                "reply": [
                    "reply"
                ],
                "replay_all": [
                    "replay_all"
                ],
                "look_back": [
                    "look_back"
                ],
                "number_query": [
                    "number_query"
                ],
                "position": [
                    "position"
                ],
                "play": [
                    "play"
                ],
                "default": [
                    "default"
                ],
                "dial": [
                    "dial"
                ],
                "translation": [
                    "translation"
                ],
                "open": [
                    "open"
                ],
                "create": [
                    "create"
                ],
                "forward": [
                    "forward"
                ],
                "view": [
                    "view"
                ],
                "search": [
                    "search"
                ],
                "riserate_query": [
                    "riserate_query"
                ],
                "download": [
                    "download"
                ],
                "date_query": [
                    "date_query"
                ],
                "closeprice_query": [
                    "close_price_query"
                ]
            },
            "version_1": {
                "launch": [
                    "launch"
                ],
                "query": [
                    "query"
                ],
                "route": [
                    "route"
                ],
                "sendcontacts": [
                    "send contacts"
                ],
                "send": [
                    "send"
                ],
                "reply": [
                    "reply"
                ],
                "replay_all": [
                    "replay all"
                ],
                "look_back": [
                    "look back"
                ],
                "number_query": [
                    "number query"
                ],
                "position": [
                    "position"
                ],
                "play": [
                    "play"
                ],
                "default": [
                    "default"
                ],
                "dial": [
                    "dial"
                ],
                "translation": [
                    "translation"
                ],
                "open": [
                    "open"
                ],
                "create": [
                    "create"
                ],
                "forward": [
                    "forward"
                ],
                "view": [
                    "view"
                ],
                "search": [
                    "search"
                ],
                "riserate_query": [
                    "riserate query"
                ],
                "download": [
                    "download"
                ],
                "date_query": [
                    "date query"
                ],
                "closeprice_query": [
                    "close price query"
                ]
            },
            "version_2": {
                "launch": [
                    "Launch"
                ],
                "query": [
                    "Query"
                ],
                "route": [
                    "Route"
                ],
                "sendcontacts": [
                    "Send Contacts"
                ],
                "send": [
                    "Send"
                ],
                "reply": [
                    "Reply"
                ],
                "replay_all": [
                    "Replay All"
                ],
                "look_back": [
                    "Look Back"
                ],
                "number_query": [
                    "Number Query"
                ],
                "position": [
                    "Position"
                ],
                "play": [
                    "Play"
                ],
                "default": [
                    "Default"
                ],
                "dial": [
                    "Dial"
                ],
                "translation": [
                    "Translation"
                ],
                "open": [
                    "Open"
                ],
                "create": [
                    "Create"
                ],
                "forward": [
                    "Forward"
                ],
                "view": [
                    "View"
                ],
                "search": [
                    "Search"
                ],
                "riserate_query": [
                    "Riserate Query"
                ],
                "download": [
                    "Download"
                ],
                "date_query": [
                    "Date Query"
                ],
                "closeprice_query": [
                    "Close Price Query"
                ]
            },
            "version_3": {
                "launch": [
                    "Launch"
                ],
                "query": [
                    "Query"
                ],
                "route": [
                    "Route"
                ],
                "sendcontacts": [
                    "SendContacts"
                ],
                "send": [
                    "Send"
                ],
                "reply": [
                    "Reply"
                ],
                "replay_all": [
                    "ReplayAll"
                ],
                "look_back": [
                    "LookBack"
                ],
                "number_query": [
                    "NumberQuery"
                ],
                "position": [
                    "Position"
                ],
                "play": [
                    "Play"
                ],
                "default": [
                    "Default"
                ],
                "dial": [
                    "Dial"
                ],
                "translation": [
                    "Translation"
                ],
                "open": [
                    "Open"
                ],
                "create": [
                    "Create"
                ],
                "forward": [
                    "Forward"
                ],
                "view": [
                    "View"
                ],
                "search": [
                    "Search"
                ],
                "riserate_query": [
                    "RiserateQuery"
                ],
                "download": [
                    "Download"
                ],
                "date_query": [
                    "DateQuery"
                ],
                "closeprice_query": [
                    "ClosePriceQuery"
                ]
            },
            "version_4": {
                "launch": [
                    "LAUNCH"
                ],
                "query": [
                    "QUERY"
                ],
                "route": [
                    "ROUTE"
                ],
                "sendcontacts": [
                    "SEND_CONTACTS"
                ],
                "send": [
                    "SEND"
                ],
                "reply": [
                    "REPLY"
                ],
                "replay_all": [
                    "REPLAY_ALL"
                ],
                "look_back": [
                    "LOOK_BACK"
                ],
                "number_query": [
                    "NUMBER_QUERY"
                ],
                "position": [
                    "POSITION"
                ],
                "play": [
                    "PLAY"
                ],
                "default": [
                    "DEFAULT"
                ],
                "dial": [
                    "DIAL"
                ],
                "translation": [
                    "TRANSLATION"
                ],
                "open": [
                    "OPEN"
                ],
                "create": [
                    "CREATE"
                ],
                "forward": [
                    "FORWARD"
                ],
                "view": [
                    "VIEW"
                ],
                "search": [
                    "SEARCH"
                ],
                "riserate_query": [
                    "RISERATE_QUERY"
                ],
                "download": [
                    "DOWNLOAD"
                ],
                "date_query": [
                    "DATE_QUERY"
                ],
                "closeprice_query": [
                    "CLOSE_PRICE_QUERY"
                ]
            }
        },
        "snips_built_in_intents": {"version_0": {
            "ComparePlaces": [
                "ComparePlaces"
            ],
            "RequestRide": [
                "RequestRide"
            ],
            "GetWeather": [
                "GetWeather"
            ],
            "SearchPlace": [
                "SearchPlace"
            ],
            "GetPlaceDetails": [
                "GetPlaceDetails"
            ],
            "ShareCurrentLocation": [
                "ShareCurrentLocation"
            ],
            "GetTrafficInformation": [
                "GetTrafficInformation"
            ],
            "BookRestaurant": [
                "BookRestaurant"
            ],
            "GetDirections": [
                "GetDirections"
            ],
            "ShareETA": [
                "ShareETA"
            ]
        }},
        "star_wars": {
            "version_0": {
                "greeting": ["greeting"],
                "goodbye": ["goodbye"],
                "thanks": ["thanks"],
                "tasks": ["tasks"],
                "alive": ["alive"],
                "Menu": ["menu"],
                "hepl": ["help"],
                "mission": ["mission"],
                "jedi": ["jedi"],
                "sith": ["sith"],
                "bounti hounter": ["bounti hounter"],
                "funny": ["funny"],
                "about me": ["about me"],
                "creator": ["creator"],
                "myself": ["myself"],
                "stories": ["stories"],

            }
        },
        "suicide_intent": {
            "version_0": {
                "happy intent": [
                    "happy_intent"
                ],
                "sad intent": [
                    "sad_intent"
                ],
                "normal intent": [
                    "normal_intent"
                ],
                "suicidal intent": [
                    "suicidal_intent"
                ]
            },
            "version_1": {
                "happy intent": [
                    "happy intent"
                ],
                "sad intent": [
                    "sad intent"
                ],
                "normal intent": [
                    "normal intent"
                ],
                "suicidal intent": [
                    "suicidal intent"
                ]
            },
            "version_2": {
                "happy intent": [
                    "Happy Intent"
                ],
                "sad intent": [
                    "Sad Intent"
                ],
                "normal intent": [
                    "Normal Intent"
                ],
                "suicidal intent": [
                    "Suicidal Intent"
                ]
            },
            "version_3": {
                "happy intent": [
                    "HappyIntent"
                ],
                "sad intent": [
                    "SadIntent"
                ],
                "normal intent": [
                    "NormalIntent"
                ],
                "suicidal intent": [
                    "SuicidalIntent"
                ]
            },
            "version_4": {
                "happy intent": [
                    "HAPPY INTENT"
                ],
                "sad intent": [
                    "SAD INTENT"
                ],
                "normal intent": [
                    "NORMAL INTENT"
                ],
                "suicidal intent": [
                    "SUICIDAL INTENT"
                ]
            }
        },
        "telemarketing_intent_en": {"version_0": {
            "无关领域": ["outside the field", "out domain"],
            "肯定(yes)": ["yes"],
            "否定(not)": ["not"],
            "我在": ["I'm here", "I am listening", "I'm listening"],
            "实体(数值)": ["number", "contain number"],
            "答时间": ["contain data or time"],
            "听不清楚": ["I can not hear you"],
            "别担心": ["don't worry", "do not worry", "take it easy", "take easy"],
            "肯定(no problem)": ["no problem"],
            "资金困难": ["financial difficulties", "short money"],
            "招呼用语": ["greeting"],
            "肯定(go ahead)": ["go ahead"],
            "语音信箱": ["voicemail"],
            "否定(no)": ["no"],
            "查自我介绍": ["check self-introduction", "query self-introduction"],
            "会按时处理": ["will be processed on time", "will handle it"],
            "污言秽语": ["curse", "abuse", "vituperation", "snap", "damn"],
            "否定(dont want)": ["don't want", "don't wanna"],
            "赞美用语": ["praise", "laud"],
            "实体(人名)": ["name", "contain name", "contains names"],
            "否定(dont know)": ["don't know", "do not know"],
            "礼貌用语": ["polite", "polite words", "polite expressions"],
            "做自我介绍": ["introducing himself", "he is introducing himself"],
            "肯定(ok)": ["ok", "OK"],
            "否定(not interested)": ["not interested", "no interest"],
            "暴力敏感": ["violent", "contain violent"],
            "问意图": ["ask about intention", "ask about intent"],
            "答地址": ["address", "contain address"],
            "肯定(alright)": ["alright"],
            "肯定(sure)": ["sure"],
            "转账完成": ["transfer completed"],
            "查物品信息": ["check item information", "check item info", "check info"],
            "疑问(地址)": ["query address", "check address", "ask address"],
            "是否机器人": ["are you robot", "robot"],
            "投诉警告": ["complaint warning", "complaint"],
            "打错电话": ["wrong number", "called the wrong person", "mixed up the numbers"],
            "肯定(I see)": ["I see"],
            "语气词": ["modal particles", "interjection"],
            "要求复述": ["ask for a repeat", "can you speak again"],
            "不信任": ["distrust", "mistrust", "doubt", "suspect"],
            "未能理解": ["don't understand", "not understand", "not understood"],
            "价格太高": ["expensive", "price is too high"],
            "请等一等": ["please wait", "wait a minute"],
            "请求谅解": ["ask for understanding", "apologize", "make an apology", "excuse"],
            "疑问": ["inquiry"],
            "结束用语": ["farewell phrase", "closing phrase"],
            "肯定(interested)": ["interested"],
            "请讲": ["please speak"],
            "疑问(时间)": ["ask date or time", "ask time", "query date or time", "query time"],
            "疑问(姓名)": ["ask for name", "ask name", "query name"],
            "骚扰电话": ["harassing phone calls", "harassing", "bothering"],
            "肯定(agree)": ["agree"],
            "否定(not enough)": ["not enough"],
            "提出建议": ["make a suggestion"],
            "查详细信息": ["check details"],
            "肯定(yes I do)": ["yes I do"],
            "疑问(数值)": ["check number"],
            "考虑一下": ["think about it", "think twice"],
            "消极情绪": ["negative emotions"],
            "遭遇不幸": ["misfortune", "bad luck", "accident"],
            "用户正忙": ["busy"],
            "肯定(correct)": ["correct"],
            "号码来源": ["number source", "where did you get my number"],
            "许下愿望": ["make a wish"],
            "查收费方式": ["check the charging", "charging"],
            "肯定(need)": ["need"],
            "已经拥有": ["already have"],
            "疑问(whats up)": ["whats up"],
            "色情敏感": ["porn", "pornography", "obscene", "harlot"],
            "答状态": ["answered a status"],
            "已完成": ["finished"],
            "你还在吗": ["are you there"],
            "否定句": ["negative sentences"],
            "否定(not sure)": ["not sure"],
            "听我说话": ["listen to me"],
            "太多太高": ["too much or too high"],
            "祝福用语": ["phrases of blessing", "blessing phrases"],
            "疑问(金额)": ["how much"],
            "解释原因": ["explain the reason"],
            "否定(nothing)": ["nothing"],
            "鼓励用语": ["encouragement", "encourage"],
            "疑问(长度)": ["check length"],
            "加快速度": ["boost", "hurry up", "make haste"],
            "重复一次": ["repeat"],
            "肯定(i know)": ["I know"],
            "无所谓": ["It doesn't matter", "not to matter", "be indifferent"],
            "否定(not need)": ["not need"],
            "否定(cant)": ["can't", "can not"],
            "肯定(姓名)": ["confirm name"],
            "否定(refuse)": ["refuse"],
            "改天再谈": ["let's talk another day"],
            "肯定(understand)": ["understand", "do understand"],
            "太少太低": ["too little or too low"],
            "查公司介绍": ["check company introduction", "check company information", "check company info"],
            "资金充足": ["sufficient funds", "have enough money"],
            "政治敏感": ["involving politics"],
            "贫穷词汇": ["poverty related"],
            "否定(not available)": ["not available"],
            "质疑来电号码": ["question the caller number", "suspicious caller number"],
            "查操作流程": ["check the operation process", "check the process"],
            "否定(wrong)": ["wrong"],
            "正在进行": ["ongoing"],
            "肯定(why not)": ["why not"],
            "陈述(ready)": ["ready"],
            "答非所问": ["not answering the question", "give an irrelevant answer"],
            "太迟了": ["too late"],
            "否定(dont have)": ["don't have"],
            "肯定(i can)": ["I can"],
            "肯定(i want)": ["I want"],
            "否定(no time)": ["no time"],
            "陈述(forget)": ["forget"],
        }},
        "telemarketing_intent_cn": {"version_0": {
            "无关领域": ["无关领域"],
            "否定(不需要)": ["否定(不需要)", "不需要"],
            "否定(不用了)": ["否定(不用了)", "不用了"],
            "肯定(好的)": ["肯定(好的)", "好的"],
            "否定(没有)": ["否定(没有)", "没有"],
            "答数值": ["答数值", "数值"],
            "答时间": ["答时间", "时间"],
            "查收费方式": ["查收费方式", "查收费方式"],
            "语气词": ["语气词"],
            "否定答复": ["否定答复", "否定答复"],
            "不信任": ["不信任", "不信任"],
            "答非所问": ["答非所问"],
            "污言秽语": ["污言秽语", "脏话", "骂人"],
            "疑问(数值)": ["疑问(数值)", "问数值"],
            "肯定(知道了)": ["肯定(知道了)", "知道了"],
            "肯定(正确)": ["肯定(正确)", "正确"],
            "资金困难": ["资金困难", "缺钱"],
            "礼貌用语": ["礼貌用语"],
            "查联系方式": ["查联系方式"],
            "查操作流程": ["查操作流程"],
            "是否机器人": ["是否机器人"],
            "招呼用语": ["招呼用语"],
            "用户正忙": ["用户正忙"],
            "肯定(是的)": ["肯定(是的)", "是的"],
            "肯定(可以)": ["肯定(可以)", "可以"],
            "查自我介绍": ["查自我介绍"],
            "肯定(嗯嗯)": ["肯定(嗯嗯)", "嗯嗯"],
            "肯定(有)": ["肯定(有)", "有"],
            "政治敏感": ["政治敏感"],
            "否定(不方便)": ["否定(不方便)", "不方便"],
            "你还在吗": ["你还在吗"],
            "肯定(需要)": ["肯定(需要)", "需要"],
            "疑问(时间)": ["疑问(时间)", "问时间"],
            "否定(不知道)": ["否定(不知道)", "不知道"],
            "疑问(地址)": ["疑问(地址)", "问地址"],
            "骚扰电话": ["骚扰电话"],
            "实体(地址)": ["实体(地址)", "地址"],
            "未能理解": ["未能理解"],
            "查公司介绍": ["查公司介绍"],
            "听不清楚": ["听不清楚"],
            "实体(人名)": ["实体(人名)", "人名"],
            "语音信箱": ["语音信箱"],
            "要求复述": ["要求复述"],
            "否定(不是)": ["否定(不是)", "不是"],
            "请讲": ["请讲"],
            "问意图": ["问意图"],
            "结束用语": ["结束用语"],
            "否定(不可以)": ["否定(不可以)", "不可以"],
            "肯定(好了)": ["肯定(好了)", "好了"],
            "请等一等": ["请等一等"],
            "查物品信息": ["查物品信息"],
            "祝福用语": ["祝福用语"],
            "否定(没时间)": ["否定(没时间)", "没时间"],
            "否定(不想要)": ["否定(不想要)", "不想要"],
            "会按时处理": ["会按时处理"],
            "查详细信息": ["查详细信息"],
            "否定(错误)": ["否定(错误)", "错误", "错了"],
            "否定(没兴趣)": ["否定(没兴趣)"],
            "我在": ["我在"],
            "号码来源": ["号码来源"],
            "投诉警告": ["投诉警告"],
            "请求谅解": ["请求谅解"],
            "赞美用语": ["赞美用语"],
            "改天再谈": ["改天再谈"],
            "已完成": ["已完成"],
            "做自我介绍": ["做自我介绍"],
            "价格太高": ["价格太高"],
            "请讲重点": ["请讲重点"],
            "听我说话": ["听我说话"],
            "肯定(没问题)": ["肯定(没问题)", "没问题"],
            "转人工客服": ["转人工客服"],
            "遭遇不幸": ["遭遇不幸"],
            "质疑来电号码": ["质疑来电号码"],
            "否定(取消)": ["否定(取消)", "取消"],
            "打错电话": ["打错电话"],
            "否定(不清楚)": ["否定(不清楚)", "不清楚"],
            "疑问(时长)": ["疑问(时长)", "问时长"],
            "资金充足": ["资金充足"],
            "祝贺用语": ["祝贺用语"],
            "已经购买": ["已经购买"],
            "查优惠政策": ["查优惠政策"],
            "肯定答复": ["肯定答复"],
            "会帮忙转告": ["会帮忙转告"],
            "疑问(姓名)": ["疑问(姓名)", "问姓名"],
            "时间推迟": ["时间推迟"],
            "考虑一下": ["考虑一下"],
            "疑问(能否)": ["疑问(能否)", "能否", "能不能"],
            "实体(时长)": ["实体(时长)", "时长"],
            "答状态": ["答状态"],
            "重复一次": ["重复一次"],
            "实体(组织)": ["实体(组织)", "组织"],
            "加快速度": ["加快速度"],
            "无所谓": ["无所谓"],
            "信号不好": ["信号不好"],
            "已经记录": ["已经记录"],
            "质疑隐私安全": ["质疑隐私安全"],
            "不是本人": ["不是本人"],
            "否定(不能)": ["否定(不能)", "不能"],
            "太少太低": ["太少太低"]
        }},
        "vira_intents": {
            "version_0": {
                "COVID-19 is not as dangerous as they say": [
                    "COVID-19 is not as dangerous as they say"
                ],
                "Do I need to continue safety measures after getting the vaccine?": [
                    "Do I need to continue safety measures after getting the vaccine?"
                ],
                "How long until I will be protected after taking the vaccine?": [
                    "How long until I will be protected after taking the vaccine?"
                ],
                "How many people already got the vaccine?": [
                    "How many people already got the vaccine?"
                ],
                "I am afraid the vaccine will change my DNA": [
                    "I am afraid the vaccine will change my DNA"
                ],
                "I am concerned getting the vaccine because I have a pre-existing condition": [
                    "I am concerned getting the vaccine because I have a pre-existing condition"
                ],
                "I am concerned I will be a guinea pig": [
                    "I am concerned I will be a guinea pig"
                ],
                "I'm concerned the vaccine will make me sick.": [
                    "I'm concerned the vaccine will make me sick."
                ],
                "I am not sure if I can trust the government": [
                    "I am not sure if I can trust the government"
                ],
                "I am young and healthy so I don't think I should vaccinate": [
                    "I am young and healthy so I don't think I should vaccinate"
                ],
                "I distrust this vaccine": [
                    "I distrust this vaccine"
                ],
                "How much will I have to pay for the vaccine": [
                    "How much will I have to pay for the vaccine"
                ],
                "I don't think the vaccine is necessary": [
                    "I don't think the vaccine is necessary"
                ],
                "I don't trust the companies producing the vaccines": [
                    "I don't trust the companies producing the vaccines"
                ],
                "I don't want my children to get the vaccine": [
                    "I don't want my children to get the vaccine"
                ],
                "I think the vaccine was not tested on my community": [
                    "I think the vaccine was not tested on my community"
                ],
                "I'm not sure it is effective enough": [
                    "I'm not sure it is effective enough"
                ],
                "I'm waiting to see how it affects others": [
                    "I'm waiting to see how it affects others"
                ],
                "COVID vaccines can be worse than the disease itself": [
                    "COVID vaccines can be worse than the disease itself"
                ],
                "Long term side-effects were not researched enough": [
                    "Long term side-effects were not researched enough"
                ],
                "Are regular safety measures enough to stay healthy?": [
                    "Are regular safety measures enough to stay healthy?"
                ],
                "Should people that had COVID get the vaccine?": [
                    "Should people that had COVID get the vaccine?"
                ],
                "Side effects and adverse reactions worry me": [
                    "Side effects and adverse reactions worry me"
                ],
                "The COVID vaccine is not safe": [
                    "The COVID vaccine is not safe"
                ],
                "The vaccine should not be mandatory": [
                    "The vaccine should not be mandatory"
                ],
                "Do vaccines work against the mutated strains of COVID-19?": [
                    "Do vaccines work against the mutated strains of COVID-19?"
                ],
                "They will put a chip/microchip to manipulate me": [
                    "They will put a chip/microchip to manipulate me"
                ],
                "What can this chatbot do?": [
                    "What can this chatbot do?"
                ],
                "What is in the vaccine?": [
                    "What is in the vaccine?"
                ],
                "Which one of the vaccines should I take?": [
                    "Which one of the vaccines should I take?"
                ],
                "Will I test positive after getting the vaccine?": [
                    "Will I test positive after getting the vaccine?"
                ],
                "Can other vaccines protect me from COVID-19?": [
                    "Can other vaccines protect me from COVID-19?"
                ],
                "Do I qualify for the vaccine?": [
                    "Do I qualify for the vaccine?"
                ],
                "I don't trust vaccines if they're from China or Russia": [
                    "I don't trust vaccines if they're from China or Russia"
                ],
                "Are the side effects worse for the second shot": [
                    "Are the side effects worse for the second shot"
                ],
                "Can I get a second dose even after a COVID exposure?": [
                    "Can I get a second dose even after a COVID exposure?"
                ],
                "Can I get other vaccines at the same time?": [
                    "Can I get other vaccines at the same time?"
                ],
                "Can I get the vaccine if I have allergies?": [
                    "Can I get the vaccine if I have allergies?"
                ],
                "Can I get the vaccine if I have had allergic reactions to vaccines before?": [
                    "Can I get the vaccine if I have had allergic reactions to vaccines before?"
                ],
                "Can I have the vaccine as a Catholic?": [
                    "Can I have the vaccine as a Catholic?"
                ],
                "Can I have the vaccine if I'm allergic to penicillin?": [
                    "Can I have the vaccine if I'm allergic to penicillin?"
                ],
                "Can I still get COVID even after being vaccinated?": [
                    "Can I still get COVID even after being vaccinated?"
                ],
                "Can you mix the vaccines?": [
                    "Can you mix the vaccines?"
                ],
                "COVID-19 vaccines cause brain inflammation": [
                    "COVID-19 vaccines cause brain inflammation"
                ],
                "Do the COVID-19 vaccines cause Bell's palsy?": [
                    "Do the COVID-19 vaccines cause Bell's palsy?"
                ],
                "Do the mRNA vaccines contain preservatives, like thimerosal?": [
                    "Do the mRNA vaccines contain preservatives, like thimerosal?"
                ],
                "Do the vaccines work in obese people?": [
                    "Do the vaccines work in obese people?"
                ],
                "Do you have to be tested for COVID before you vaccinated?": [
                    "Do you have to be tested for COVID before you vaccinated?"
                ],
                "Does the vaccine contain animal products?": [
                    "Does the vaccine contain animal products?"
                ],
                "Does the vaccine contain live COVID virus?": [
                    "Does the vaccine contain live COVID virus?"
                ],
                "Does the vaccine impact pregnancy?": [
                    "Does the vaccine impact pregnancy?"
                ],
                "Does the vaccine work if I do not experience any side effects?": [
                    "Does the vaccine work if I do not experience any side effects?"
                ],
                "How can I stay safe until I'm vaccinated?": [
                    "How can I stay safe until I'm vaccinated?"
                ],
                "How do I know I'm getting a legitimate, authorized vaccine?": [
                    "How do I know I'm getting a legitimate, authorized vaccine?"
                ],
                "How do I report an adverse reaction or side-effect": [
                    "How do I report an adverse reaction or side-effect"
                ],
                "How long do I have to wait between doses?": [
                    "How long do I have to wait between doses?"
                ],
                "How many doses do I need?": [
                    "How many doses do I need?"
                ],
                "How was the vaccine tested?": [
                    "How was the vaccine tested?"
                ],
                "I am concerned about getting the vaccine because of my medications.": [
                    "I am concerned about getting the vaccine because of my medications."
                ],
                "I don't want the v-safe app monitoring or tracking me": [
                    "I don't want the v-safe app monitoring or tracking me"
                ],
                "I don't want to share my personal information": [
                    "I don't want to share my personal information"
                ],
                "Is breastfeeding safe with the vaccine": [
                    "Is breastfeeding safe with the vaccine"
                ],
                "Is the Johnson & Johnson vaccine less effective than the others?": [
                    "Is the Johnson & Johnson vaccine less effective than the others?"
                ],
                "Is the vaccine halal?": [
                    "Is the vaccine halal?"
                ],
                "Is the vaccine Kosher?": [
                    "Is the vaccine Kosher?"
                ],
                "Is there vaccine safety monitoring?": [
                    "Is there vaccine safety monitoring?"
                ],
                "Other vaccines have caused long-term health problems": [
                    "Other vaccines have caused long-term health problems"
                ],
                "Should I get the COVID-19 vaccine if I am immunocompromised": [
                    "Should I get the COVID-19 vaccine if I am immunocompromised"
                ],
                "Should I get the vaccine if I've tested positive for antibodies?": [
                    "Should I get the vaccine if I've tested positive for antibodies?"
                ],
                "The vaccine includes fetal tissue or abortion by-products": [
                    "The vaccine includes fetal tissue or abortion by-products"
                ],
                "The vaccine was rushed": [
                    "The vaccine was rushed"
                ],
                "Vaccine side effects are not getting reported": [
                    "Vaccine side effects are not getting reported"
                ],
                "What does vaccine efficacy mean?": [
                    "What does vaccine efficacy mean?"
                ],
                "What if I still get infected even after receiving the vaccine?": [
                    "What if I still get infected even after receiving the vaccine?"
                ],
                "What if I've been treated with convalescent plasma?": [
                    "What if I've been treated with convalescent plasma?"
                ],
                "What if I've been treated with monoclonal antibodies?": [
                    "What if I've been treated with monoclonal antibodies?"
                ],
                "What is mRNA?": [
                    "What is mRNA?"
                ],
                "What is the difference between mRNA and viral vector vaccines?": [
                    "What is the difference between mRNA and viral vector vaccines?"
                ],
                "When can I go back to normal life?": [
                    "When can I go back to normal life?"
                ],
                "Why are there different vaccines?": [
                    "Why are there different vaccines?"
                ],
                "Why do I need the COVID vaccine if I don't get immunized for flu": [
                    "Why do I need the COVID vaccine if I don't get immunized for flu"
                ],
                "Why do we need the vaccine if we can wait for herd immunity?": [
                    "Why do we need the vaccine if we can wait for herd immunity?"
                ],
                "Why get vaccinated if I can still transmit the virus?": [
                    "Why get vaccinated if I can still transmit the virus?"
                ],
                "Will 1 dose of vaccine protect me?": [
                    "Will 1 dose of vaccine protect me?"
                ],
                "Can I take a pain reliever when I get vaccinated?": [
                    "Can I take a pain reliever when I get vaccinated?"
                ],
                "Will the vaccine benefit me?": [
                    "Will the vaccine benefit me?"
                ],
                "Will the vaccine make me sterile or infertile?": [
                    "Will the vaccine make me sterile or infertile?"
                ],
                "Can we change the vaccine quickly if the virus mutates?": [
                    "Can we change the vaccine quickly if the virus mutates?"
                ],
                "Can I get COVID-19 from the vaccine?": [
                    "Can I get COVID-19 from the vaccine?"
                ],
                "I am still experiencing COVID symptoms even after testing negative, should I still take the vaccine?": [
                    "I am still experiencing COVID symptoms even after testing negative, should I still take the vaccine?"
                ],
                "Can children get the vaccine?": [
                    "Can children get the vaccine?"
                ],
                "Can we choose which vaccine we want?": [
                    "Can we choose which vaccine we want?"
                ],
                "How long does the immunity from the vaccine last?": [
                    "How long does the immunity from the vaccine last?"
                ],
                "The mortality rate of COVID-19 is low, why should I get the vaccine?": [
                    "The mortality rate of COVID-19 is low, why should I get the vaccine?"
                ],
                "There are many reports of severe side effects or deaths from the vaccine": [
                    "There are many reports of severe side effects or deaths from the vaccine"
                ],
                "How can I get the vaccine?": [
                    "How can I get the vaccine?"
                ],
                "I am worried about blood clots as a result of the vaccine": [
                    "I am worried about blood clots as a result of the vaccine"
                ],
                "what is covid?": [
                    "what is covid?"
                ],
                "Who developed the vaccine?": [
                    "Who developed the vaccine?"
                ],
                "Which vaccines are available?": [
                    "Which vaccines are available?"
                ],
                "What are the side effect of the vaccine?": [
                    "What are the side effect of the vaccine?"
                ],
                "Can I meet in groups after I'm vaccinated?": [
                    "Can I meet in groups after I'm vaccinated?"
                ],
                "Is it safe to go to the gym indoors if I'm vaccinated?": [
                    "Is it safe to go to the gym indoors if I'm vaccinated?"
                ],
                "How do I protect myself indoors?": [
                    "How do I protect myself indoors?"
                ],
                "What are the effects of long COVID?": [
                    "What are the effects of long COVID?"
                ],
                "Do you need a social security number to get a COVID-19 vaccine?": [
                    "Do you need a social security number to get a COVID-19 vaccine?"
                ],
                "Do you need to be a U.S. citizen to get a COVID-19 vaccine?": [
                    "Do you need to be a U.S. citizen to get a COVID-19 vaccine?"
                ],
                "Is it okay for me to travel internationally if I'm vaccinated?": [
                    "Is it okay for me to travel internationally if I'm vaccinated?"
                ],
                "Can my kids go back to school without a vaccine?": [
                    "Can my kids go back to school without a vaccine?"
                ],
                "Will I need a booster shot?": [
                    "Will I need a booster shot?"
                ],
                "If I live with an immuno-compromised individual, do I still need to wear a mask outdoors if I'm vaccinated?": [
                    "If I live with an immuno-compromised individual, do I still need to wear a mask outdoors if I'm vaccinated?"
                ],
                "Does the vaccine prevent transmission?": [
                    "Does the vaccine prevent transmission?"
                ],
                "Why is AstraZeneca not approved in the USA?": [
                    "Why is AstraZeneca not approved in the USA?"
                ],
                "Do I need to change my masking and social distancing practices depending on which COVID-19 vaccine I got?": [
                    "Do I need to change my masking and social distancing practices depending on which COVID-19 vaccine I got?"
                ],
                "Does the Pfizer vaccine cause myocarditis?": [
                    "Does the Pfizer vaccine cause myocarditis?"
                ],
                "Does the Pfizer vaccine cause heart problems?": [
                    "Does the Pfizer vaccine cause heart problems?"
                ],
                "What can you tell me about COVID-19 vaccines?": [
                    "What can you tell me about COVID-19 vaccines?"
                ],
                "Are there medical contraindications to the vaccines?": [
                    "Are there medical contraindications to the vaccines?"
                ],
                "How many people died from COVID-19?": [
                    "How many people died from COVID-19?"
                ],
                "What about reports of abnormal periods due to the vaccine?": [
                    "What about reports of abnormal periods due to the vaccine?"
                ],
                "Do I need the vaccine?": [
                    "Do I need the vaccine?"
                ],
                "Tell me about the vaccine": [
                    "Tell me about the vaccine"
                ],
                "Is the Pfizer vaccine safe for young men?": [
                    "Is the Pfizer vaccine safe for young men?"
                ],
                "Will vaccination lead to more dangerous variants?": [
                    "Will vaccination lead to more dangerous variants?"
                ],
                "Is it safe for my baby to get the vaccine?": [
                    "Is it safe for my baby to get the vaccine?"
                ],
                "Did a volunteer in the Oxford trial die?": [
                    "Did a volunteer in the Oxford trial die?"
                ],
                "Can I get COVID-19 twice?": [
                    "Can I get COVID-19 twice?"
                ],
                "Are some vaccines safer for younger children than others?": [
                    "Are some vaccines safer for younger children than others?"
                ],
                "How long am I immune from COVID-19 if I had the virus?": [
                    "How long am I immune from COVID-19 if I had the virus?"
                ],
                "Are women more likely to get worse side effects than men?": [
                    "Are women more likely to get worse side effects than men?"
                ],
                "How do I convince my family and friends to get the COVID-19 vaccine?": [
                    "How do I convince my family and friends to get the COVID-19 vaccine?"
                ],
                "Why are COVID-19 vaccination rates slowing in the U.S.?": [
                    "Why are COVID-19 vaccination rates slowing in the U.S.?"
                ],
                "I'm going to get vaccinated": [
                    "I'm going to get vaccinated"
                ],
                "Is getting vaccinated painful?": [
                    "Is getting vaccinated painful?"
                ],
                "What do I do if I lose my COVID-19 vaccination card?": [
                    "What do I do if I lose my COVID-19 vaccination card?"
                ],
                "Can I get swollen lymph nodes from the vaccine?": [
                    "Can I get swollen lymph nodes from the vaccine?"
                ],
                "Can my newborn become immune to COVID-19 if I'm vaccinated?": [
                    "Can my newborn become immune to COVID-19 if I'm vaccinated?"
                ],
                "COVID-19 is over, why should I get the vaccine?": [
                    "COVID-19 is over, why should I get the vaccine?"
                ],
                "Did one woman die after getting the J&J vaccine?": [
                    "Did one woman die after getting the J&J vaccine?"
                ],
                "Do people become magnetic after getting vaccinated?": [
                    "Do people become magnetic after getting vaccinated?"
                ],
                "Does the vaccine contain eggs?": [
                    "Does the vaccine contain eggs?"
                ],
                "How is the COVID-19 vaccine different than others?": [
                    "How is the COVID-19 vaccine different than others?"
                ],
                "How soon after I've had COVID-19 can I get the vaccination?": [
                    "How soon after I've had COVID-19 can I get the vaccination?"
                ],
                "Is it safe for my teen to get the vaccine?": [
                    "Is it safe for my teen to get the vaccine?"
                ],
                "Is this Pfizer vaccine equally effective in kids as it is in adults?": [
                    "Is this Pfizer vaccine equally effective in kids as it is in adults?"
                ],
                "Were the COVID-19 vaccines tested on animals?": [
                    "Were the COVID-19 vaccines tested on animals?"
                ],
                "What are the side effects of the vaccine in children?": [
                    "What are the side effects of the vaccine in children?"
                ],
                "What is the delta variant?": [
                    "What is the delta variant?"
                ],
                "What is the J&J vaccine?": [
                    "What is the J&J vaccine?"
                ],
                "What is the Moderna vaccine?": [
                    "What is the Moderna vaccine?"
                ],
                "What is the Pfizer vaccine?": [
                    "What is the Pfizer vaccine?"
                ],
                "Where are we required to wear masks now?": [
                    "Where are we required to wear masks now?"
                ],
                "Who can get the Pfizer vaccine?": [
                    "Who can get the Pfizer vaccine?"
                ],
                "Who can I talk to about COVID-19 in person?": [
                    "Who can I talk to about COVID-19 in person?"
                ],
                "Why should I trust you?": [
                    "Why should I trust you?"
                ],
                "Will my child need my permission to get vaccinated?": [
                    "Will my child need my permission to get vaccinated?"
                ],
                "Will the US reach herd immunity?": [
                    "Will the US reach herd immunity?"
                ],
                "Will my child miss school when they get vaccinated?": [
                    "Will my child miss school when they get vaccinated?"
                ],
                "Is the vaccine FDA approved?": [
                    "Is the vaccine FDA approved?"
                ],
                "Why do vaccinated people need to wear a mask indoors?": [
                    "Why do vaccinated people need to wear a mask indoors?"
                ],
                "Do vaccinated people need to quarantine if exposed to COVID-19?": [
                    "Do vaccinated people need to quarantine if exposed to COVID-19?"
                ],
                "What is Ivermectin?": [
                    "What is Ivermectin?"
                ],
                "Does the Johnson and Johnson vaccine cause Rare Nerve Syndrome?": [
                    "Does the Johnson and Johnson vaccine cause Rare Nerve Syndrome?"
                ],
                "What is the difference between quarantine and isolation?": [
                    "What is the difference between quarantine and isolation?"
                ],
                "Does the COVID-19 vaccine cause autism?": [
                    "Does the COVID-19 vaccine cause autism?"
                ],
                "Does the vaccine cause impotence?": [
                    "Does the vaccine cause impotence?"
                ],
                "Who is required to get vaccinated under the federal vaccine mandate?": [
                    "Who is required to get vaccinated under the federal vaccine mandate?"
                ],
                "Is the Delta variant more dangerous for kids?": [
                    "Is the Delta variant more dangerous for kids?"
                ],
                "Will there be a booster shot for J&J and Moderna?": [
                    "Will there be a booster shot for J&J and Moderna?"
                ],
                "Is the booster the same as the original vaccine?": [
                    "Is the booster the same as the original vaccine?"
                ],
                "What are the side effects of booster shots?": [
                    "What are the side effects of booster shots?"
                ],
                "What is the difference between the third shot and a booster shot?": [
                    "What is the difference between the third shot and a booster shot?"
                ],
                "How common are vaccine side effects?": [
                    "How common are vaccine side effects?"
                ],
                "Why do my kids need a vaccine if they're unlikely to get sick with COVID-19?": [
                    "Why do my kids need a vaccine if they're unlikely to get sick with COVID-19?"
                ],
                "What happens if there is a COVID-19 case at my child's school?": [
                    "What happens if there is a COVID-19 case at my child's school?"
                ],
                "Are booster shot side effects worse than those from the second shot?": [
                    "Are booster shot side effects worse than those from the second shot?"
                ],
                "Is the booster shot dangerous?": [
                    "Is the booster shot dangerous?"
                ],
                "Can I get the vaccine if I have Multiple Sclerosis?": [
                    "Can I get the vaccine if I have Multiple Sclerosis?"
                ],
                "Do children receive the same dose of Pfizer as adults?": [
                    "Do children receive the same dose of Pfizer as adults?"
                ],
                "What is the Omicron variant?": [
                    "What is the Omicron variant?"
                ],
                "How effective is the vaccine against the Omicron variant?": [
                    "How effective is the vaccine against the Omicron variant?"
                ],
                "How can I get free masks?": [
                    "How can I get free masks?"
                ],
                "Are the rapid, at-home tests accurate?": [
                    "Are the rapid, at-home tests accurate?"
                ],
                "Does a COVID-19 vaccine booster protect me against the omicron variant?": [
                    "Does a COVID-19 vaccine booster protect me against the omicron variant?"
                ],
                "What is the new omicron variant (BA.2)?": [
                    "What is the new omicron variant (BA.2)?"
                ],
                "Is the fourth shot available in the US?": [
                    "Is the fourth shot available in the US?"
                ],
                "What mask should I be wearing?": [
                    "What mask should I be wearing?"
                ],
                "How do I request at-home tests for my family?": [
                    "How do I request at-home tests for my family?"
                ],
                "Will insurance cover costs of the tests requested?": [
                    "Will insurance cover costs of the tests requested?"
                ],
                "Does the COVID-19 vaccine protect me against the \"stealth variant\"?": [
                    "Does the COVID-19 vaccine protect me against the \"stealth variant\"?"
                ],
                "Does the COVID-19 vaccine cause heart attacks?": [
                    "Does the COVID-19 vaccine cause heart attacks?"
                ],
                "Does the COVID-19 vaccine affect white blood cells?": [
                    "Does the COVID-19 vaccine affect white blood cells?"
                ],
                "Have the COVID-19 vaccines completed clinical trials?": [
                    "Have the COVID-19 vaccines completed clinical trials?"
                ],
                "What is deltacron?": [
                    "What is deltacron?"
                ],
                "How do I find the COVID-19 Community levels of my county?": [
                    "How do I find the COVID-19 Community levels of my county?"
                ],
                "What is breakthrough infection?": [
                    "What is breakthrough infection?"
                ],
                "Does the COVID-19 vaccine cause tinnitus?": [
                    "Does the COVID-19 vaccine cause tinnitus?"
                ],
                "My kids get too many injections as it is": [
                    "My kids get too many injections as it is"
                ],
                "How many doses does my child under 5 need?": [
                    "How many doses does my child under 5 need?"
                ],
                "Kids can still spread COVID after getting vaccinated": [
                    "Kids can still spread COVID after getting vaccinated"
                ],
                "Is the vaccine effective for children under 5": [
                    "Is the vaccine effective for children under 5"
                ],
                "Do I need the second booster dose?": [
                    "Do I need the second booster dose?"
                ],
                "How is the Novavax vaccine different from the other vaccines?": [
                    "How is the Novavax vaccine different from the other vaccines?"
                ],
                "What is Paxlovid?": [
                    "What is Paxlovid?"
                ],
                "Are children under 5 eligible for a vaccine?": [
                    "Are children under 5 eligible for a vaccine?"
                ],
                "What is the Novavax vaccine?": [
                    "What is the Novavax vaccine?"
                ],
                "Was the vaccine tested in kids before authorization?": [
                    "Was the vaccine tested in kids before authorization?"
                ],
                "What are the long-term effects of the vaccine for my kids?": [
                    "What are the long-term effects of the vaccine for my kids?"
                ],
                "Can my child get the booster?": [
                    "Can my child get the booster?"
                ],
                "Is the vaccine safe for children under 5?": [
                    "Is the vaccine safe for children under 5?"
                ],
                "How do I explain the benefits of the vaccine to my school age children?": [
                    "How do I explain the benefits of the vaccine to my school age children?"
                ],
                "What are the side effects of the Novavax vaccine?": [
                    "What are the side effects of the Novavax vaccine?"
                ],
                "Can my infant or child get a Moderna vaccine?": [
                    "Can my infant or child get a Moderna vaccine?"
                ],
                "I prefer to wait and see how vaccines work for my child": [
                    "I prefer to wait and see how vaccines work for my child"
                ],
                "It's too experimental for my kids": [
                    "It's too experimental for my kids"
                ],
                "What does bivalent mean?": [
                    "What does bivalent mean?"
                ],
                "Were the new boosters tested?": [
                    "Were the new boosters tested?"
                ],
                "Why didn't the new booster undergo clinical trials?": [
                    "Why didn't the new booster undergo clinical trials?"
                ],
                "Do I need another booster?": [
                    "Do I need another booster?"
                ],
                "How do the new boosters work?": [
                    "How do the new boosters work?"
                ],
                "How many boosters can I get?": [
                    "How many boosters can I get?"
                ],
                "Will the old boosters still be available?": [
                    "Will the old boosters still be available?"
                ]
            }
        },

    }


_intent_urls = {
    "a_intent": "data/a_intent.jsonl",
    "amazon_massive_intent_en_us": "data/amazon_massive_intent_en_us.jsonl",
    "amazon_massive_intent_zh_cn": "data/amazon_massive_intent_zh_cn.jsonl",
    "atis_intents": "data/atis_intents.jsonl",
    "banking77": "data/banking77.jsonl",
    "bi_text11": "data/bi_text11.jsonl",
    "bi_text27": "data/bi_text27.jsonl",
    "book6": "data/book6.jsonl",
    "carer": "data/carer.jsonl",
    "chatbots": "data/chatbots.jsonl",
    "chinese_news_title": "data/chinese_news_title.jsonl",
    "cmid_4class": "data/cmid_4class.jsonl",
    "cmid_36class": "data/cmid_36class.jsonl",
    "coig_cqia": "data/coig_cqia.jsonl",
    "conv_intent": "data/conv_intent.jsonl",
    "crosswoz": "data/crosswoz.jsonl",
    "dmslots": "data/dmslots.jsonl",
    "dnd_style_intents": "data/dnd_style_intents.jsonl",
    "emo2019": "data/emo2019.jsonl",
    "finance21": "data/finance21.jsonl",
    "ide_intent": "data/ide_intent.jsonl",
    "intent_classification": "data/intent_classification.jsonl",
    "jarvis_intent": "data/jarvis_intent.jsonl",
    "mobile_assistant": "data/mobile_assistant.jsonl",
    "mtop_intent": "data/mtop_intent.jsonl",
    "out_of_scope": "data/out_of_scope.jsonl",
    "ri_sawoz_domain": "data/ri_sawoz_domain.jsonl",
    "ri_sawoz_general": "data/ri_sawoz_general.jsonl",
    "small_talk": "data/small_talk.jsonl",
    "smp2017_task1": "data/smp2017_task1.jsonl",
    "smp2019_task1_domain": "data/smp2019_task1_domain.jsonl",
    "smp2019_task1_intent": "data/smp2019_task1_intent.jsonl",
    "snips_built_in_intents": "data/snips_built_in_intents.jsonl",
    "star_wars": "data/star_wars.jsonl",
    "suicide_intent": "data/suicide_intent.jsonl",
    "telemarketing_intent_en": "data/telemarketing_intent_en.jsonl",
    "telemarketing_intent_cn": "data/telemarketing_intent_cn.jsonl",
    "vira_intents": "data/vira_intents.jsonl",

}


_template_urls = {
    "a_intent_template": "data/a_intent_template.txt",
    "amazon_massive_intent_en_us_template": "data/amazon_massive_intent_en_us_template.txt",
    "amazon_massive_intent_zh_cn_template": "data/amazon_massive_intent_zh_cn_template.txt",
    "atis_intents_template": "data/atis_intents_template.txt",
    "banking77_template": "data/banking77_template.txt",
    "bi_text11_template": "data/bi_text11_template.txt",
    "bi_text27_template": "data/bi_text27_template.txt",
    "book6_template": "data/book6_template.txt",
    "carer_template": "data/carer_template.txt",
    "chatbots_template": "data/chatbots_template.txt",
    "chinese_news_title_template": "data/chinese_news_title_template.txt",
    "cmid_4class_template": "data/cmid_4class_template.txt",
    "cmid_36class_template": "data/cmid_36class_template.txt",
    "coig_cqia_template": "data/coig_cqia_template.txt",
    "conv_intent_template": "data/conv_intent_template.txt",
    "crosswoz_template": "data/crosswoz_template.txt",
    "dmslots_template": "data/dmslots_template.txt",
    "dnd_style_intents_template": "data/dnd_style_intents_template.txt",
    "emo2019_template": "data/emo2019_template.txt",
    "finance21_template": "data/finance21_template.txt",
    "ide_intent_template": "data/ide_intent_template.txt",
    "intent_classification_template": "data/intent_classification_template.txt",
    "jarvis_intent_template": "data/jarvis_intent_template.txt",
    "mobile_assistant_template": "data/mobile_assistant_template.txt",
    "mtop_intent_template": "data/mtop_intent_template.txt",
    "out_of_scope_template": "data/out_of_scope_template.txt",
    "ri_sawoz_domain_template": "data/ri_sawoz_domain_template.txt",
    "ri_sawoz_general_template": "data/ri_sawoz_general_template.txt",
    "small_talk_template": "data/small_talk_template.txt",
    "smp2017_task1_template": "data/smp2017_task1_template.txt",
    "smp2019_task1_domain_template": "data/smp2019_task1_domain_template.txt",
    "smp2019_task1_intent_template": "data/smp2019_task1_intent_template.txt",
    "snips_built_in_intents_template": "data/snips_built_in_intents_template.txt",
    "star_wars_template": "data/star_wars_template.txt",
    "suicide_intent_template": "data/suicide_intent_template.txt",
    "telemarketing_intent_en_template": "data/telemarketing_intent_en_template.txt",
    "telemarketing_intent_cn_template": "data/telemarketing_intent_cn_template.txt",
    "vira_intents_template": "data/vira_intents_template.txt",

}


_prompt_urls = {
    "a_intent_prompt": None,
    "amazon_massive_intent_en_us_prompt": None,
    "amazon_massive_intent_zh_cn_prompt": None,
    "atis_intents_prompt": None,
    "banking77_prompt": None,
    "bi_text11_prompt": None,
    "bi_text27_prompt": None,
    "book6_prompt": None,
    "carer_prompt": None,
    "chatbots_prompt": None,
    "chinese_news_title_prompt": None,
    "cmid_4class_prompt": None,
    "cmid_36class_prompt": None,
    "coig_cqia_prompt": None,
    "conv_intent_prompt": None,
    "crosswoz_prompt": None,
    "dmslots_prompt": None,
    "dnd_style_intents_prompt": None,
    "emo2019_prompt": None,
    "finance21_prompt": None,
    "ide_intent_prompt": None,
    "intent_classification_prompt": None,
    "jarvis_intent_prompt": None,
    "mobile_assistant_prompt": None,
    "mtop_intent_prompt": None,
    "out_of_scope_prompt": None,
    "ri_sawoz_domain_prompt": None,
    "ri_sawoz_general_prompt": None,
    "small_talk_prompt": None,
    "smp2017_task1_prompt": None,
    "smp2019_task1_domain_prompt": None,
    "smp2019_task1_intent_prompt": None,
    "snips_built_in_intents_prompt": None,
    "star_wars_prompt": None,
    "suicide_intent_prompt": None,
    "telemarketing_intent_en_prompt": None,
    "telemarketing_intent_cn_prompt": None,
    "vira_intents_prompt": None,

}


_CITATION = """\
@dataset{few_shot_intent_sft,
  author       = {Xing Tian},
  title        = {few_shot_intent_sft},
  month        = sep,
  year         = 2023,
  publisher    = {Xing Tian},
  version      = {1.0},
}
"""


class FewShotIntentSFT(datasets.GeneratorBasedBuilder):
    VERSION = datasets.Version("1.0.0")

    intent_configs = list()
    for name in _intent_urls.keys():
        config = datasets.BuilderConfig(name=name, version=VERSION, description=name)
        intent_configs.append(config)

    template_configs = list()
    for name in _template_urls.keys():
        config = datasets.BuilderConfig(name=name, version=VERSION, description=name)
        template_configs.append(config)

    prompt_configs = list()
    for name in _prompt_urls.keys():
        config = datasets.BuilderConfig(name=name, version=VERSION, description=name)
        prompt_configs.append(config)

    BUILDER_CONFIGS = [
        *intent_configs,
        *template_configs,
        *prompt_configs,
    ]

    def _info(self):
        if self.config.name in _intent_urls.keys():
            features = datasets.Features({
                "text": datasets.Value("string"),
                "label": datasets.Value("string"),
                "data_source": datasets.Value("string"),
            })
        elif self.config.name in _template_urls.keys():
            features = datasets.Features({
                "prompt_template": datasets.Value("string"),
                "response_template": datasets.Value("string"),
                "kwargs": datasets.Value("string"),
            })
        elif self.config.name in _prompt_urls.keys():
            features = datasets.Features(
                {
                    "prompt": datasets.Value("string"),
                    "response": datasets.Value("string"),
                    "not_applicable": datasets.Value("bool"),
                    "intent": datasets.Value("string"),
                    "intent_version": datasets.Value("string"),
                    "n_way": datasets.Value("int32"),
                    "n_shot": datasets.Value("int32"),
                    "description": datasets.Value("string"),
                }
            )
        else:
            raise NotImplementedError

        return datasets.DatasetInfo(
            features=features,
            supervised_keys=None,
            homepage="",
            license="",
            citation=_CITATION,
        )

    def _split_intent_generators(self, dl_manager):
        """Returns SplitGenerators."""
        url = _intent_urls[self.config.name]
        dl_path = dl_manager.download(url)
        archive_path = dl_path

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"archive_path": archive_path, "split": "train"},
            ),
            datasets.SplitGenerator(
                name=datasets.Split.VALIDATION,
                gen_kwargs={"archive_path": archive_path, "split": "validation"},
            ),
            datasets.SplitGenerator(
                name=datasets.Split.TEST,
                gen_kwargs={"archive_path": archive_path, "split": "test"},
            ),
        ]

    def _split_template_generators(self, dl_manager):
        """Returns SplitGenerators."""
        url = _template_urls[self.config.name]
        dl_path = dl_manager.download(url)
        archive_path = dl_path

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"archive_path": archive_path},
            ),
        ]

    def _split_prompt_generators(self, dl_manager):
        """Returns SplitGenerators."""
        dataset_name = self.config.name[:-7]
        intent_url = _intent_urls.get(dataset_name)
        intent_dl_path = dl_manager.download(intent_url)

        template_name = "{}_template".format(dataset_name)
        template_url = _template_urls.get(template_name)
        template_dl_path = dl_manager.download(template_url)

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"intent_dl_path": intent_dl_path, "template_dl_path": template_dl_path,
                            "data_source": dataset_name, "split": "train"},
            ),
            datasets.SplitGenerator(
                name=datasets.Split.TEST,
                gen_kwargs={"intent_dl_path": intent_dl_path, "template_dl_path": template_dl_path,
                            "data_source": dataset_name, "split": "test"},
            ),
        ]

    def _split_generators(self, dl_manager):
        """Returns SplitGenerators."""
        if self.config.name in _intent_urls.keys():
            return self._split_intent_generators(dl_manager)
        elif self.config.name in _template_urls.keys():
            return self._split_template_generators(dl_manager)
        elif self.config.name in _prompt_urls.keys():
            return self._split_prompt_generators(dl_manager)
        else:
            raise NotImplementedError

    def _generate_intent_examples(self, archive_path, split):
        """Yields examples."""
        archive_path = Path(archive_path)

        idx = 0

        with open(archive_path, "r", encoding="utf-8") as f:
            for row in f:
                sample = json.loads(row)

                if sample["split"] != split:
                    continue

                yield idx, {
                    "text": sample["text"],
                    "label": sample["label"],
                    "data_source": sample["data_source"],
                }
                idx += 1

    def _generate_template_examples(self, archive_path):
        archive_path = Path(archive_path)

        templates = PromptDataset.load_templates(template_file=archive_path)
        for idx, template in enumerate(templates):
            yield idx, template

    def _generate_prompt_examples(self, intent_dl_path, template_dl_path, data_source, split):
        dataset = PromptDataset(
            intent_file=intent_dl_path,
            template_file=template_dl_path,
            data_source=data_source,
            split=split,
        )
        for idx, sample in enumerate(dataset):
            yield idx, sample

    def _generate_examples(self, **kwargs):
        """Yields examples."""
        if self.config.name in _intent_urls.keys():
            return self._generate_intent_examples(**kwargs)
        elif self.config.name in _template_urls.keys():
            return self._generate_template_examples(**kwargs)
        elif self.config.name in _prompt_urls.keys():
            return self._generate_prompt_examples(**kwargs)
        else:
            raise NotImplementedError


if __name__ == '__main__':
    pass
