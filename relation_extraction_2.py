#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于实体位置和关键词的关系抽取（不依赖正则捕获）
输入：实体JSON、原始文本
输出：关系三元组JSON
"""

import json
import re
from collections import defaultdict
from typing import List, Dict, Tuple

# ========== 配置 ==========
ENTITIES_FILE = "entities_disambiguated_1.json"
TEXT_FILE = r"D:\yige\python code\AI_2025_7\Turing\data\data.txt"
OUTPUT_FILE = "relations.json"

# ========== 关系关键词映射表 ==========
# 格式: 关系类型 -> [关键词列表] (关键词按优先级排序，顺序不影响)
RELATION_KEYWORDS = {
    "WORKED_AT": ["工作于", "任职于", "加入", "服务于", "供职于", "受雇于", "工作", "任职"],
    "STUDIED_AT": ["就读于", "学习于", "毕业于", "师从", "求学于", "攻读", "取得博士学位", "获得博士学位"],
    "PROPOSED": ["提出", "发明了", "创造了", "设计了", "给出", "定义", "创建"],
    "LOCATED_IN": ["位于", "坐落于", "在"],
    "BORN_IN": ["生于", "出生于"],
    "DIED_IN": ["卒于", "逝世于", "去世于", "死"],
    "INFLUENCED": ["影响", "启发", "认为"],
}

def load_entities(filepath: str) -> Tuple[List[Dict], Dict[str, str], Dict[str, str]]:
    """加载实体，返回实体列表、名称到ID映射、名称到规范名映射"""
    with open(filepath, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    name2id = {}
    name2canon = {}
    for ent in entities:
        canon = ent["canonical_name"]
        name2canon[canon] = canon
        name2id[canon] = ent["id"]
        for m in ent["mentions"]:
            mention = m["mention"]
            name2id[mention] = ent["id"]
            name2canon[mention] = canon
    return entities, name2id, name2canon

def get_entities_in_sentence(sent_start: int, sent_end: int, entities: List[Dict]) -> List[Dict]:
    """返回落在句子范围内的实体（按出现顺序排序）"""
    result = []
    for ent in entities:
        # 取该实体的第一个提及（通常就是主要位置）
        for m in ent["mentions"]:
            if m["start_char"] >= sent_start and m["end_char"] <= sent_end:
                result.append({
                    "id": ent["id"],
                    "name": ent["canonical_name"],
                    "start": m["start_char"],
                    "end": m["end_char"],
                    "mention_text": m["mention"]
                })
                break  # 只取第一个提及
    # 按起始位置排序
    result.sort(key=lambda x: x["start"])
    return result

def extract_relations_from_sentence(sent_text: str, sent_start: int, sent_end: int, entities_in_sent: List[Dict], name2canon: Dict) -> List[Dict]:
    """
    在句子中根据关键词抽取实体间关系
    对于句子中出现的实体对，检查它们之间的文本是否包含关系关键词
    """
    relations = []
    n = len(entities_in_sent)
    for i in range(n):
        for j in range(i+1, n):
            ent_a = entities_in_sent[i]
            ent_b = entities_in_sent[j]
            # 确定两个实体的顺序（按位置）
            if ent_a["start"] < ent_b["start"]:
                first = ent_a
                second = ent_b
            else:
                first = ent_b
                second = ent_a
            # 提取两个实体之间的文本片段
            between_text = sent_text[first["end"] - sent_start : second["start"] - sent_start].strip()
            if not between_text:
                continue
            # 检查关键词
            for rel_type, keywords in RELATION_KEYWORDS.items():
                for kw in keywords:
                    if kw in between_text:
                        # 确定方向：一般关键词前面的是主语，后面的是宾语
                        # 这里简单地将第一个实体作为主语，第二个作为宾语（因为关键词通常位于两者之间）
                        # 如果需要更精确，可以检查关键词在between_text中的位置更靠近哪一侧
                        relations.append({
                            "subject_id": first["id"],
                            "subject_name": first["name"],
                            "relation_type": rel_type,
                            "object_id": second["id"],
                            "object_name": second["name"],
                            "source_sentence": sent_text,
                            "source_start": sent_start,
                            "source_end": sent_end,
                            "keyword": kw,
                            "between_text": between_text
                        })
                        break  # 一个关系类型只取第一个匹配的关键词
    return relations

def main():
    print("加载实体...")
    entities, name2id, name2canon = load_entities(ENTITIES_FILE)
    print(f"共 {len(entities)} 个唯一实体，{len(name2id)} 个名称映射")

    print("加载文本...")
    with open(TEXT_FILE, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # 分割句子（简单按句号、感叹号、问号、换行）
    sentences = []
    start = 0
    for i, ch in enumerate(full_text):
        if ch in "。！？\n":
            if i > start:
                sent_text = full_text[start:i+1].strip()
                if sent_text:
                    sentences.append({
                        "start": start,
                        "end": i+1,
                        "text": sent_text
                    })
            start = i+1
    if start < len(full_text):
        sentences.append({
            "start": start,
            "end": len(full_text),
            "text": full_text[start:].strip()
        })
    print(f"分割出 {len(sentences)} 个句子")

    all_relations = []
    for idx, sent in enumerate(sentences):
        ents_in_sent = get_entities_in_sentence(sent["start"], sent["end"], entities)
        if len(ents_in_sent) < 2:
            continue
        rels = extract_relations_from_sentence(sent["text"], sent["start"], sent["end"], ents_in_sent, name2canon)
        all_relations.extend(rels)

    # 去重（相同主语、关系、宾语且在同一个句子中只保留一次）
    seen = set()
    unique = []
    for r in all_relations:
        key = (r["subject_id"], r["relation_type"], r["object_id"], r["source_sentence"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"抽取到 {len(unique)} 条关系，保存至 {OUTPUT_FILE}")
    if unique:
        print("\n=== 关系示例（前10条）===")
        for r in unique[:10]:
            print(f"{r['subject_name']} --{r['relation_type']}--> {r['object_name']} (关键词: {r['keyword']})")
    else:
        print("没有抽取出任何关系。")
        print("请检查关系关键词是否完整，或手动添加更多关键词。")

if __name__ == "__main__":
    main()