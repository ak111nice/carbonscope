"""
企业碳盘查自动化系统 v2.0
===========================
升级功能:
  - PDF 能源账单自动解析 (pdfplumber)
  - 产品碳足迹计算 (LCA/ISO 14067)
  - AI 智能分析 (异常检测 + 自然语言减排建议)
  - Streamlit Web 仪表盘

作者: 电子科学与技术应届生项目
标准: GB/T 32150-2025, ISO 14067
"""
import pandas as pd
import numpy as np
import os, json, re, sys
import warnings
from datetime import datetime
from io import StringIO
from typing import Tuple, Optional

warnings.filterwarnings("ignore")

# ============================================================
# 排放因子库
# ============================================================
EMISSION_FACTORS = {
    "电网电力":   {"单位": "tCO2/MWh",   "因子": 0.5810, "类型": "Scope 2"},
    "天然气":     {"单位": "tCO2/万m³",  "因子": 21.62,  "类型": "Scope 1"},
    "烟煤":       {"单位": "tCO2/吨",    "因子": 2.53,   "类型": "Scope 1"},
    "柴油":       {"单位": "tCO2/吨",    "因子": 3.16,   "类型": "Scope 1"},
    "汽油":       {"单位": "tCO2/吨",    "因子": 2.99,   "类型": "Scope 1"},
    # 工艺排放
    "水泥熟料":   {"单位": "tCO2/吨熟料", "因子": 0.535,  "类型": "Scope 1"},
    "钢铁(吨钢)": {"单位": "tCO2/吨钢",   "因子": 1.80,   "类型": "Scope 1"},
}

MATERIAL_FACTORS = {
    # ISO 14067 常用原材料碳足迹因子 (kgCO2e/kg)
    "钢材": 2.3, "铝材": 11.5, "铜": 5.8, "塑料": 3.1,
    "玻璃": 1.2, "水泥": 0.9, "木材": 0.3, "纸板": 0.8,
    "硅": 45.0, "锂电池(kg)": 120.0, "芯片(kg)": 2000.0,
}

TRANSPORT_FACTORS = {
    # kgCO2e per ton-km
    "海运": 0.015, "铁路": 0.025, "公路": 0.12, "空运": 0.60,
}

# ============================================================
# 1. PDF 能源账单解析器
# ============================================================
def parse_energy_pdf(pdf_path: str) -> pd.DataFrame:
    """
    解析文字版能源账单 PDF，提取可用于碳核算的活动数据。

    该函数同时尝试表格提取和正文正则匹配，适配电费单、燃气单、
    煤耗单等常见企业凭证。输出字段统一为日期、部门、能源类型、
    活动数据和数据单位，便于后续直接进入 Scope 1/2 核算。

    注意：扫描版 PDF 需要先 OCR；提取结果应保留人工复核环节，
    避免金额、编号等非能耗数字误入账。
    """
    import pdfplumber

    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            text = page.extract_text() or ""

            # 策略1: 提取表格数据
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or not any(row):
                        continue
                    row_str = " ".join([str(c) if c else "" for c in row])
                    parsed = _parse_energy_line(row_str)
                    if parsed:
                        rows.append(parsed)

            # 策略2: 从文本中正则提取能耗数据
            patterns = [
                # "用电量: 1200 MWh" / "2025年1月 电力 1200"
                (r"(电力|用电|电|Electricity|Consumption).*?(\d+\.?\d*)\s*(MWh|兆瓦时|kWh|千瓦时|度)", "电网电力"),
                # "天然气 8.5 万m³" / "Natural Gas Usage: 9.8 x 10000 m3"
                (r"(天然气|用气|燃气|Natural\s*Gas|Gas\s*Usage).*?(\d+\.?\d*)\s*(万m³|万立方米|m³|立方米|x\s*10000\s*m3)", "天然气"),
                # "煤炭 45 吨" / "Coal Consumption: 55 tons"
                (r"(煤炭|用煤|燃煤|烟煤|Coal\s*Consumption|Coal).*?(\d+\.?\d*)\s*(吨|t|tons)", "烟煤"),
                # "柴油 3.5 吨" / "Diesel Fuel: 4.8 tons"
                (r"(柴油|Diesel\s*Fuel|Diesel).*?(\d+\.?\d*)\s*(吨|t|tons|升|L)", "柴油"),
                # "汽油 1.8 吨" / "Gasoline: 2.3 tons"
                (r"(汽油|Gasoline).*?(\d+\.?\d*)\s*(吨|t|tons|升|L)", "汽油"),
            ]
            for pattern, fuel_type in patterns:
                for match in re.finditer(pattern, text):
                    val = float(match.group(2))
                    unit = match.group(3)
                    # 单位换算
                    if unit in ("kWh", "千瓦时", "度"):
                        val = val / 1000  # kWh -> MWh
                        unit = "MWh"
                    elif unit in ("万m³", "万立方米"):
                        unit = "万m³"
                    elif unit in ("m³", "立方米"):
                        val = val / 10000
                        unit = "万m³"
                    elif unit in ("吨", "t"):
                        unit = "吨"
                    elif unit in ("升", "L"):
                        if fuel_type == "柴油":
                            val = val * 0.85 / 1000  # L -> ton
                        else:
                            val = val * 0.74 / 1000
                        unit = "吨"
                    rows.append({
                        "日期": datetime.now().strftime("%Y-%m"),
                        "部门": "生产车间",
                        "能源类型": fuel_type,
                        "活动数据": round(val, 3),
                        "数据单位": unit,
                    })

    pdf.close()
    return pd.DataFrame(rows)


