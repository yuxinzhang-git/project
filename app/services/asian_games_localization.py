"""Chinese labels for the English-only fields exposed by the official feed."""

from __future__ import annotations

import re
from typing import Any


DISCIPLINE_ZH = {
    "3x3 Basketball": "三人篮球",
    "Artistic Gymnastics": "竞技体操",
    "Athletics": "田径",
    "Badminton": "羽毛球",
    "Baseball": "棒球",
    "Beach Volleyball": "沙滩排球",
    "Boxing": "拳击",
    "Canoe Sprint": "皮划艇静水",
    "Cycling Road": "公路自行车",
    "Equestrian": "马术",
    "Esports": "电子竞技",
    "Fencing": "击剑",
    "Football": "足球",
    "Handball": "手球",
    "Hockey": "曲棍球",
    "Kabaddi": "卡巴迪",
    "Karate": "空手道",
    "Rowing": "赛艇",
    "Sepaktakraw": "藤球",
    "Shooting": "射击",
    "Soft Tennis": "软式网球",
    "Squash": "壁球",
    "Swimming": "游泳",
    "Table Tennis": "乒乓球",
    "Water Polo": "水球",
    "Weightlifting": "举重",
    "Wushu": "武术",
}

VENUE_ZH = {
    "Circular course around the Aichi Prefectural Government office and the Nagoya City Hall": "爱知县政府及名古屋市政府周边环形赛道",
    "Nagoya City Higashiyama Park Tennis Center": "名古屋市东山公园网球中心",
    "Aichi Prefectural Martial Arts Hall": "爱知县立武道馆",
    "Aichi Sky Expo Hall D": "爱知天空会展中心D馆",
    "Nagaragawa International Regatta Course(Gifu)": "岐阜长良川国际赛艇赛道",
    "Shinshiro Cycling Road Course": "新城公路自行车赛道",
    "Nagoya City Mizuho Park Gymnasium - Court 1": "名古屋市瑞穗公园体育馆1号场",
    "Hekinan Ryokuchi Beach Court": "碧南绿地沙滩场",
    "Aichi Sky Expo Esport Substage (Competition Room L4)": "爱知天空会展中心电子竞技副赛场（L4比赛室）",
    "Aichi Sky Expo Esport Competition Room L5": "爱知天空会展中心电子竞技L5比赛室",
    "Aichi Sky Expo Esport Competition Room M4": "爱知天空会展中心电子竞技M4比赛室",
    "Aichi Sky Expo Esport Competition Room M5": "爱知天空会展中心电子竞技M5比赛室",
    "Gifu Prefectural Green Stadium(Gifu)": "岐阜县立绿茵体育场",
    "Tokai Citizen Gymnasium": "东海市民体育馆",
    "Ichinomiya City Municipal Gymnasium": "一宫市立体育馆",
    "Aichi Prefectural General Shooting Gallery": "爱知县立综合射击场",
    "Toyohashi Gymnasium": "丰桥体育馆",
    "Nagoya City Trade and Industry Center": "名古屋市贸易产业中心",
    "Aichi Sky Expo Hall F": "爱知天空会展中心F馆",
    "Miyoshi Lake Canoe Course": "三好池皮划艇赛道",
    "Equestrian Park(Tokyo)": "东京马术公园",
    "Tokyo Aquatics Centre": "东京水上运动中心",
    "SKY HALL TOYOTA": "丰田天空馆",
    "Nagoya Kinjo Futo Arena": "名古屋金城码头体育馆",
    "Okazaki Chuo Sogo Park Baseball Stadium": "冈崎中央综合公园棒球场",
    "Toyohashi Municipal Baseball Stadium": "丰桥市立棒球场",
    "Nishio Gymnasium": "西尾体育馆",
    "Kinjo Futo Station Square Venue": "金城码头站前广场赛场",
    "Nagoya City General Gymnasium [Rainbow Hall]": "名古屋市综合体育馆（彩虹馆）",
    "Kasugai City Gymnasium": "春日井市体育馆",
    "Nagoya City General Gymnasium [Rainbow Pool]": "名古屋市综合体育馆（彩虹泳池）",
    "TOYOTA STADIUM": "丰田体育场",
    "WAVE STADIUM KARIYA": "刈谷波浪体育场",
}

EXACT_TEXT_ZH = {
    "Athletics": "田径",
    "Track and Field": "田径",
    "Daoshu": "刀术",
    "Jianshu": "剑术",
}


def localize_discipline(value: Any) -> str:
    text = str(value or "").strip()
    return DISCIPLINE_ZH.get(text, localize_text(text))


def localize_venue(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text in VENUE_ZH:
        return VENUE_ZH[text]
    return localize_text(text)


def localize_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text or any("\u4e00" <= char <= "\u9fff" for char in text):
        return text
    if text in EXACT_TEXT_ZH:
        return EXACT_TEXT_ZH[text]

    replacements = (
        (r"Half Marathon Race Walk", "半程马拉松竞走"),
        (r"Single Sculls", "单人双桨"),
        (r"Double Sculls", "双人双桨"),
        (r"Road Race", "公路赛"),
        (r"Cross Country", "越野"),
        (r"Air Pistol", "气手枪"),
        (r"Team Kata", "团体型"),
        (r"Round of Pool", "小组赛"),
        (r"Preliminary Phase", "预赛阶段"),
        (r"Quarterfinals?", "四分之一决赛"),
        (r"Semifinals?", "半决赛"),
        (r"Finals?", "决赛"),
        (r"Qualification", "资格赛"),
        (r"Preliminary", "预赛"),
        (r"Heats?", "预赛"),
        (r"Mixed Doubles", "混合双打"),
        (r"Doubles", "双打"),
        (r"Singles", "单打"),
        (r"Individual", "个人"),
        (r"Team", "团体"),
        (r"Butterfly", "蝶泳"),
        (r"Freestyle", "自由泳"),
        (r"Breaststroke", "蛙泳"),
        (r"Backstroke", "仰泳"),
        (r"Medley", "混合泳"),
        (r"Skeet", "飞碟"),
        (r"Foil", "花剑"),
        (r"Kayak", "皮艇"),
        (r"Canoe", "划艇"),
        (r"Lightweight", "轻量级"),
        (r"Women's", "女子"),
        (r"Men's", "男子"),
        (r"Women", "女子"),
        (r"Men", "男子"),
        (r"Group\s+([A-Z])", r"小组\1"),
        (r"Pool\s+([A-Z])", r"小组\1"),
        (r"\bHeat\s+(\d+)\b", r"第\1组"),
        (r"\bMatch\s+(\d+)\b", r"第\1场"),
        (r"\bGame\s+(\d+)\b", r"第\1场"),
        (r"\bBout\s+(\d+)\b", r"第\1场"),
        (r"\bDay\s+(\d+)\b", r"第\1天"),
        (r"(\d+)m\b", r"\1米"),
        (r"(\d+)kg\b", r"\1公斤"),
        (r"\s+-\s+", " · "),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
