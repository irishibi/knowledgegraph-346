#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将实体以类型标签导入 Neo4j，关系以具体类型导入
- 节点标签映射：PER→Person, LOC→Location, ORG→Organization, CONCEPT→Concept, WORK→Work, AWARD→Award, EVENT→Event, DATE→Date
- 关系直接使用 relation_type 作为 Cypher 关系类型
"""

import json
import os
from neo4j import GraphDatabase, exceptions

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "iris5678"

ENTITIES_FILE = "entities_disambiguated_1.json"
RELATIONS_FILE = "relations.json"

# 实体类型代码 -> Neo4j 标签映射
TYPE_TO_LABEL = {
    "PER": "Person",
    "LOC": "Location",
    "ORG": "Organization",
    "CONCEPT": "Concept",
    "WORK": "Work",
    "AWARD": "Award",
    "EVENT": "Event",
    "DATE": "Date",
}

DEFAULT_LABEL = "Entity"

def clear_database(tx):
    """清空所有节点和关系"""
    tx.run("MATCH (n) DETACH DELETE n")

def create_constraints(tx):
    """为每种实体标签的 canonical_name 属性创建唯一性约束"""
    labels = set(TYPE_TO_LABEL.values()) | {DEFAULT_LABEL}
    for label in labels:
        try:
            tx.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.canonical_name IS UNIQUE")
        except Exception as e:
            print(f"约束创建跳过 ({label}): {e}")

def create_entity_node(tx, entity):
    """
    根据实体类型创建对应标签的节点
    使用 MERGE 基于 canonical_name 避免重复
    """
    type_code = entity["type_code"]
    label = TYPE_TO_LABEL.get(type_code, DEFAULT_LABEL)
    query = f"""
    MERGE (n:{label} {{canonical_name: $canonical_name}})
    SET n.id = $id,
        n.type_code = $type_code,
        n.type_name = $type_name,
        n.description = $description,
        n.kb_id = $kb_id
    RETURN n
    """
    tx.run(query,
           id=entity["id"],
           canonical_name=entity["canonical_name"],
           type_code=type_code,
           type_name=entity["type_name"],
           description=entity["description"],
           kb_id=entity.get("kb_id"))

def create_typed_relation(tx, relation):
    rel_type = relation["relation_type"]
    query = f"""
    MATCH (s {{canonical_name: $subject_name}})
    MATCH (o {{canonical_name: $object_name}})
    MERGE (s)-[r:{rel_type}]->(o)
    SET r.source_sentence = $source_sentence,
        r.keyword = $keyword
    RETURN r
    """
    tx.run(query,
           subject_name=relation["subject_name"],
           object_name=relation["object_name"],
           source_sentence=relation.get("source_sentence", ""),
           keyword=relation.get("keyword", ""))

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
        print(f"加载了 {len(relations)} 条关系")
    else:
        print("未找到关系文件，将只创建节点")

    # 连接 Neo4j
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("✅ 成功连接到 Neo4j")
    except exceptions.ServiceUnavailable:
        print("❌ 无法连接到 Neo4j，请检查数据库是否运行，URI 是否正确。")
        return
    except exceptions.AuthError:
        print("❌ 认证失败，请检查用户名和密码。")
        return

    with driver.session() as session:
        session.execute_write(create_constraints)
        print("已创建唯一性约束")

        # 创建节点
        print("正在创建实体节点...")
        for i, ent in enumerate(entities):
            session.execute_write(create_entity_node, ent)
            if (i+1) % 20 == 0:
                print(f"  已创建 {i+1}/{len(entities)} 个节点")
        print(f"✅ 创建了 {len(entities)} 个节点")

        # 创建关系
        if relations:
            print("正在创建关系...")
            for i, rel in enumerate(relations):
                session.execute_write(create_typed_relation, rel)
                if (i+1) % 50 == 0:
                    print(f"  已创建 {i+1}/{len(relations)} 条关系")
            print(f"✅ 创建了 {len(relations)} 条关系")
        else:
            print("没有关系需要创建")

    driver.close()
    print("\n知识图谱构建完成！")
    print(f"可在 Neo4j Browser ({NEO4J_URI.replace('bolt', 'http')}) 中运行查询：")
    print("  MATCH (n) RETURN n LIMIT 50")
    print("  MATCH p=()-[r]->() RETURN p LIMIT 25")

def clean_relations(relations):
    """去除重复关系和自循环关系"""
    seen = set()
    unique = []
    for r in relations:
        sub = r["subject_id"]
        obj = r["object_id"]
        rel = r["relation_type"].upper().strip()
        # 过滤自循环
        if sub == obj:
            continue
        # 过滤不正常关系类型（如 RELAX）
        if rel not in ["WORKED_AT", "STUDIED_AT", "PROPOSED", "LOCATED_IN", "BORN_IN", "DIED_IN", "INFLUENCED"]:
            print(f"警告: 跳过未知关系类型 {rel} 在 {sub} -> {obj}")
            continue
        key = (sub, rel, obj)
        if key in seen:
            continue
        seen.add(key)
        r["relation_type"] = rel
        unique.append(r)
    return unique


if __name__ == "__main__":
    main()