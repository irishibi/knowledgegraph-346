#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版规则关系抽取 - 增加调试和模糊匹配
"""

import json
import re
from collections import defaultdict
from typing import List, Dict

# ========== 配置 ==========
ENTITIES_FILE = "entities_disambiguated_1.json"
TEXT_FILE = r"D:\yige\python code\AI_2025_7\Turing\data\data.txt"
OUTPUT_FILE = "relations.json"

# 关系规则库
RELATION_RULES = {
    "WORKED_AT": {
        "patterns": [
            r"(?P<subj>.+?)工作于(?P<obj>.+?)",
            r"(?P<subj>.+?)任职于(?P<obj>.+?)",
            r"(?P<subj>.+?)在(?P<obj>.+?)工作",
            r"(?P<subj>.+?)加入(?P<obj>.+?)",
            r"(?P<subj>.+?)服务于(?P<obj>.+?)",
            r"(?P<subj>.+?)供职于(?P<obj>.+?)",
            r"(?P<subj>.+?)进入(?P<obj>.+?)工作",
            r"(?P<subj>.+?)受雇于(?P<obj>.+?)",
        ]
    },
    "STUDIED_AT": {
        "patterns": [
            r"(?P<subj>.+?)就读于(?P<obj>.+?)",
            r"(?P<subj>.+?)在(?P<obj>.+?)学习",
            r"(?P<subj>.+?)毕业于(?P<obj>.+?)",
            r"(?P<subj>.+?)师从(?P<obj>.+?)",
            r"(?P<subj>.+?)求学于(?P<obj>.+?)",
            r"(?P<subj>.+?)就读(?P<obj>.+?)",
        ]
    },
    "PROPOSED": {
        "patterns": [
            r"(?P<subj>.+?)提出(?P<obj>.+?)",
            r"(?P<subj>.+?)发明了(?P<obj>.+?)",
            r"(?P<subj>.+?)创造了(?P<obj>.+?)",
            r"(?P<subj>.+?)设计了(?P<obj>.+?)",
            r"(?P<subj>.+?)给出(?P<obj>.+?)概念",
        ]
    },
    "LOCATED_IN": {
        "patterns": [
            r"(?P<subj>.+?)位于(?P<obj>.+?)",
            r"(?P<subj>.+?)坐落于(?P<obj>.+?)",
            r"(?P<subj>.+?)在(?P<obj>.+?)",
        ]
    },
    "BORN_IN": {
        "patterns": [
            r"(?P<subj>.+?)生于(?P<obj>.+?)",
            r"(?P<subj>.+?)出生于(?P<obj>.+?)",
        ]
    },
    "DIED_IN": {
        "patterns": [
            r"(?P<subj>.+?)卒于(?P<obj>.+?)",
            r"(?P<subj>.+?)逝世于(?P<obj>.+?)",
            r"(?P<subj>.+?)在(?P<obj>.+?)去世",
        ]
    }
}

def normalize_name(name: str) -> str:
    name = name.strip()
    # 去除中文标点
    name = re.sub(r'[，,。！？；：""''《》【】（）()\[\]{}]', '', name)
    # 去除空格
    name = re.sub(r'\s+', '', name)
    return name

def load_entities(filepath: str) -> tuple:
    """加载实体并构建名称到ID的映射（包含规范名和所有提及），同时生成归一化映射"""
    with open(filepath, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    name2id = {}
    norm2id = {}
    for ent in entities:
        # 规范名
        canon = ent["canonical_name"]
        name2id[canon] = ent["id"]
        norm = normalize_name(canon)
        norm2id[norm] = ent["id"]
        # 所有提及
        for m in ent["mentions"]:
            mention = m["mention"]
            name2id[mention] = ent["id"]
            norm_mention = normalize_name(mention)
            norm2id[norm_mention] = ent["id"]
    return entities, name2id, norm2id

def split_sentences(text: str) -> List[Dict]:
    sentences = []
    start = 0
    for i, ch in enumerate(text):
        if ch in "。！？\n":
            if i > start:
                sent_text = text[start:i+1].strip()
                if sent_text:
                    sentences.append({
                        "start": start,
                        "end": i+1,
                        "text": sent_text
                    })
            start = i+1
    if start < len(text):
        sentences.append({
            "start": start,
            "end": len(text),
            "text": text[start:].strip()
        })
    return sentences

def extract_relations_from_sentence(sent: Dict, name2id: Dict, norm2id: Dict, debug=False) -> List[Dict]:
    """在一个句子中应用所有规则，返回三元组，支持归一化模糊匹配"""
    relations = []
    text = sent["text"]
    for rel_type, rule in RELATION_RULES.items():
        for pattern in rule["patterns"]:
            for match in re.finditer(pattern, text):
                subj_str_raw = match.group("subj").strip()
                obj_str_raw = match.group("obj").strip()
                # 先尝试精确匹配
                subj_id = name2id.get(subj_str_raw)
                obj_id = name2id.get(obj_str_raw)
                if not subj_id:
                    # 模糊匹配：归一化后查找
                    subj_norm = normalize_name(subj_str_raw)
                    subj_id = norm2id.get(subj_norm)
                if not obj_id:
                    obj_norm = normalize_name(obj_str_raw)
                    obj_id = norm2id.get(obj_norm)
                if subj_id and obj_id and subj_id != obj_id:
                    relations.append({
                        "subject_id": subj_id,
                        "subject_name": subj_str_raw,
                        "relation_type": rel_type,
                        "object_id": obj_id,
                        "object_name": obj_str_raw,
                        "source_sentence": text,
                        "source_start": sent["start"] + match.start(),
                        "source_end": sent["start"] + match.end()
                    })
    return relations

def main():
    print("加载实体...")
    entities, name2id, norm2id = load_entities(ENTITIES_FILE)
    print(f"共 {len(entities)} 个唯一实体，{len(name2id)} 个原始名称映射，{len(norm2id)} 个归一化映射")

    print("加载文本并分割句子...")
    with open(TEXT_FILE, 'r', encoding='utf-8') as f:
        text = f.read()
    sentences = split_sentences(text)
    print(f"分割出 {len(sentences)} 个句子")

    print("\n=== 调试：前5个句子及其中出现的实体（精确名称）===")
    for i, sent in enumerate(sentences[:5]):
        print(f"\n句子{i+1}: {sent['text'][:100]}...")
        entities_in_sent = []
        for name, eid in name2id.items():
            if name in sent['text']:
                entities_in_sent.append(name)
        if entities_in_sent:
            print(f"  实体: {', '.join(entities_in_sent)}")
        else:
            print("  未找到任何实体（精确名称）")

    print("\n抽取关系...")
    all_rels = []
    for sent in sentences:
        rels = extract_relations_from_sentence(sent, name2id, norm2id, debug=False)
        all_rels.extend(rels)

    # 去重
    seen = set()
    unique = []
    for r in all_rels:
        key = (r["subject_id"], r["relation_type"], r["object_id"], r["source_sentence"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"抽取到 {len(unique)} 条关系，保存至 {OUTPUT_FILE}")
    if unique:
        for r in unique[:10]:
            print(f"{r['subject_name']} --{r['relation_type']}--> {r['object_name']}")
    else:
        print("没有抽取出任何关系，请检查规则模板是否匹配文本内容。")

if __name__ == "__main__":
    main()