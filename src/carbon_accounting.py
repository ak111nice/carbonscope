"""
AI 自动碳盘查系统 Demo
输入：工厂能源数据（电/天然气/煤/油）的 Excel 或 CSV
输出：自动计算碳排放总量 + 生成报告 + 可视化

基于 GB/T 32150-2025 标准
排放因子来源：国家发改委《省级温室气体清单编制指南》
"""
import pandas as pd
import os
import json
from datetime import datetime

# ============================================
# 1. 排放因子库（国家发改委发布的标准值）
# ============================================
EMISSION_FACTORS = {
    # 燃料燃烧排放因子
    "电网电力": {
        "单位": "tCO2/MWh",
        "排放因子": 0.5810,  # 2024年全国电网平均排放因子
        "类型": "间接排放(Scope 2)"
    },
    "天然气": {
        "单位": "tCO2/万m³",
        "排放因子": 21.62,
        "类型": "直接排放(Scope 1)"
    },
    "烟煤": {
        "单位": "tCO2/吨",
        "排放因子": 2.53,
        "类型": "直接排放(Scope 1)"
    },
    "柴油": {
        "单位": "tCO2/吨",
        "排放因子": 3.16,
        "类型": "直接排放(Scope 1)"
    },
    "汽油": {
        "单位": "tCO2/吨",
        "排放因子": 2.99,
        "类型": "直接排放(Scope 1)"
    },
    # 工艺过程排放
    "水泥熟料": {
        "单位": "tCO2/吨熟料",
        "排放因子": 0.535,
        "类型": "工艺排放(Scope 1)"
    },
    "钢铁(吨钢)": {
        "单位": "tCO2/吨钢",
        "排放因子": 1.80,
        "类型": "工艺排放(Scope 1)"
    },
}

# 全球变暖潜势值 (GWP, 基于 IPCC AR6)
GWP = {
    "CO2": 1,
    "CH4": 28,
    "N2O": 265,
}


# ============================================
# 2. 碳核算引擎（每个工程师都能看懂）
# ============================================
def load_data(filepath):
    """加载能源数据"""
    df = pd.read_csv(filepath)
    return df


def calculate_emissions(df):
    """
    核心公式: 碳排放 = 活动数据 × 排放因子
    """
    results = []
    total_scope1 = 0  # 直接排放
    total_scope2 = 0  # 间接排放

    for _, row in df.iterrows():
        activity = row["活动数据"]        # 比如：用了1000度电
        fuel_type = row["能源类型"]       # 比如：电网电力
        unit = row["数据单位"]            # 比如：MWh

        factor_info = EMISSION_FACTORS.get(fuel_type)
        if not factor_info:
            print(f"⚠️ 未找到排放因子: {fuel_type}")
            continue

        factor = factor_info["排放因子"]
        scope = factor_info["类型"]

        # 实际计算
        emission = activity * factor

        record = {
            "日期": row.get("日期", "N/A"),
            "部门": row.get("部门", "全厂"),
            "能源类型": fuel_type,
            "活动数据": activity,
            "数据单位": unit,
            "排放因子": factor,
            "排放因子单位": factor_info["单位"],
            "碳排放(tCO2)": round(emission, 3),
            "排放范围": scope,
        }
        results.append(record)

        if "Scope 1" in scope:
            total_scope1 += emission
        else:
            total_scope2 += emission

    return pd.DataFrame(results), total_scope1, total_scope2


def generate_report(results_df, total_scope1, total_scope2):
    """生成碳盘查报告"""
    total = total_scope1 + total_scope2

    report = f"""
{'='*60}
          企业温室气体排放核算报告
          基于 GB/T 32150-2025
{'='*60}

报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

一、排放总量
{'─'*40}
  直接排放(Scope 1):  {total_scope1:>10.3f} tCO2e
  间接排放(Scope 2):  {total_scope2:>10.3f} tCO2e
  {'─'*40}
  总排放量:           {total:>10.3f} tCO2e

  等效于：
  ▸ {total * 1000:.0f} 公斤 CO2
  ▸ 约 {total / 2.3:.0f} 辆家用轿车一年的排放
  ▸ 约需要 {total / 0.06:.0f} 棵树生长一年来吸收

二、排放明细
{'─'*40}
"""
    for _, row in results_df.iterrows():
        report += f"""
  部门: {row['部门']} | {row['能源类型']}
    活动数据: {row['活动数据']} {row['数据单位']}
    排放因子: {row['排放因子']} {row['排放因子单位']}
    碳排放:   {row['碳排放(tCO2)']:.3f} tCO2 ({row['排放范围']})
"""

    report += f"""
三、排放结构
{'─'*40}
"""
    # 按能源类型汇总
    by_fuel = results_df.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values(ascending=False)
    for fuel, val in by_fuel.items():
        pct = val / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 2)
        report += f"  {fuel:<12} {val:>8.3f} t  ({pct:>5.1f}%) {bar}\n"

    report += f"""
四、合规建议（AI 辅助生成）
{'─'*40}
"""
    # 智能建议
    if total > 26000:
        report += "  ⚠️ 年排放超过 26,000 吨，已触发全国碳市场纳入门槛，须强制履约。\n"
    elif total > 5000:
        report += "  ⚡ 年排放在 5,000-26,000 吨之间，建议主动建立碳管理体系，应对未来扩容。\n"
    else:
        report += "  📋 年排放低于 5,000 吨，暂不强制履约，但建议提前建立碳核算能力。\n"

    # 最大排放源
    top_source = by_fuel.index[0]
    report += f"  🎯 最大排放源是「{top_source}」，占总排放的 {by_fuel.iloc[0]/total*100:.1f}%。\n"
    report += f"     建议优先对该能源类型进行节能改造或替代。\n"

    report += f"""
{'='*60}
  本报告由 AI 自动碳盘查系统生成
  排放因子来源：国家发改委《省级温室气体清单编制指南》
  核算标准：GB/T 32150-2025
{'='*60}
"""
    return report


# ============================================
# 3. 入口
# ============================================
if __name__ == "__main__":
    import sys

    data_file = sys.argv[1] if len(sys.argv) > 1 else "sample_energy_data.csv"
    report_file = sys.argv[2] if len(sys.argv) > 2 else "carbon_report.txt"

    if not os.path.exists(data_file):
        print(f"❌ 文件不存在: {data_file}")
        sys.exit(1)

    # 加载数据
    df = load_data(data_file)
    print(f"📂 加载 {len(df)} 条能源数据\n")

    # 核算
    results_df, s1, s2 = calculate_emissions(df)

    # 生成报告
    report = generate_report(results_df, s1, s2)

    # 输出
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\n📄 报告已保存至: {report_file}")
