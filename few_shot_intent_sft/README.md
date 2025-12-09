---
license: apache-2.0
task_categories:
- text-classification
- question-answering
- text-generation
language:
- zh
- en
size_categories:
- 100M<n<1B
---
## 小样本意图识别指令数据集

收集了意图识别的数据集, 将其制作成 prompt, 用于 few-shot 的意图识别 LLM 研究. 

编写 prompt 模板需要想像力, 你可以在 community 中交流你的想法. 

`{dataset_name}_prompt` 子集是从其对应的 `{dataset_name}` 数据集和 `{dataset_name}_template` 子集动态生成的, 因此每一次的结果都会不一样. 

提示: 由于训练时 prompt 的长度可能超出最大限制而被 truncate, 因此尽量把 prompt 设计成即使被 truncate 也仍然可以用于 GPT 训练. 

[提示工程指南](https://www.promptingguide.ai/zh/techniques/cot)


### 样本示例

<details>
<summary>train subset prompt 示例: (intent: Is it safe to go to the gym indoors if I'm vaccinated?)</summary>
<pre><code>intent recognition.<br>
Examples:
------------
text: will i be okay on the gym
intent: Is it safe to go to the gym indoors if I'm vaccinated?
------------
text: I want to go and exercise at the gym, indoors, but I don't know if it's safe?
intent: Is it safe to go to the gym indoors if I'm vaccinated?
------------
text: I worry I will catch Covid from the Gym even though I have been vaccinated?
intent: Is it safe to go to the gym indoors if I'm vaccinated?
------------
text: What does the fda think about the covid 19 vaccine?
intent: Is the vaccine FDA approved?
------------
text: it's never safe in a gym there are always bacteria everywhere
intent: Is it safe to go to the gym indoors if I'm vaccinated?
------------
text: who is the difference between FDA authorization and approval?
intent: Is the vaccine FDA approved?
------------
text: would the vaccine FDA be approved
intent: Is the vaccine FDA approved?
------------
text: If I had my vaccine, is it safe to go to the indoor gym?
intent:
</code></pre>
</details>


<details>
<summary>train subset prompt 示例: (intent: 考虑一下)</summary>
<pre><code>电销场景意图识别。如果不能确定，请输出 “未知意图”。<br>
Examples:
------------
text: 没关系啦 知道的
intent: 肯定答复
------------
text: 怎么能联系你
intent: 查联系方式
------------
text: 恩。让我想想吧。
intent: 考虑一下
------------
text: 说点有用的
intent: 请讲重点
------------
text: 唉唉
intent: 语气词
------------
text: 说快一点
intent: 请讲重点
------------
text: 再介绍一下
intent: 要求复述
------------
text: 从哪弄到我信息
intent: 质疑隐私安全
------------
text: 哎。。不是的
intent: 不是
------------
text: 给我电话号码
intent: 查联系方式
------------
text: 先看看吧
intent: 考虑一下
------------
text: 怎么知道道我的信息
intent: 质疑隐私安全
------------
text: 哎,再说吧,我再想想
intent: 考虑一下
------------
text: 不,我清醒。
intent: 不是
------------
text: 重说一次
intent: 要求复述
------------
text: 行了,晚安
intent: 肯定答复
------------
text: 额额额额
intent: 语气词
------------
text: 恩。哎再说吧我考虑一下hiahia
intent:
</code></pre>
</details>


<details>
<summary>train subset prompt 示例: (intent: 污言秽语)</summary>
<pre><code>电销场景意图识别。<br>
Examples:
text: 那留言
intent: 语音信箱<br>
text: 好啊,哈哈,没事,我再找其他的人
intent: 好的<br>
text: 在!
intent: 我在<br>
text: 要打副本,没时间
intent: 没时间<br>
text: 必须去学习!赶快去!
intent: 加快速度<br>
text: 好的。满汉全席送上
intent: 好的<br>
text: 你看到我给你的留言了么
intent: 语音信箱<br>
text: 我在呢。
intent: 我在<br>
text: 傻逼？
intent: 污言秽语<br>
text: 胸大无脑
intent: 污言秽语<br>
text: 不着急。
intent: 请等一等<br>
text: 恩 我是团子
intent: 做自我介绍<br>
text: 我是收电费的
intent: 做自我介绍<br>
text: 我现在没时间接电话呢,待会儿打给你。
intent: 没时间<br>
text: 好的。哈哈。初六见。我去睡觉啦
intent: 好的<br>
text: 在啊
intent: 我在<br>
text: 包皮猩
intent: 污言秽语<br>
text: 离开一下
intent: 请等一等<br>
text: 有病
intent: 污言秽语<br>
text: 给我留个言
intent: 语音信箱<br>
text: 你等一下
intent: 请等一等<br>
text: 立刻马上!!!快快快快
intent: 加快速度<br>
text: 我是郭钊源
intent: 做自我介绍<br>
text: 快点儿
intent: 加快速度<br>
text: 没时间睡觉怎么办吖
intent: 没时间<br>
text: 吃!你来
intent:
</code></pre>
</details>


<details>
<summary>test subset prompt 示例: (intent: 未能理解)</summary>
<pre><code>电销场景意图识别。如果不能确定，请输出 “未知意图”。<br>
Examples:
------------
text: 讲什么
intent: 未能理解
------------
text: 等着吧!
intent: 请等一等
------------
text: 搞不懂你
intent: 未能理解
------------
text: 我实在是不想弄了,我那时事多没时间啊!
intent: 没时间
------------
text: 这你自己不清楚自己啊,还不晓得
intent: 不清楚
------------
text: 没问题放心吧
intent: 肯定(没问题)
------------
text: 公司名字是什么
intent: 查公司介绍
------------
text: 不放弃
intent: 肯定(需要)
------------
text: 老师也不懂
intent:
</code></pre>
</details>


<details>
<summary>test subset prompt 示例: (intent: 肯定(嗯嗯))</summary>
<pre><code>电销场景意图识别。
不确定时请输出 “未知领域”。<br>
Examples:
------------
text: 截止期过了多少天
intent: 疑问(时长)
------------
text: 不了
intent: 不需要
------------
text: 不行,不够不够
intent: 否定(不可以)
------------
text: 4个1
intent: 答数值
------------
text: 辽宁
intent: 地址
------------
text: 不清楚
intent: 不清楚
------------
text: 店里
intent: 地址
------------
text: 嗯啊嗯嗯来吧
intent: 肯定(嗯嗯)
------------
text: 利息比别的贷款高
intent: 价格太高
------------
text: 算23点,[9,4,8,2
intent: 答数值
------------
text: 可以还得上
intent: 会按时处理
------------
text: 对啊  就是不行
intent: 否定(不可以)
------------
text: 真的不便宜
intent: 价格太高
------------
text: 嗯,thanks
intent: 肯定(嗯嗯)
------------
text: 这你自己不清楚自己啊,还不晓得
intent: 不清楚
------------
text: 我找找吧
intent: 会按时处理
------------
text: 这是拖欠几天了
intent: 疑问(时长)
------------
text: 不需要证据
intent: 不需要
------------
text: 噢,谢谢
intent: 肯定(嗯嗯)
------------
text: 恩恩,想我
intent:
</code></pre>
</details>


<details>
<summary>test subset prompt 示例: (intent: 不信任)</summary>
<pre><code>意图识别。<br>
Examples:
text: 你不要答非所问
intent: 答非所问<br>
text: 费用搞错了
intent: 否定(错误)<br>
text: 我给你留言了,你木有回
intent: 语音信箱<br>
text: 小骗子
intent: 不信任<br>
text: 昆明
intent: 实体(地址)<br>
text: 哦,行,好了你发信息给我
intent: 肯定(可以)<br>
text: 哦,这样啊,没时间就算了
intent: 没时间<br>
text: 我错了,别欺负我了
intent: 请求谅解<br>
text: 万一你们是骗子怎么办
intent: 不信任<br>
text: 我太乃刀了
intent: 无关领域<br>
text: 讲清楚重要的
intent: 请讲重点<br>
text: 骗子,好好说话
intent:
</code></pre>
</details>


### 数据来源

数据集从网上收集整理如下:


#### 意图识别

意图识别（英语）
| 数据 | 语言 | 原始数据/项目地址 | 样本个数 | 原始数据描述 | 替代数据下载地址 |
| :--- | :---: |    :---:      |   :---: |    :---:    |     :---:     |
| ATIS | 英语 | [ATIS](https://paperswithcode.com/dataset/atis); [ATIS_dataset](https://github.com/howl-anderson/ATIS_dataset) | 4978(Training set)+893(Testing set) | 微软提供的公开数据集 (Airline Travel Information System)，实现意图识别任务。 | [atis_intents](https://huggingface.co/datasets/fathyshalab/atis_intents) |
| conv_intent | 英语 | [conv_intent](https://huggingface.co/datasets/generalization/conv_intent_Full-p_1) | 13.8K |  | [intent-recogniton](https://www.kaggle.com/code/upsunny/intent-recogniton-based-on-bert) |
| banking77 | 英语 | [banking77](https://arxiv.org/abs/2003.04807); [task-specific-datasets](https://github.com/PolyAI-LDN/task-specific-datasets) | 13,083 | 在线银行查询数据集 | [banking77](https://huggingface.co/datasets/banking77) |
| mobile_assistant | 英语 | [Intent-Classification-large](https://huggingface.co/datasets/dipesh/Intent-Classification-large) | 17K (但是我去除了意图为 others 的样本.) |  |  |
| amazon_massive_intent_en_us | 英语 | [amazon_massive_intent_en_us](https://huggingface.co/datasets/SetFit/amazon_massive_intent_en-US) | 16.5K | Alexa virtual assistant | [nlu_evaluation_data](https://huggingface.co/datasets/nlu_evaluation_data) |
| snips_built_in_intents | 英语 | [nlu-benchmark](https://github.com/sonos/nlu-benchmark); [benchmarking](https://medium.com/snips-ai/benchmarking-natural-language-understanding-systems-d35be6ce568d) | 328 |  | [snips_built_in_intents](https://huggingface.co/datasets/snips_built_in_intents) |
| vira_intents | 英语 | [vira-intent-classification](https://github.com/IBM/vira-intent-classification) | 10.9K | COVID-19 疫苗意图 | [vira_intents_live](https://huggingface.co/datasets/codesj/vira-intents-live); [vira_intents_live](https://huggingface.co/datasets/vira-chatbot/vira-intents-live) |
| intent_classification | 英语 | [intent_classification](https://huggingface.co/datasets/Bhuvaneshwari/intent_classification) | 13.8K |  |  |
| Out-of-Scope | 英语 | [范围外意图分类数据集](https://tianchi.aliyun.com/dataset/94112); [clinc150](https://archive.ics.uci.edu/dataset/570/clinc150); [clinc150](https://paperswithcode.com/dataset/clinc150) |  | 该数据集提供了一种评估“Out-of-Scope”输入的意图分类模型的方法。 | [Out-of-Scope Intent Classification Dataset](https://www.kaggle.com/datasets/stefanlarson/outofscope-intent-classification-dataset); [clinc_oos](https://huggingface.co/datasets/clinc_oos); [xjlulu/ntu_adl_intent](https://huggingface.co/datasets/xjlulu/ntu_adl_intent); [cmaldona/Generalization-MultiClass-CLINC150-ROSTD](https://huggingface.co/datasets/cmaldona/Generalization-MultiClass-CLINC150-ROSTD); [FastFit/clinc_150](https://huggingface.co/datasets/FastFit/clinc_150) |
| finance21 | 英语 | [finance21](https://github.com/Dark-Sied/Intent_Classification/) |  |  |  |
| book6 | 英语 | [book6](https://github.com/ajinkyaT/CNN_Intent_Classification) | 12000 | Six categories namely: AddToPlaylist, BookRestaurant, GetWeather , RateBook , SearchCreativeWork, SearchScreeningEvent each having nearly 2000 sentences. | [Intent Recognition Dataset](https://www.kaggle.com/datasets/himanshunayal/intent-recognition-dataset) |
| bi_text | 英语 | [bi_text](https://www.kaggle.com/datasets/bitext/training-dataset-for-chatbotsvirtual-assistants); [customer-support-intent-dataset](https://www.kaggle.com/datasets/scodepy/customer-support-intent-dataset) | 8175 | 该数据集涵盖“客户支持”领域，包括分为 11 个类别的 27 个意图。 这些意图是从 Bitext 的 20 个特定领域数据集（银行、零售、公用事业……）中选择的，保留了跨领域的通用意图。 |  |
| small talk | 英语 | [Small Talk](https://www.kaggle.com/datasets/salmanfaroz/small-talk-intent-classification-data) | 3000 | 闲聊用于为用户提供与聊天机器人的随意对话流程 |  |
| chatbots | 英语 | [Chatbots: Intent Recognition Dataset](https://www.kaggle.com/datasets/elvinagammed/chatbots-intent-recognition-dataset) |  | 用于分类、识别和聊天机器人开发的数据 |  |
| ide_intent | 英语 | [intent-classification-for-ide-functionalities](https://www.kaggle.com/datasets/abdullahusmani86/intent-classification-for-ide-functionalities) | 27019 | IDE 意图分类数据集。 |  |
| star_wars | 英语 | [star-wars](https://www.kaggle.com/datasets/aslanahmedov/star-wars-chat-bot) | 100 | 包含有关星球大战宇宙的各种数据。 |  |
| jarvis_intent | 英语 | [jarvisintent](https://www.kaggle.com/datasets/joelyu/jarvisintent) | 4556 |  |  |
| dnd_style_intents | 英语 |  | train: 131K; eval: 16.3K; test: 16.3K; | 该数据集是为游戏开发者对话系统中的意图分类模块而设计的。 数据集中有超过 17 个意图的约 163K 个示例。 | [neurae/dnd_style_intents](https://huggingface.co/datasets/neurae/dnd_style_intents) |
| HWU64 | 英语 | [1903.05566](https://arxiv.org/abs/1903.05566) | train: 8954; validation: 1076; test: 1076; | 具有 64 个意图和多个领域的个人助理 | [FastFit/hwu_64](https://huggingface.co/datasets/FastFit/hwu_64) |


意图识别（汉语）
| 数据 | 语言 | 原始数据/项目地址 | 样本个数 | 原始数据描述 | 替代数据下载地址 |
| :--- | :---: |    :---:      |   :---: |    :---:    |     :---:     |
| amazon_massive_intent_zh_cn | 汉语 |  [amazon_massive_intent_zh_cn](https://huggingface.co/datasets/SetFit/amazon_massive_intent_zh-CN) | 16.5K | Alexa virtual assistant |  |
| THU Intent Corpus | 汉语 |  | 共计约6,000个句子 | 清华大学发布的中文意图识别和词槽填充数据集，包含15个领域和27个意图类别 |  |
| CrossWOZ | 汉语 | [CrossWOZ](https://github.com/thu-coai/CrossWOZ) |  | CrossWOZ是第一个大规模中文跨域Wizard-of-Oz任务导向数据集。 它包含 5 个领域的 6K 对话会话和 102K 话语，包括酒店、餐厅、景点、地铁和出租车。 此外，该语料库还包含用户侧和系统侧丰富的对话状态和对话行为注释。 |  |
| CMID | 汉语 | [CMID](https://github.com/ishine/CMID) |  | 该数据集用于中文医学 QA 意图理解任务。 |  |
| dmslots | 汉语 | [dmslots](https://raw.githubusercontent.com/kids/bert_nlu/main/data/dmslots.txt) |  | 弱标注数据 |  |
| SMP2017 | 汉语 | [SMP2017-ECDT](http://ir.hit.edu.cn/SMP2017-ECDT); [1709.10217](https://arxiv.org/abs/1709.10217); [SMP2017ECDT-DATA](https://github.com/HITlilingzhi/SMP2017ECDT-DATA) |  | 第六届全国社会媒体处理大会之中文人机对话技术评测(SMP2017-ECDT) | [ChineseNLPCorpus](https://github.com/InsaneLife/ChineseNLPCorpus) |
| SMP2019 | 汉语 | [SMP2019](https://conference.cipsc.org.cn/smp2019/evaluation.html); [smp2019ecdt_task1](https://adamszq.github.io/smp2019ecdt_task1/) |  | SMP2019 ECDT 中文人机对话技术测评 | [SMP2017-2019-ECDT-data](https://github.com/hml-ubt/SMP2017-2019-ECDT-data); [ChineseNLPCorpus](https://github.com/InsaneLife/ChineseNLPCorpus) |
| a_intent | 汉语 | [意图识别](https://blog.csdn.net/weixin_42551154/article/details/129480825); [意图识别](https://competition.coggle.club/); [a_intent](https://pan.baidu.com/s/19_oqY4bC_lJa_7Mc6lxU7w?pwd=v4bi) | 12000 | 该意图识别数据集是一个多分类任务，目标是根据用户的输入文本判断用户的意图 |  |
| RiSAWOZ | 汉语 | [RiSAWOZ](https://gem-benchmark.com/data_cards/RiSAWOZ) |  | RiSAWOZ 是一个中文对话数据集。 它可用于研究各种对话任务，例如对话状态跟踪、对话上下文到文本生成、共指消解以及统一生成省略号和共指消解。 | [GEM/RiSAWOZ](https://huggingface.co/datasets/GEM/RiSAWOZ) |
| IMCS-IR | 汉语 | [中文医疗信息处理评测基准CBLUE](https://tianchi.aliyun.com/dataset/95414); [CBLUE 智能对话诊疗意图识别 IMCS-IR](https://github.com/winninghealth/imcs-ir) |  | 中文医疗信息处理挑战榜CBLUE |  |


#### 文本分类

| 数据 | 语言 | 原始数据/项目地址 | 样本个数 | 原始数据描述 | 替代数据下载地址 |
| :--- | :---: |    :---:      |   :---: |    :---:    |     :---:     |
| ag_news | 英语 | [AG_corpus_of_news_articles](http://www.di.unipi.it/~gulli/AG_corpus_of_news_articles.html); [Character-level Convolutional Networks for Text Classification](https://arxiv.org/abs/1509.01626); [ag_news](https://huggingface.co/datasets/ag_news) | 120K | AG的新闻主题分类数据集 |  |
| daily_dialog | 英语 | [DailyDialog](http://yanran.li/dailydialog) | 11.1K | 标签分类为：dummy (0), inform (1), question (2), directive (3), commissive (4). 情感分类为：no emotion (0), anger (1), disgust (2), fear (3), happiness (4), sadness (5), surprise (6). | [daily_dialog](https://huggingface.co/datasets/daily_dialog) |
| chinese_news_title | 汉语 | [中文新闻文本标题分类](https://aistudio.baidu.com/datasetdetail/103654) |  | 中文新闻标题数据集包含可供训练的32类(即新闻主题)标题47,952个，可供测试的新闻标题15,986个。在删除这些包含不能处理的特殊字符的标题后，我们保留了47,850个训练标题和15,950个测试标题(即#DataSet1)。 | [百度网盘](https://pan.baidu.com/s/1mgBTFOO) |
| ap_106 | 英语 |  |  |  | [FastFit/ap_106](https://huggingface.co/datasets/FastFit/ap_106) |
| argument_topic_71 | 英语 |  |  |  | [FastFit/argument_topic_71](https://huggingface.co/datasets/FastFit/argument_topic_71) |
| claim_stance_55 | 英语 |  |  |  | [FastFit/claim_stance_55](https://huggingface.co/datasets/FastFit/claim_stance_55) |
| trec_50 | 英语 |  |  |  | [FastFit/trec_50](https://huggingface.co/datasets/FastFit/trec_50) |
| dbpedia_70 | 英语 |  |  |  | [FastFit/dbpedia_70](https://huggingface.co/datasets/FastFit/dbpedia_70) |


#### 其它任务类型

| 数据 | 语言 | 任务类型 | 原始数据/项目地址 | 样本个数 | 原始数据描述 | 替代数据下载地址 |
| :--- | :---: |  :-----:  |    :---:      |   :---: |    :---:    |     :---:     |
| suicide_intent | 英语 | 情感分类 | [suicide-intent](https://www.kaggle.com/datasets/hetarthraval/suicide-intent-detection-dataset) | 3731 | 该数据集有四个类别：快乐、正常、悲伤和自杀意图。 |  |
| CARER | 英语 | 情感分类 | [emotion](https://paperswithcode.com/dataset/emotion) | 20K | 情感是英语 Twitter 消息的数据集，包含六种基本情感：愤怒、恐惧、快乐、爱、悲伤和惊讶。 | [dair-ai/emotion](https://huggingface.co/datasets/dair-ai/emotion) |
| COIG-CQIA | 汉语 | 指令微调 | [CValues](https://arxiv.org/abs/2307.09705); [paralym/COIG-CQIA](https://github.com/paralym/COIG-CQIA) |  | 高质量指令微调数据集，旨在为中文NLP社区提供高质量且符合人类交互行为的指令微调数据。 | [m-a-p/COIG-CQIA](https://huggingface.co/datasets/m-a-p/COIG-CQIA) |
| emo2019 | 英语 | 情感分类 | [SemEval-2019 Task 3](https://www.aclweb.org/anthology/S19-2005) | TRAIN: 30160, TEST: 5509 | 情绪检测。四个标签：others (0), happy (1), sad (2), angry (3). | [emo](https://huggingface.co/datasets/emo) |


### 数据加载

```python
#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datasets import load_dataset, concatenate_datasets

name_list = [
    "amazon_massive_intent_en_us_prompt",
    "amazon_massive_intent_zh_cn_prompt",
    "atis_intent_prompt",
    "banking77_prompt",
    "bi_text11_prompt",
    "bi_text27_prompt",
    "book6_prompt",
    # "chinese_news_title_prompt",
    "cmid_4class_prompt",
    "cmid_36class_prompt",
    "conv_intent_prompt",
    "crosswoz_prompt",
    "dmslots_prompt",
    "finance21_prompt",
    "intent_classification_prompt",
    "mobile_assistant_prompt",
    "mtop_intent_prompt",
    "out_of_scope_prompt",
    "small_talk_prompt",
    "smp2017_task1_prompt",
    "smp2019_task1_domain_prompt",
    "smp2019_task1_intent_prompt",
    "snips_built_in_intents_prompt",
    "telemarketing_intent_en_prompt",
    "telemarketing_intent_cn_prompt",
    "vira_intents_prompt",
]
train_dataset = list()
for name in name_list:
    dataset = load_dataset(
        path="qgyd2021/few_shot_intent_sft",
        name=name,
        split="train",
    )
    train_dataset.append(dataset)
train_dataset = concatenate_datasets(train_dataset)

valid_dataset = list()
for name in name_list:
    dataset = load_dataset(
        path="qgyd2021/few_shot_intent_sft",
        name=name,
        split="test",
    )
    valid_dataset.append(dataset)
valid_dataset = concatenate_datasets(valid_dataset)

```


### 参考来源
<details>
<summary>参考的数据来源,展开查看</summary>
<pre><code>
https://huggingface.co/datasets/qanastek/MASSIVE

https://huggingface.co/datasets/fathyshalab/atis_intents
https://huggingface.co/datasets/generalization/conv_intent_Full-p_1
https://huggingface.co/datasets/banking77
https://huggingface.co/datasets/dipesh/Intent-Classification-large
https://huggingface.co/datasets/SetFit/amazon_massive_intent_en-US
https://huggingface.co/datasets/SetFit/amazon_massive_intent_zh-CN
https://huggingface.co/datasets/SetFit/amazon_massive_intent_zh-TW
https://huggingface.co/datasets/snips_built_in_intents
https://huggingface.co/datasets/zapsdcn/citation_intent
https://huggingface.co/datasets/ibm/vira-intents
https://huggingface.co/datasets/mteb/mtop_intent
https://huggingface.co/datasets/Bhuvaneshwari/intent_classification
https://huggingface.co/datasets/ibm/vira-intents-live
https://huggingface.co/datasets/ebrigham/nl_banking_intents
https://pan.baidu.com/s/19_oqY4bC_lJa_7Mc6lxU7w?pwd=v4bi
https://gitee.com/a2798063/SMP2019/tree/master

https://cold-eye.github.io/post/nlp-corpus/

https://www.cluebenchmarks.com/introduce.html

https://github.com/search?q=chinese%20intent&type=repositories

https://aistudio.baidu.com/projectdetail/3441337

JDDC Corpus (JingDong Dialogue Chanllenge)
https://arxiv.org/abs/1911.09969
https://github.com/SimonJYang/JDDC-Baseline-TFIDF
https://github.com/hrlinlp/jddc2.1
https://github.com/zhangbo2008/JDDC_for_train_gpt_data
https://github.com/anony-dev-res/JDDC

ECD Corpus (Ecommerce Dialogue Corpus) 多轮对话数据集，没有标注意图。
https://arxiv.org/abs/1806.09102
https://github.com/cooelf/DeepUtteranceAggregation

</code></pre>
</details>

### TODO

```text
1. hwu_64 子集添加标签描述, 和模板. 
2. 新增子集 ap_106, argument_topic_71, claim_stance_55, trec_50, dbpedia_70 

```