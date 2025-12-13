#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表情包类别映射
拼音到中文的映射关系，供表情包管理工具使用
"""

# 类别映射字典：拼音 -> 中文
CATEGORY_MAP = {
    # 社交礼仪类
    "zhaohu_yongyu": "招呼用语",
    "limao_yongyu": "礼貌用语",
    "zhufu_yongyu": "祝福用语",
    "zhuhe_yongyu": "祝贺用语",
    "zanmei_yongyu": "赞美用语",
    "jieshu_yongyu": "结束用语",
    "qingqiu_liangjie": "请求谅解",
    "yuqi_ci": "语气词",
    # 肯定确认类
    "kending_haode": "肯定(好的)",
    "kending_shide": "肯定(是的)",
    "kending_keyi": "肯定(可以)",
    "kending_zhidaole": "肯定(知道了)",
    "kending_enen": "肯定(嗯嗯)",
    "kending_you": "肯定(有)",
    "kending_haole": "肯定(好了)",
    "kending_zhengque": "肯定(正确)",
    # 否定拒绝类
    "fouding_buxuyao": "否定(不需要)",
    "fouding_buxiangyao": "否定(不想要)",
    "fouding_bukeyi": "否定(不可以)",
    "fouding_buzhidao": "否定(不知道)",
    "fouding_meishijian": "否定(没时间)",
    "fouding_meixingqu": "否定(没兴趣)",
    "fouding_bufangbian": "否定(不方便)",
    "fouding_bushi": "否定(不是)",
    "fouding_buqingchu": "否定(不清楚)",
    "fouding_buyongle": "否定(不用了)",
    "fouding_quxiao": "否定(取消)",
    "fouding_cuowu": "否定(错误)",
    "fouding_dafu": "否定答复",
    # 信息查询类
    "yiwen_shijian": "疑问(时间)",
    "yiwen_dizhi": "疑问(地址)",
    "yiwen_shuzhi": "疑问(数值)",
    "yiwen_shichang": "疑问(时长)",
    "cha_xiangxi_xinxi": "查详细信息",
    "cha_lianxi_fangshi": "查联系方式",
    "cha_ziwo_jieshao": "查自我介绍",
    "cha_youhui_zhengce": "查优惠政策",
    "cha_gongsi_jieshao": "查公司介绍",
    "cha_caozuo_liucheng": "查操作流程",
    "cha_shoufei_fangshi": "查收费方式",
    "cha_wupin_xinxi": "查物品信息",
    "haoma_laiyuan": "号码来源",
    "zhiyi_laidian_haoma": "质疑来电号码",
    "wen_yitu": "问意图",
    # 信息回答类
    "shiti_dizhi": "实体(地址)",
    "da_shijian": "答时间",
    "da_feisuowen": "答非所问",
    # 对话控制类
    "qing_deng_yideng": "请等一等",
    "qing_jiang": "请讲",
    "ting_bu_qingchu": "听不清楚",
    "ni_hai_zai_ma": "你还在吗",
    "wo_zai": "我在",
    "weineng_lijie": "未能理解",
    "ting_wo_shuohua": "听我说话",
    "yonghu_zhengmang": "用户正忙",
    "gaitian_zaitan": "改天再谈",
    "shijian_tuichi": "时间推迟",
    "shifou_jiqiren": "是否机器人",
    "yaoqiu_fushu": "要求复述",
    "qing_jiang_zhongdian": "请讲重点",
    "zhuan_rengong_kefu": "转人工客服",
    # 问题异议类
    "tousu_jinggao": "投诉警告",
    "buxinren": "不信任",
    "jiage_taigao": "价格太高",
    "dacuo_dianhua": "打错电话",
    "zijin_kunnan": "资金困难",
    "zaoyu_buxing": "遭遇不幸",
    "saorao_dianhua": "骚扰电话",
    # 状态确认类
    "yi_wancheng": "已完成",
    "hui_anshi_chuli": "会按时处理",
}

# 反向映射：中文 -> 拼音
CHINESE_TO_ROMAJI = {v: k for k, v in CATEGORY_MAP.items()}
