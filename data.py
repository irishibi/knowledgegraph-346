import pandas as pd
import re
from pandas.io.pytables import attribute_conflict_doc

df = pd.read_csv('D:\yige\python code\knowledge_graph\jobs.csv')

print(df)
print("\n列名：", df.columns.tolist())

#对于职业规划知识图谱，抽取实体类型为三种：职业领域、应聘职位 属性为要求技能，职位描述
#定义实体列和属性列
entity_columns = ['company_title','job_category']
attribute_columns = ['job_description','requirements']
print("实体列：",entity_columns)
print("属性列：",attribute_columns)

#发现requirments属性列中的信息冗长，不利于知识图谱构建，将属性信息精简
def simplify_requirements(text):
    """
    将岗位要求的长文本精简为一句话（工作经验 + 学历 + 核心技能）
    """
    if not isinstance(text, str):
        return ""

    lines = text.strip().split('\n')

    # 初始化提取结果
    skills = [] #掌握技能

    skill_keywords = {
        # 营销类
        '营销渠道', '推广方式', '市场策划', '执行能力', '商务谈判', '行业资源',
        # 运营类
        '新媒体运营', '内容策划', '文案写作', '数据分析', '运营思维', '成功运营案例',
        # 设计类
        '审美能力', '创意思维', '设计经验', '作品集',
        # 产品类
        '产品思维', '用户洞察', 'Axure', 'Figma', '产品经验',
        # 技术/通用类
        '编程基础', '算法能力', '技术栈', '开发工具', '办公软件', '沟通协调能力',
        '沟通理解能力', '逻辑思维', '问题解决', '团队协作', '责任心', '抗压能力',
        '学习能力', '认真负责', '细致耐心'
    }

    # 收集所有技能词
    for line in lines:
        for kw in skill_keywords:
            if kw in line:
                skills.append(kw)

    # 去重并保留顺序
    unique_skills = []
    for s in skills:
        if s not in unique_skills:
            unique_skills.append(s)

    # 取前4个最核心的技能
    core_skills = unique_skills[:4]
    skills_str = "、".join(core_skills) if core_skills else ""

    parts = []
    if skills_str:
        parts.append(skills_str + ("等能力" if len(core_skills) >= 2 else ""))

    if parts:
        return "，".join(parts)
    else:
        return text[:50] + "..." if len(text) > 50 else text


if __name__ == "__main__":
    df = pd.read_csv('D:\yige\python code\knowledge_graph\jobs.csv')
    # 对 requirements 列进行精简
    df['requirements_simplified'] = df['requirements'].apply(simplify_requirements)
    output_file = r'D:\yige\python code\knowledge_graph\jobs_simplified.csv'
    print(df[ 'requirements_simplified'])
    df.to_csv(output_file, index=False, encoding='utf-8-sig')