def _parse_energy_line(text: str) -> Optional[dict]:
    """
    从表格行或文本行中识别能源类型和活动数据。

    返回 None 表示该行不包含可识别的能源数据；返回 dict 时，
    结果可直接拼接到核算 DataFrame。这里使用规则匹配，便于
    解释、审计和面试展示。
    """
    text_lower = text.lower()
    mapping = [
        ("电", "电网电力", "MWh"),
        ("天然气", "天然气", "万m³"),
        ("煤", "烟煤", "吨"),
        ("柴油", "柴油", "吨"),
        ("汽油", "汽油", "吨"),
    ]
    for keyword, fuel, unit in mapping:
        if keyword in text_lower:
            nums = re.findall(r'(\d+\.?\d*)', text)
            if nums:
                return {
                    "日期": datetime.now().strftime("%Y-%m"),
                    "部门": "生产车间",
                    "能源类型": fuel,
                    "活动数据": float(nums[0]),
                    "数据单位": unit,
                }
    return None


# ============================================================
# 2. 产品碳足迹计算 (LCA / ISO 14067)
# ============================================================
def calculate_product_footprint(
    product_name: str,
    materials: dict,        # {"钢材": 50, "铝材": 10}  单位: kg
    energy_consumption: dict,  # {"电网电力": 100}  单位: MWh
    transport: dict,        # {"type": "公路", "distance_km": 500, "weight_ton": 5}
    production_waste_pct: float = 5.0,
) -> dict:
    """计算单个产品的全生命周期碳足迹 (Cradle-to-Gate)"""
    results = {"产品名称": product_name, "明细": {}}

    # Stage A: 原材料获取
    total_material = 0
    for mat, kg in materials.items():
        factor = MATERIAL_FACTORS.get(mat, 1.0)
        co2 = kg * factor / 1000  # kgCO2 -> tCO2
        results["明细"][f"原材料-{mat}"] = {
            "用量": f"{kg} kg", "排放因子": f"{factor} kgCO2/kg", "碳排放": round(co2, 4)
        }
        total_material += co2

    # Stage B: 生产制造(能源消耗)
    total_energy = 0
    for fuel, amount in energy_consumption.items():
        info = EMISSION_FACTORS.get(fuel)
        if info:
            co2 = amount * info["因子"]
            results["明细"][f"生产能耗-{fuel}"] = {
                "用量": f"{amount} MWh" if fuel == "电网电力" else f"{amount} 万m³",
                "排放因子": f"{info['因子']} {info['单位']}",
                "碳排放": round(co2, 4),
            }
            total_energy += co2

    # Stage C: 运输
    transport_co2 = 0
    if transport:
        t_type = transport.get("type", "公路")
        factor = TRANSPORT_FACTORS.get(t_type, 0.12)
        co2 = transport["distance_km"] * transport["weight_ton"] * factor / 1000
        results["明细"][f"运输-{t_type}"] = {
            "距离": f"{transport['distance_km']} km",
            "重量": f"{transport['weight_ton']} 吨",
            "排放因子": f"{factor} kgCO2/吨·km",
            "碳排放": round(co2, 4),
        }
        transport_co2 = co2

    # 废品率加成
    waste_factor = 1 + production_waste_pct / 100
    total = (total_material + total_energy + transport_co2) * waste_factor

    results.update({
        "原材料碳排放(tCO2)": round(total_material, 4),
        "生产能耗碳排放(tCO2)": round(total_energy, 4),
        "运输碳排放(tCO2)": round(transport_co2, 4),
        "废品率加成": f"{production_waste_pct}%",
        "总碳足迹(tCO2/单位产品)": round(total, 4),
    })
    return results


