"""
基于 jieba 的中文实体抽取 + 简单消歧
输入：文本文件路径
输出：JSON 文件 (entities_disambiguated.json)
"""
#经过jieba分词处理后的效果不佳，更换策略，使用词典+AC自动机的方式，实现代码为extract_entities_dict.py
import json
import re
from collections import defaultdict
from typing import List, Dict

import jieba.posseg as pseg

INPUT_FILE = "D:\yige\python code\AI_2025_7\Turing\data\data.txt"
OUTPUT_FILE = "entities_disambiguated.json"

# 实体类型映射
TYPE_MAP = {
    "nr": "人物",
    "ns": "地点",
    "nt": "组织机构",
    "nz": "其他专有名词",
    "t": "时间",
    "m": "数字",
    "mq": "数量词",
}

# 消歧
ALIAS_MAP = {
    "艾伦·图灵": ["图灵", "艾伦·图灵", "艾伦·麦席森·图灵", "Alan Turing", "阿兰·图灵", "阿兰·麦席森·图灵"],
    "克里斯多夫·摩尔康": ["摩尔康", "克里斯多夫", "Christopher Morcom"],
    "阿隆佐·丘奇": ["丘奇", "阿隆佐·丘奇", "Alonzo Church"],
    "约翰·冯·诺伊曼": ["冯诺伊曼", "冯·诺伊曼", "冯·诺依曼", "John von Neumann"],
    "库尔特·哥德尔": ["哥德尔", "Kurt Gödel"],
    "大卫·希尔伯特": ["希尔伯特", "David Hilbert"],
    "牛顿": ["牛顿", "Isaac Newton"],
    "柏拉图": ["柏拉图"],
    "笛卡儿": ["笛卡儿", "笛卡尔"],
    "乔姆斯基": ["乔姆斯基", "Noam Chomsky"],
    "罗素": ["罗素", "Bertrand Russell"],
    "维特根斯坦": ["维特根斯坦", "Ludwig Wittgenstein"],
    "怀特海": ["怀特海", "Alfred North Whitehead"],
    "艾达": ["艾达", "Ada Lovelace"],
    "巴贝奇": ["巴贝奇", "Charles Babbage"],
    "杰弗逊": ["杰弗逊", "Geoffrey Jefferson"],
    "纽曼": ["纽曼", "M. H. A. Newman"],
    "戈登·布朗": ["戈登·布朗", "Gordon Brown"],
    "卷福": ["卷福", "本尼迪克特·康伯巴奇", "Benedict Cumberbatch"],
    "休谟": ["休谟", "David Hume"],
    "艾丁顿": ["艾丁顿", "Arthur Eddington"],
    "周以真": ["周以真", "Jeannette Wing"],
    "费曼": ["费曼", "Richard Feynman"],
    "斯诺": ["斯诺", "C. P. Snow"],
    "维格纳": ["维格纳", "Eugene Wigner"],
    "米德": ["米德", "Carver Mead"],
    "罗森布拉特": ["罗森布拉特", "Frank Rosenblatt"],
    "戴维斯": ["戴维斯", "Martin Davis"],
    "霍奇斯": ["霍奇斯", "Andrew Hodges"],
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
ALIAS_TO_CANONICAL = {}
for canon, aliases in ALIAS_MAP.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias] = canon


def normalize_entity_name(name: str) -> str:
    """名称归一化：去除空格和标点符号"""
    name = name.strip()
    name = re.sub(r"[ 　]", "", name)
    name = re.sub(r"[，,。！？；：”“《》【】（）()\[\]{}]", "", name)
    return name


def get_sentence_context(text: str, start_char: int, end_char: int) -> str:
    """提取所在句子的文本"""
    # 向前找到句首
    start = start_char
    for i in range(start_char - 1, -1, -1):
        if text[i] in "。！？\n":
            start = i + 1
            break
    # 向后找到句尾
    end = end_char
    for i in range(end_char, len(text)):
        if text[i] in "。！？\n":
            end = i
            break
    return text[start:end].strip()


def extract_entities_by_jieba(text: str) -> List[Dict]:
    """
    使用 jieba 词性标注抽取实体
    返回提及列表，包含 mention, type_code, type_name, start_char, end_char, sentence
    """
    words = pseg.cut(text)
    mentions = []
    current = None
    current_start = 0
    current_end = 0

    pos = 0
    for word, flag in words:
        if flag in TYPE_MAP:
            if current and current["type_code"] == flag:
                # 继续当前实体
                current["mention"] += word
                current["end_char"] = pos + len(word)
                current["words"].append(word)
            else:
                # 新实体开始
                if current:
                    mentions.append(current)
                current = {
                    "mention": word,
                    "type_code": flag,
                    "type_name": TYPE_MAP[flag],
                    "start_char": pos,
                    "end_char": pos + len(word),
                    "words": [word],
                }
        else:
            if current:
                mentions.append(current)
                current = None
        pos += len(word)

    if current:
        mentions.append(current)

    # 为每个提及添加上下文句子
    for ent in mentions:
        ent["sentence"] = get_sentence_context(text, ent["start_char"], ent["end_char"])
    return mentions


def disambiguate_entities(mentions: List[Dict]) -> List[Dict]:
    """消歧：合并同一实体的多个提及"""
    # 候选规范名
    for m in mentions:
        raw = m["mention"]
        norm = normalize_entity_name(raw)
        if norm in ALIAS_TO_CANONICAL:
            canon = ALIAS_TO_CANONICAL[norm]
        elif raw in ALIAS_TO_CANONICAL:
            canon = ALIAS_TO_CANONICAL[raw]
        else:
            canon = norm if len(norm) > 1 else raw
        m["canonical_candidate"] = canon

    # 分组
    groups = defaultdict(list)
    for m in mentions:
        groups[m["canonical_candidate"]].append(m)

    # 构建规范实体
    entities = []
    for idx, (canon_name, group) in enumerate(groups.items(), start=1):
        # 多数表决类型
        type_counter = defaultdict(int)
        for m in group:
            type_counter[m["type_code"]] += 1
        main_type = max(type_counter, key=type_counter.get)
        main_type_name = TYPE_MAP.get(main_type, main_type)

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
    print(f"正在读取文件: {INPUT_FILE}")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 {INPUT_FILE}")
        return

    print("正在进行实体抽取（jieba）...")
    mentions = extract_entities_by_jieba(text)
    print(f"抽取到 {len(mentions)} 个实体提及")

    print("正在进行实体消歧...")
    entities = disambiguate_entities(mentions)
    print(f"消歧后得到 {len(entities)} 个唯一实体")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)

    print(f"结果已保存至 {OUTPUT_FILE}")

    # 预览前10个实体
    print("\n=== 消歧后实体示例（前10个）===")
    for ent in entities[:10]:
        print(f"{ent['id']}: {ent['canonical_name']} ({ent['type_name']}) — 提及次数: {len(ent['mentions'])}")
        if ent['mentions']:
            sample = ent['mentions'][0]['sentence'][:60].replace("\n", " ")
            print(f"    示例提及: \"{ent['mentions'][0]['mention']}\" 上下文: {sample}...")


if __name__ == "__main__":
    main()