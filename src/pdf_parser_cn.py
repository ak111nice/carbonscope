"""
PDF 能源账单解析引擎 v2 — 中文+表格+多页支持
==============================================
用途：
  从中文 PDF 格式的电费单、燃气单、燃煤账单中自动提取能耗数据。
  支持 pdfplumber 表格提取 + 中文正则文本匹配双通道。

使用示例：
  >>> from pdf_parser_cn import parse_pdf_full, parse_chinese_text
  >>> df = parse_pdf_full("电费单.pdf")
  >>> # 或纯文本快速测试
  >>> df = parse_chinese_text("用电量: 1350 MWh, 天然气: 10.2 万m³")

匹配规则：
  - "用电量/电力/电费" + 数字 + "MWh/kWh/度"   → 电网电力
  - "天然气/用气/燃气" + 数字 + "万m³/立方米"    → 天然气
  - "煤炭/用煤/燃煤/烟煤" + 数字 + "吨/t"        → 烟煤
  - "柴油" + 数字 + "吨/t/升"                   → 柴油
  - "汽油" + 数字 + "吨/t/升"                   → 汽油

限制：
  - 只提取五种主要能源类型
  - 单位自动换算（kWh→MWh, m³→万m³, 升→吨）
  - 同一能源类型只保留首次匹配值（去重）
"""
import re
from io import StringIO
from datetime import datetime
import pandas as pd
from typing import Optional

# 中文能源关键词匹配规则
CN_PATTERNS = [
    # (正则, 能源类型, 默认单位)
    (r"(用电量|电力|电费|用电){:—=，,。\.\s]*(\d+\.?\d*)\s*(MWh|兆瓦时|kWh|千瓦时|万度|度)", "电网电力", "MWh"),
    (r"(天然气|用气|燃气|气费){:—=，,。\.\s]*(\d+\.?\d*)\s*(万m³|万立方米|m³|立方米|立方)", "天然气", "万m³"),
    (r"(煤炭|用煤|燃煤|烟煤|原煤){:—=，,。\.\s]*(\d+\.?\d*)\s*(万吨|吨|t)", "烟煤", "吨"),
    (r"(柴油|用油|燃油){:—=，,。\.\s]*(\d+\.?\d*)\s*(吨|t|升|L|公升)", "柴油", "吨"),
    (r"(汽油){:—=，,。\.\s]*(\d+\.?\d*)\s*(吨|t|升|L|公升)", "汽油", "吨"),
    (r"(液化气|LPG|液化石油气){:—=，,。\.\s]*(\d+\.?\d*)\s*(吨|t|kg|千克|公斤)", "液化石油气", "吨"),
]

# 单位换算表 → 标准单位
UNIT_CONVERT = {
    "kWh": ("MWh", 0.001),
    "千瓦时": ("MWh", 0.001),
    "度": ("MWh", 0.001),
    "万度": ("MWh", 10),
    "m³": ("万m³", 0.0001),
    "立方米": ("万m³", 0.0001),
    "立方": ("万m³", 0.0001),
    "万吨": ("吨", 10000),
    "t": ("吨", 1),
    "升": ("吨", 0.00085),
    "L": ("吨", 0.00085),
    "公升": ("吨", 0.00085),
    "kg": ("吨", 0.001),
    "千克": ("吨", 0.001),
    "公斤": ("吨", 0.001),
}


def parse_chinese_text(text: str) -> pd.DataFrame:
    """从中文文本提取能耗数据"""
    rows = []
    for pattern, fuel_type, default_unit in CN_PATTERNS:
        for match in re.finditer(pattern, text):
            val = float(match.group(2))
            unit = match.group(3) if len(match.groups()) >= 3 else default_unit

            # 单位换算
            std_unit, factor = UNIT_CONVERT.get(unit, (unit, 1))
            val = val * factor

            # 去重（同一能源类型+接近的数据值）
            duplicate = False
            for existing in rows:
                if existing["能源类型"] == fuel_type and abs(existing["活动数据"] - val) < 0.01:
                    duplicate = True
                    break
            if not duplicate:
                rows.append({
                    "日期": datetime.now().strftime("%Y-%m"),
                    "部门": "生产车间",
                    "能源类型": fuel_type,
                    "活动数据": round(val, 3),
                    "数据单位": std_unit,
                    "来源": "PDF自动提取",
                })
    return pd.DataFrame(rows)


def parse_tables(tables: list) -> pd.DataFrame:
    """从 pdfplumber 提取的表格中识别能耗行"""
    rows = []
    keywords = {
        "电": "电网电力", "电力": "电网电力", "用电": "电网电力",
        "气": "天然气", "天然气": "天然气", "燃气": "天然气",
        "煤": "烟煤", "煤炭": "烟煤", "烟煤": "烟煤",
        "柴油": "柴油", "汽油": "汽油",
    }

    for table in tables:
        if not table:
            continue
        for row in table:
            if not row or not any(row):
                continue
            row_str = " ".join([str(c) if c else "" for c in row])

            for keyword, fuel_type in keywords.items():
                if keyword in row_str:
                    nums = re.findall(r'(\d+\.?\d*)', row_str)
                    if nums:
                        rows.append({
                            "日期": datetime.now().strftime("%Y-%m"),
                            "部门": "生产车间",
                            "能源类型": fuel_type,
                            "活动数据": float(nums[0]),
                            "数据单位": "未指定",
                            "来源": "PDF表格提取",
                        })
                        break
    return pd.DataFrame(rows)


def parse_pdf_full(pdf_path: str) -> pd.DataFrame:
    """完整解析 PDF —— 表格 + 文本双通道"""
    try:
        import pdfplumber
    except ImportError:
        return pd.DataFrame()

    all_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # 通道1：表格
            tables = page.extract_tables()
            if tables:
                df_tables = parse_tables(tables)
                if not df_tables.empty:
                    all_rows.append(df_tables)

            # 通道2：中文文本正则
            text = page.extract_text() or ""
            if text.strip():
                df_text = parse_chinese_text(text)
                if not df_text.empty:
                    all_rows.append(df_text)

    pdf.close()

    if not all_rows:
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    result.drop_duplicates(subset=["能源类型", "活动数据"], inplace=True)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"解析: {path}")
        df = parse_pdf_full(path)
        if df.empty:
            print("未提取到数据")
        else:
            print(f"\n提取到 {len(df)} 条:\n{df.to_string()}")
    else:
        # 自测：模拟一段中文电费文本
        sample = """
        客户名称：XX制造有限公司
        结算月份：2025年7月
        当期用电量：1350 MWh（兆瓦时）
        其中峰时：680 MWh，平时：420 MWh，谷时：250 MWh
        天然气用气量：10.2 万立方米
        煤炭消耗：52 吨
        柴油用量：5.1 吨
        """
        df = parse_chinese_text(sample)
        print("中文文本解析测试:")
        print(df.to_string())