# ============================================================
# 3. AI 智能分析引擎
# ============================================================
def detect_anomalies(df: pd.DataFrame) -> list:
    """自动检测异常排放（Z-score 方法）"""
    alerts = []
    if len(df) < 3:
        alerts.append("⚠️ 数据点不足3个，无法进行异常检测（需至少3个月数据）")
        return alerts

    for fuel_type in df["能源类型"].unique():
        subset = df[df["能源类型"] == fuel_type]["碳排放(tCO2)"]
        if len(subset) < 3:
            continue
        mean = subset.mean()
        std = subset.std()
        if std == 0:
            continue

        for idx in subset.index:
            val = subset[idx]
            z_score = (val - mean) / std
            if abs(z_score) > 2.0:
                row = df.loc[idx]
                direction = "⬆ 偏高" if z_score > 0 else "⬇ 偏低"
                alerts.append(
                    f"🔴 异常: {row['部门']} {row['能源类型']} "
                    f"({row.get('日期','?')}) = {val:.2f} tCO2, "
                    f"Z-score={z_score:.1f} ({direction}), "
                    f"月均值={mean:.2f}"
                )
    return alerts


def generate_recommendations(df: pd.DataFrame) -> list:
    """生成自然语言的减排建议"""
    recs = []
    by_fuel = df.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values(ascending=False)

    top = by_fuel.index[0] if len(by_fuel) > 0 else None
    pct = by_fuel.iloc[0] / by_fuel.sum() * 100 if by_fuel.sum() > 0 else 0

    if top == "电网电力" and pct > 50:
        recs.append(
            f"🎯 最大排放源是「电网电力」(占 {pct:.0f}%)。建议优先考虑:\n"
            "   ① 安装屋顶分布式光伏，自发自用比例目标 >30%\n"
            "   ② 采购绿证(GEC)或参与绿电交易，锁定固定电价\n"
            "   ③ 排查空压机、制冷系统等高耗能设备，加装变频器"
        )
    elif top == "天然气":
        recs.append(
            f"🎯 最大排放源是「天然气」(占 {pct:.0f}%)。建议:\n"
            "   ① 评估电锅炉替代燃气锅炉的可行性\n"
            "   ② 安装余热回收装置，天然气利用率可提升15-25%"
        )
    elif top == "烟煤":
        recs.append(
            f"🎯 最大排放源是「烟煤」(占 {pct:.0f}%)。这是减排优先级最高的能源:\n"
            "   ① 评估天然气替代方案（每替代1吨煤可减排约0.6 tCO2）\n"
            "   ② 如果无法替代，至少换高效煤粉锅炉（热效率从65%→90%）"
        )

    # 总排放量合规判断
    total = by_fuel.sum()
    if total > 26000:
        recs.append(
            "⚖️ 年排放 >26,000 tCO2：已触发全国碳市场纳入门槛。\n"
            "   须聘请第三方核查机构(DOE)出具核查声明，并在交易所完成年度履约。"
        )
    elif total > 5000:
        recs.append(
            "📈 年排放 5,000-26,000 tCO2：预计2027年碳市场扩容后将被纳入。\n"
            "   建议即日起建立碳排放数据管理系统，提前准备MRV能力。"
        )

    return recs


