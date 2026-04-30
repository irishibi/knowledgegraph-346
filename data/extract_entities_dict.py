#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于词典的实体抽取 + 消歧
使用 ahocorasick 实现高效多模式匹配（若无则降级为简单循环）
"""

import json
import re
from collections import defaultdict
from typing import List, Dict, Set

try:
    import ahocorasick
    HAS_AHO = True
except ImportError:
    HAS_AHO = False
    print("提示：未安装 ahocorasick，将使用较慢的简单匹配。可运行 'pip install pyahocorasick' 加速。")

# 实体词典（手动整理 + 从文本中提取）
# 格式：{实体名称: 类型代码}
ENTITY_DICT = {
    # 人物
    "艾伦·图灵": "PER",
    "图灵": "PER",
    "艾伦·麦席森·图灵": "PER",
    "阿兰·图灵": "PER",
    "克里斯多夫·摩尔康": "PER",
    "摩尔康": "PER",
    "阿隆佐·丘奇": "PER",
    "丘奇": "PER",
    "约翰·冯·诺伊曼": "PER",
    "冯·诺伊曼": "PER",
    "冯诺依曼": "PER",
    "库尔特·哥德尔": "PER",
    "哥德尔": "PER",
    "大卫·希尔伯特": "PER",
    "希尔伯特": "PER",
    "牛顿": "PER",
    "柏拉图": "PER",
    "笛卡儿": "PER",
    "笛卡尔": "PER",
    "乔姆斯基": "PER",
    "罗素": "PER",
    "维特根斯坦": "PER",
    "怀特海": "PER",
    "艾达": "PER",
    "巴贝奇": "PER",
    "杰弗逊": "PER",
    "纽曼": "PER",
    "戈登·布朗": "PER",
    "卷福": "PER",
    "休谟": "PER",
    "艾丁顿": "PER",
    "周以真": "PER",
    "费曼": "PER",
    "斯诺": "PER",
    "维格纳": "PER",
    "米德": "PER",
    "罗森布拉特": "PER",
    "戴维斯": "PER",
    "霍奇斯": "PER",
    "哈姆雷特": "PER",
    "莎士比亚": "PER",
    # 机构/实验室
    "曼彻斯特大学": "ORG",
    "剑桥大学": "ORG",
    "普林斯顿大学": "ORG",
    "国家物理实验室": "ORG",
    "NPL": "ORG",
    "布莱切利园": "LOC",
    "政府密码学校": "ORG",
    "GC&CS": "ORG",
    "军情六处": "ORG",
    "皇家学会": "ORG",
    "英国皇家学会": "ORG",
    # 地名
    "英国": "LOC",
    "伦敦": "LOC",
    "曼彻斯特": "LOC",
    "剑桥": "LOC",
    "普林斯顿": "LOC",
    "巴黎": "LOC",
    "美国": "LOC",
    # 奖项/概念/作品
    "图灵奖": "AWARD",
    "图灵机": "CONCEPT",
    "通用图灵机": "CONCEPT",
    "图灵测试": "CONCEPT",
    "模仿游戏": "WORK",
    "恩尼格玛": "CONCEPT",
    "Enigma": "CONCEPT",
    "人工智能": "CONCEPT",
    "AI": "CONCEPT",
    "机器智能": "CONCEPT",
    "神经网络": "CONCEPT",
    "联结主义": "CONCEPT",
    "计算理论": "CONCEPT",
    "可计算数": "WORK",
    "计算机与智能": "WORK",
    "智能机器": "WORK",
    "精神之本质": "WORK",
    "皇家赦免": "EVENT",
    "皇家特赦": "EVENT",
    # 时间
    "1912年": "DATE",
    "1954年": "DATE",
    "1936年": "DATE",
    "1950年": "DATE",
}

# 别名映射
ALIAS_MAP = {
    "艾伦·图灵": ["图灵", "艾伦·图灵", "艾伦·麦席森·图灵", "阿兰·图灵", "阿兰·麦席森·图灵"],
    "克里斯多夫·摩尔康": ["摩尔康", "克里斯多夫"],
    "阿隆佐·丘奇": ["丘奇", "阿隆佐·丘奇"],
    "约翰·冯·诺伊曼": ["冯诺伊曼", "冯·诺伊曼", "冯·诺依曼"],
    "库尔特·哥德尔": ["哥德尔"],
    "大卫·希尔伯特": ["希尔伯特"],
    "牛顿": ["牛顿"],
    "柏拉图": ["柏拉图"],
    "笛卡儿": ["笛卡儿", "笛卡尔"],
    "乔姆斯基": ["乔姆斯基"],
    "罗素": ["罗素"],
    "维特根斯坦": ["维特根斯坦"],
    "怀特海": ["怀特海"],
    "艾达": ["艾达"],
    "巴贝奇": ["巴贝奇"],
    "杰弗逊": ["杰弗逊"],
    "纽曼": ["纽曼"],
    "戈登·布朗": ["戈登·布朗"],
    "卷福": ["卷福"],
    "休谟": ["休谟"],
    "艾丁顿": ["艾丁顿"],
    "周以真": ["周以真"],
    "费曼": ["费曼"],
    "斯诺": ["斯诺"],
    "维格纳": ["维格纳"],
    "米德": ["米德"],
    "罗森布拉特": ["罗森布拉特"],
    "戴维斯": ["戴维斯"],
    "霍奇斯": ["霍奇斯"],
    "哈姆雷特": ["哈姆雷特"],
    "莎士比亚": ["莎士比亚"],
    "英国": ["英国", "UK", "大不列颠"],
    "曼彻斯特大学": ["曼彻斯特大学", "曼彻斯特计算机实验室"],
    "剑桥大学": ["剑桥大学", "剑桥"],
    "普林斯顿大学": ["普林斯顿大学", "普林斯顿"],
    "国家物理实验室": ["国家物理实验室", "NPL"],
    "布莱切利园": ["布莱切利园", "Bletchley Park"],
    "图灵奖": ["图灵奖", "Turing Award"],
    "模仿游戏": ["模仿游戏", "The Imitation Game"],
    "皇家赦免": ["皇家赦免", "皇家特赦"],
    "人工智能": ["人工智能", "AI"],
    "图灵机": ["图灵机", "通用图灵机", "UTM"],
    "图灵测试": ["图灵测试", "Turing Test"],
    "恩尼格玛": ["恩尼格玛", "Enigma"],
}

# 构建反向索引
ALIAS_TO_CANON = {}
for canon, aliases in ALIAS_MAP.items():
    for alias in aliases:
        ALIAS_TO_CANON[alias] = canon

for entity in ENTITY_DICT:
    if entity not in ALIAS_TO_CANON:
        ALIAS_TO_CANON[entity] = entity


# 构建多模式匹配器
def build_automaton(patterns: Set[str]):
    """构建AC自动机"""
    if HAS_AHO:
        automaton = ahocorasick.Automaton()
        for pattern in patterns:
            automaton.add_word(pattern, pattern)
        automaton.make_automaton()
        return automaton
    else:
        return None


def find_matches_simple(text: str, patterns: Set[str]) -> List[tuple]:
    """简单循环匹配"""
    matches = []
    for pattern in patterns:
        start = 0
        while True:
            pos = text.find(pattern, start)
            if pos == -1:
                break
            matches.append((pos, pos + len(pattern), pattern))
            start = pos + 1
    # 去重并按起始位置排序
    matches = sorted(set(matches), key=lambda x: x[0])
    return matches


def find_matches(text: str, automaton) -> List[tuple]:
    """用AC自动机匹配"""
    if automaton is None:
        patterns = set(ENTITY_DICT.keys())
        return find_matches_simple(text, patterns)
    matches = []
    for end_index, pattern in automaton.iter(text):
        start = end_index - len(pattern) + 1
        matches.append((start, end_index + 1, pattern))
    # 去重
    matches = sorted(set(matches), key=lambda x: x[0])
    return matches


def merge_overlapping_matches(matches: List[tuple]) -> List[tuple]:
    """合并重叠匹配，优先保留最长的实体"""
    if not matches:
        return []
    merged = []
    matches.sort(key=lambda x: (x[0], - (x[1] - x[0])))  # 按起始位置升序，同起始长度降序
    cur = matches[0]
    for m in matches[1:]:
        if m[0] < cur[1]:
            # 重叠：保留较长的那个
            if (m[1] - m[0]) > (cur[1] - cur[0]):
                cur = m
        else:
            merged.append(cur)
            cur = m
    merged.append(cur)
    return merged


def get_sentence_context(text: str, start_char: int, end_char: int) -> str:
    """提取字符位置所在的句子"""
    sent_start = 0
    for i in range(start_char - 1, -1, -1):
        if text[i] in "。！？\n":
            sent_start = i + 1
            break
    sent_end = len(text)
    for i in range(end_char, len(text)):
        if text[i] in "。！？\n":
            sent_end = i
            break
    return text[sent_start:sent_end].strip()


def extract_entities_by_dict(text: str) -> List[Dict]:
    """基于词典抽取实体"""
    patterns = set(ENTITY_DICT.keys())
    automaton = build_automaton(patterns)
    raw_matches = find_matches(text, automaton)
    merged = merge_overlapping_matches(raw_matches)

    mentions = []
    for start, end, mention in merged:
        entity = {
            "mention": mention,
            "type_code": ENTITY_DICT[mention],
            "type_name": {"PER": "人物", "ORG": "组织机构", "LOC": "地点", "AWARD": "奖项", "CONCEPT": "概念", "WORK": "作品", "EVENT": "事件", "DATE": "日期"}.get(ENTITY_DICT[mention], ENTITY_DICT[mention]),
            "start_char": start,
            "end_char": end,
            "sentence": get_sentence_context(text, start, end),
        }
        mentions.append(entity)
    return mentions


def disambiguate_entities(mentions: List[Dict]) -> List[Dict]:
    """消歧：按规范名合并"""
    for m in mentions:
        raw = m["mention"]
        canon = ALIAS_TO_CANON.get(raw, raw)
        m["canonical_candidate"] = canon

    groups = defaultdict(list)
    for m in mentions:
        groups[m["canonical_candidate"]].append(m)

    entities = []
    for idx, (canon_name, group) in enumerate(groups.items(), start=1):
        # 多数表决确定类型
        type_counter = defaultdict(int)
        for m in group:
            type_counter[m["type_code"]] += 1
        main_type = max(type_counter, key=type_counter.get)
        main_type_name = {"PER":"人物","ORG":"组织机构","LOC":"地点","AWARD":"奖项","CONCEPT":"概念","WORK":"作品","EVENT":"事件","DATE":"日期"}.get(main_type, main_type)
        mentions_list = []
        for m in group:
            mentions_list.append({
                "mention": m["mention"],
                "start_char": m["start_char"],
                "end_char": m["end_char"],
                "sentence": m["sentence"],
                "type_code": m["type_code"]
            })
        entities.append({
            "id": f"ENT_{idx:03d}",
            "canonical_name": canon_name,
            "type_code": main_type,
            "type_name": main_type_name,
            "mentions": mentions_list,
            "kb_id": None,
            "description": f"从文本中抽取的{main_type_name}实体，规范名称为“{canon_name}”。"
        })
    return entities


def main():
    input_file = "D:\yige\python code\AI_2025_7\Turing\data\data.txt"
    output_file = "entities_disambiguated_1.json"

    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    print("正在使用词典进行实体抽取...")
    mentions = extract_entities_by_dict(text)
    print(f"抽取到 {len(mentions)} 个实体提及")

    print("正在进行实体消歧...")
    entities = disambiguate_entities(mentions)
    print(f"消歧后得到 {len(entities)} 个唯一实体")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)

    print(f"结果已保存至 {output_file}")

    for ent in entities[:15]:
        print(f"{ent['id']}: {ent['canonical_name']} ({ent['type_name']}) — 提及次数: {len(ent['mentions'])}")


if __name__ == "__main__":
    main()