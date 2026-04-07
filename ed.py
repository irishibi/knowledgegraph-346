import pandas as pd

standard_mapping = {
    "Java开发工程师": ["Java开发工程师"],
    "后端开发工程师": ["后端开发工程师", "后端开发"],
    "前端开发工程师": ["前端开发工程师", "前端开发"],
    "Python开发工程师": ["Python开发工程师", "Python工程师"],
    "全栈开发工程师": ["全栈开发工程师"],
    "算法工程师": ["算法工程师", "机器学习工程师", "深度学习工程师"],
    "数据分析师": ["数据分析师"],
    "数据工程师": ["数据工程师"],
    "运维工程师": ["运维工程师", "DevOps工程师"],
    "测试工程师": ["测试工程师"],
    "架构师": ["架构师"],
    "技术总监": ["技术总监"],
    "产品经理": ["产品经理", "产品总监"],
    "产品助理": ["产品助理"],
    "UI设计师": ["UI设计师", "UI设计"],
    "UX设计师": ["UX设计师", "UX设计", "交互设计"],
    "视觉设计师": ["视觉设计", "视觉设计师"],
    "平面设计师": ["平面设计", "平面设计师"],
    "动效设计师": ["动效设计师"],
    "3D设计师": ["3D设计师"],
    "用户研究": ["用户研究"],
    "市场经理": ["市场经理"],
    "市场专员": ["市场专员"],
    "品牌经理": ["品牌经理"],
    "公关经理": ["公关经理"],
    "销售经理": ["销售经理"],
    "媒介专员": ["媒介专员"],
    "运营经理": ["运营经理"],
    "运营专员": ["运营专员"],
    "用户运营": ["用户运营"],
    "内容运营": ["内容运营"],
    "活动运营": ["活动运营"],
    "新媒体运营": ["新媒体运营"],
    "数据运营": ["数据运营"],
    "人力资源": ["人力资源", "HR"],
    "行政专员": ["行政专员", "行政助理"],
    "财务专员": ["财务专员"],
    "会计": ["会计"],
    "出纳": ["出纳"],
    "法务专员": ["法务专员"],
    "BD经理": ["BD经理", "商务拓展"]
}

# 构建反向映射：同义词 -> 标准职位
synonym_to_std = {}
for std, syns in standard_mapping.items():
    for syn in syns:
        synonym_to_std[syn] = std

def disambiguate_job_title(raw: str) -> str:
    """
    对单个职位名称进行消歧，返回标准化后的名称
    """
    if not isinstance(raw, str):
        return raw
    raw = raw.strip()
    if raw in synonym_to_std:
        return synonym_to_std[raw]
    return raw

input_file = r'D:\yige\python code\knowledge_graph\jobs_simplified.csv'
df = pd.read_csv(input_file, encoding='utf-8')

print("CSV 文件中的列名：", df.columns.tolist())

job_col = 'job_title'
if job_col not in df.columns:
    raise ValueError(f"未找到列 '{job_col}'，请检查 CSV 文件中的列名。")

df['job_title_standardized'] = df[job_col].apply(disambiguate_job_title)

output_file = r'D:\yige\python code\knowledge_graph\jobs_standardized.csv'
df.to_csv(output_file, index=False, encoding='utf-8-sig')   # utf-8-sig 便于 Excel 打开