# ============================================================
# 4. 可视化引擎 (matplotlib)
# ============================================================
def plot_dashboard(df: pd.DataFrame, output_path: str = "dashboard.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # 全局注册中文字体
    try:
        fm.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
        matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
        matplotlib.rcParams['axes.unicode_minus'] = False
    except:
        pass

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("企业碳盘查仪表盘", fontsize=16, fontweight="bold")

    # 1. Scope 1/2 饼图
    ax1 = axes[0, 0]
    by_scope = df.groupby(
        df["能源类型"].apply(lambda x: EMISSION_FACTORS.get(x, {}).get("类型", "Scope 1"))
    )["碳排放(tCO2)"].sum()
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    wedges, texts, autotexts = ax1.pie(
        by_scope.values, labels=by_scope.index, autopct="%1.1f%%",
        colors=colors, startangle=90, explode=[0.03]*len(by_scope)
    )
    ax1.set_title("Scope 1 vs Scope 2 排放占比", fontsize=12)

    # 2. 按能源类型柱状图
    ax2 = axes[0, 1]
    by_fuel = df.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values()
    bars = ax2.barh(by_fuel.index, by_fuel.values, color="#FF6B6B", edgecolor="white")
    for bar, val in zip(bars, by_fuel.values):
        ax2.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                 f"{val:.0f}", va="center", fontsize=9)
    ax2.set_title("各能源类型碳排放 (tCO2)", fontsize=12)
    ax2.set_xlabel("tCO2")

    # 3. 月度趋势
    ax3 = axes[1, 0]
    if "日期" in df.columns:
        monthly = df.groupby(["日期", "能源类型"])["碳排放(tCO2)"].sum().unstack(fill_value=0)
        if not monthly.empty:
            monthly.plot(kind="line", marker="o", ax=ax3)
    ax3.set_title("月度排放趋势", fontsize=12)
    ax3.set_ylabel("tCO2")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # 4. 部门对比
    ax4 = axes[1, 1]
    if "部门" in df.columns:
        dept = df.groupby("部门")["碳排放(tCO2)"].sum().sort_values()
        dept.plot(kind="barh", ax=ax4, color="#4ECDC4", edgecolor="white")
    ax4.set_title("部门排放对比", fontsize=12)
    ax4.set_xlabel("tCO2")

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"📊 仪表盘已保存: {output_path}")


# ============================================================
# 5. 全流程报告生成
# ============================================================
def calculate_emissions(df: pd.DataFrame) -> Tuple[pd.DataFrame, float, float]:
    """碳排放 = 活动数据 × 排放因子"""
    rows, s1, s2 = [], 0, 0
    for _, r in df.iterrows():
        info = EMISSION_FACTORS.get(r["能源类型"])
        if not info:
            continue
        e = r["活动数据"] * info["因子"]
        rows.append({
            "日期": r.get("日期", "N/A"), "部门": r.get("部门", "全厂"),
            "能源类型": r["能源类型"], "活动数据": r["活动数据"],
            "数据单位": r.get("数据单位", ""), "排放因子": info["因子"],
            "排放因子单位": info["单位"], "碳排放(tCO2)": round(e, 3),
            "排放范围": info["类型"],
        })
        if "Scope 2" in info["类型"]:
            s2 += e
        else:
            s1 += e
    return pd.DataFrame(rows), s1, s2


