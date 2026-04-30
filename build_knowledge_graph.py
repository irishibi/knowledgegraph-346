#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建知识图谱导入 Neo4j
- 节点显示具体名称（name 属性）
- 关系使用具体类型（WORKED_AT, PROPOSED 等）
- 去重 + 合法性校验（根据实体类型过滤非法关系）
"""

import json
import os
import re
from neo4j import GraphDatabase, exceptions

# ========== 配置 ==========
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "iris5678"

ENTITIES_FILE = "entities_disambiguated_1.json"
RELATIONS_FILE = "relations.json"

# ========== 关系类型允许的实体类型 ==========
ALLOWED_RELATION_TYPES = {
    "WORKED_AT":   {"subject_types": ["PER"],          "object_types": ["ORG"]},
    "STUDIED_AT":  {"subject_types": ["PER"],          "object_types": ["ORG"]},
    "PROPOSED":    {"subject_types": ["PER"],          "object_types": ["CONCEPT", "WORK", "AWARD"]},
    "LOCATED_IN":  {"subject_types": ["ORG", "LOC"],   "object_types": ["LOC"]},
    "BORN_IN":     {"subject_types": ["PER"],          "object_types": ["LOC"]},
    "DIED_IN":     {"subject_types": ["PER"],          "object_types": ["LOC"]},
    "INFLUENCED":  {"subject_types": ["PER"],          "object_types": ["PER", "CONCEPT"]},
}

def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")

def create_constraints(tx):
    try:
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
        print("唯一性约束已就绪")
    except Exception as e:
        print(f"约束警告: {e}")

def create_entity_node(tx, entity):
    query = """
    MERGE (e:Entity {id: $id})
    SET e.canonical_name = $canonical_name,
        e.name = $canonical_name,
        e.type = $type,
        e.type_name = $type_name,
        e.description = $description,
        e.kb_id = $kb_id
    RETURN e
    """
    tx.run(query,
           id=entity["id"],
           canonical_name=entity["canonical_name"],
           type=entity["type_code"],
           type_name=entity["type_name"],
           description=entity["description"],
           kb_id=entity.get("kb_id"))

def create_relation(tx, relation):
    rel_type_raw = relation["relation_type"].upper().replace(" ", "_")
    if not re.match(r'^[A-Z][A-Z0-9_]*$', rel_type_raw):
        print(f"跳过非法关系类型: {rel_type_raw}")
        return
    cypher = f"""
    MATCH (s:Entity {{id: $subject_id}})
    MATCH (o:Entity {{id: $object_id}})
    MERGE (s)-[r:{rel_type_raw}]->(o)
    SET r.source_sentence = $source_sentence,
        r.keyword = $keyword
    RETURN r
    """
    tx.run(cypher,
           subject_id=relation["subject_id"],
           object_id=relation["object_id"],
           source_sentence=relation.get("source_sentence", ""),
           keyword=relation.get("keyword", ""))

def clean_relations(relations, entity_type_map):
    seen = set()
    cleaned = []
    for rel in relations:
        rel_type = rel["relation_type"]
        subj_id = rel["subject_id"]
        obj_id = rel["object_id"]
        triple = (subj_id, rel_type, obj_id)
        if triple in seen:
            continue
        seen.add(triple)

        if rel_type in ALLOWED_RELATION_TYPES:
            allowed = ALLOWED_RELATION_TYPES[rel_type]
            subj_type = entity_type_map.get(subj_id, "")
            obj_type = entity_type_map.get(obj_id, "")
            if subj_type in allowed["subject_types"] and obj_type in allowed["object_types"]:
                cleaned.append(rel)
            else:
                print(f"丢弃非法关系: {rel_type} (主体:{subj_type} -> 客体:{obj_type})")
        else:
            print(f"丢弃未定义关系类型: {rel_type}")
    return cleaned

def main():
    if not os.path.exists(ENTITIES_FILE):
        print(f"错误：找不到实体文件 {ENTITIES_FILE}")
        return
    with open(ENTITIES_FILE, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    print(f"加载了 {len(entities)} 个实体")

    relations = []
    if os.path.exists(RELATIONS_FILE):
        with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
            relations = json.load(f)
        print(f"加载了 {len(relations)} 条原始关系")
    else:
        print("未找到关系文件，将只创建实体节点")

    entity_type_map = {ent["id"]: ent["type_code"] for ent in entities}
    if relations:
        relations = clean_relations(relations, entity_type_map)
        print(f"清洗后剩余 {len(relations)} 条有效关系")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("成功连接到 Neo4j")
    except exceptions.ServiceUnavailable:
        print("无法连接到 Neo4j，请检查数据库是否运行")
        return
    except exceptions.AuthError:
        print("认证失败，请检查用户名和密码")
        return

    with driver.session() as session:
        # session.execute_write(clear_database)
        # print("已清空数据库")

        session.execute_write(create_constraints)

        print("正在创建实体节点...")
        for i, ent in enumerate(entities):
            session.execute_write(create_entity_node, ent)
            if (i+1) % 20 == 0:
                print(f"  已创建 {i+1}/{len(entities)} 个节点")
        print(f"创建了 {len(entities)} 个节点")

        if relations:
            print("正在创建关系...")
            for i, rel in enumerate(relations):
                session.execute_write(create_relation, rel)
                if (i+1) % 50 == 0:
                    print(f"  已创建 {i+1}/{len(relations)} 条关系")
            print(f"创建了 {len(relations)} 条关系")
        else:
            print("没有有效关系需要创建")

    driver.close()
    print("知识图谱构建完成！")
    print("在 Neo4j Browser 中运行: MATCH (n) RETURN n LIMIT 50")

if __name__ == "__main__":
    main()