def full_report(df: pd.DataFrame, product_footprint: dict = None) -> str:
    results, s1, s2 = calculate_emissions(df)
    total = s1 + s2

    # AI 分析
    anomalies = detect_anomalies(results)
    recs = generate_recommendations(results)

    r = f"""\
{'='*60}
       企业温室气体排放核算报告 v2.0
       标准: GB/T 32150-2025 | ISO 14067
       生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

一、排放总量
{'─'*40}
  Scope 1 (直接排放):  {s1:>12.3f} tCO2e
  Scope 2 (间接排放):  {s2:>12.3f} tCO2e
  {'─'*40}
  总计:                 {total:>12.3f} tCO2e

  等效: {total*1000:.0f}kg CO2 ≈ {total/2.3:.0f}辆轿车年排放 ≈ {total/0.06:.0f}棵树年吸收

二、排放结构
{'─'*40}
"""
    by_fuel = results.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values(ascending=False)
    for fuel, val in by_fuel.items():
        pct = val / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        r += f"  {fuel:<12} {val:>8.3f} t  ({pct:>5.1f}%) {bar}\n"

    r += f"\n三、AI 异常检测\n{'─'*40}\n"
    r += "\n".join(anomalies) if anomalies else "  ✅ 未检测到异常排放\n"

    r += f"\n四、AI 减排建议\n{'─'*40}\n"
    r += "\n\n".join(recs) if recs else "  (数据不足,无法生成建议)\n"

    # 产品碳足迹
    if product_footprint:
        r += f"\n五、产品碳足迹 (ISO 14067)\n{'─'*40}\n"
        r += f"  产品: {product_footprint.get('产品名称', 'N/A')}\n"
        for key, val in product_footprint.items():
            if key not in ("明细", "产品名称") and isinstance(val, (int, float)):
                r += f"  {key}: {val:.4f} tCO2\n"
        r += f"\n  详细分项:\n"
        for stage, detail in product_footprint.get("明细", {}).items():
            r += f"    {stage}: {detail['碳排放']:.4f} tCO2\n"

    r += f"\n{'='*60}\n"
    return r


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  企业碳盘查自动化系统 v2.0")
    print("  python carbon_v2.py            → Streamlit 仪表盘")
    print("  python carbon_v2.py csv FILE  → CSV 模式")
    print("  python carbon_v2.py pdf FILE  → PDF 解析模式")
    print("=" * 50)

    if len(sys.argv) < 2:
        # 默认: 启动 Streamlit
        print("\n启动 Streamlit 仪表盘...")
        print("请在终端运行: streamlit run carbon_v2.py")
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "csv" and len(sys.argv) >= 3:
        path = sys.argv[2]
        df = pd.read_csv(path)
        print(parse_energy_pdf.__doc__)  # nop
        results, s1, s2 = calculate_emissions(df)
        report = full_report(df)
        out = os.path.splitext(path)[0] + "_report.txt"
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
        print(report)
        plot_dashboard(results, os.path.splitext(path)[0] + "_dashboard.png")

    elif mode == "pdf" and len(sys.argv) >= 3:
        path = sys.argv[2]
        print(f"解析 PDF: {path}")
        df = parse_energy_pdf(path)
        if df.empty:
            print("⚠️ 未提取到能耗数据，请检查 PDF 格式")
        else:
            print(f"提取到 {len(df)} 条数据")
            df.to_csv("parsed_energy.csv", index=False)
            report = full_report(df)
            print(report)
            with open("parsed_report.txt", "w", encoding="utf-8") as f:
                f.write(report)

    elif mode == "product":
        # 产品碳足迹示例
        fp = calculate_product_footprint(
            "智能手机",
            materials={"钢材": 0.05, "铝材": 0.03, "塑料": 0.02, "芯片(kg)": 0.01},
            energy_consumption={"电网电力": 0.1},
            transport={"type": "公路", "distance_km": 800, "weight_ton": 0.0002},
        )
        print(json.dumps(fp, indent=2, ensure_ascii=False))

    else:
        print("用法: python carbon_v2.py csv|pdf|product <文件路径>")
