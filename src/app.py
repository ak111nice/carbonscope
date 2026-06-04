"""
Streamlit Web 仪表盘 —— 企业碳盘查自动化系统
运行: streamlit run app.py
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
import streamlit as st
import pandas as pd
import tempfile
from carbon_v2 import (
    EMISSION_FACTORS, MATERIAL_FACTORS, TRANSPORT_FACTORS,
    calculate_emissions, full_report, detect_anomalies,
    generate_recommendations, parse_energy_pdf,
    calculate_product_footprint, plot_dashboard,
)

st.set_page_config(page_title="碳盘查系统 v2.0", page_icon="🌍", layout="wide")
st.title("🌍 企业碳盘查自动化系统 v2.0")
st.caption("标准: GB/T 32150-2025 | ISO 14067 | 电子+AI 交叉项目")

tab1, tab2, tab3, tab4 = st.tabs(["📊 碳排放核算", "📄 PDF 解析", "🏭 产品碳足迹", "📋 完整报告"])

# ==================== Tab 1: 碳排放核算 ====================
with tab1:
    st.header("碳排放核算")

    uploaded = st.file_uploader("上传能源数据 (CSV)", type="csv")

    if uploaded:
        df = pd.read_csv(uploaded)
    else:
        from io import StringIO
        df = pd.read_csv(StringIO("""\
日期,部门,能源类型,活动数据,数据单位
2025-01,生产车间,电网电力,1200,MWh
2025-01,生产车间,天然气,8.5,万m³
2025-01,生产车间,烟煤,45,吨
2025-01,办公楼,电网电力,300,MWh
"""))
        st.info("使用示例数据。上传你自己的 CSV 替换。")

    st.subheader("原始数据")
    st.dataframe(df, use_container_width=True)

    results, s1, s2 = calculate_emissions(df)
    total = s1 + s2

    col1, col2, col3 = st.columns(3)
    col1.metric("🔴 Scope 1 (直接)", f"{s1:.1f} tCO2")
    col2.metric("🟡 Scope 2 (间接)", f"{s2:.1f} tCO2")
    col3.metric("🌍 总排放", f"{total:.1f} tCO2")

    st.subheader("排放结构")
    by_fuel = results.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values()
    st.bar_chart(by_fuel)

    # AI 分析
    st.subheader("🤖 AI 异常检测")
    anomalies = detect_anomalies(results)
    if anomalies:
        for a in anomalies:
            st.warning(a)
    else:
        st.success("✅ 未检测到异常排放")

    st.subheader("💡 AI 减排建议")
    for rec in generate_recommendations(results):
        st.markdown(rec)

    # 图表
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        plot_dashboard(results, f.name)
        st.image(f.name, caption="碳盘查仪表盘", use_container_width=True)

# ==================== Tab 2: PDF 解析 ====================
with tab2:
    st.header("PDF 能源账单解析")
    st.caption("上传 PDF 格式的电费单/燃气单/能源审计报告")

    pdf_file = st.file_uploader("上传 PDF", type="pdf")

    if pdf_file:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_file.read())
            pdf_path = f.name

        with st.spinner("解析中..."):
            try:
                parsed_df = parse_energy_pdf(pdf_path)
                if parsed_df.empty:
                    st.error("未提取到能源数据，请手动输入或检查 PDF 格式")
                else:
                    st.success(f"提取到 {len(parsed_df)} 条能源数据")
                    st.dataframe(parsed_df, use_container_width=True)

                    results, s1, s2 = calculate_emissions(parsed_df)
                    st.metric("总排放", f"{s1+s2:.1f} tCO2")
                    st.download_button(
                        "下载提取的 CSV",
                        parsed_df.to_csv(index=False).encode("utf-8-sig"),
                        "parsed_energy.csv",
                    )
            except Exception as e:
                st.error(f"解析失败: {e}")
            finally:
                os.unlink(pdf_path)

# ==================== Tab 3: 产品碳足迹 ====================
with tab3:
    st.header("产品碳足迹计算 (ISO 14067)")

    product_name = st.text_input("产品名称", "智能手机")

    st.subheader("原材料 (kg)")
    col1, col2, col3 = st.columns(3)
    materials = {}
    mat_names = list(MATERIAL_FACTORS.keys())
    for i, (col, name) in enumerate(zip(
        [col1, col1, col1, col2, col2, col2, col3, col3, col3],
        mat_names[:9]
    )):
        with col:
            val = st.number_input(f"{name}", min_value=0.0, value=0.0, step=0.01, key=f"mat_{name}")
            if val > 0:
                materials[name] = val

    st.subheader("生产能耗")
    ce1, ce2 = st.columns(2)
    with ce1:
        elec = st.number_input("电力 (MWh)", min_value=0.0, value=0.1, step=0.01)
    with ce2:
        gas = st.number_input("天然气 (万m³)", min_value=0.0, value=0.0, step=0.1)
    energy = {}
    if elec > 0:
        energy["电网电力"] = elec
    if gas > 0:
        energy["天然气"] = gas

    st.subheader("运输")
    ct1, ct2, ct3 = st.columns(3)
    with ct1:
        t_type = st.selectbox("运输方式", list(TRANSPORT_FACTORS.keys()))
    with ct2:
        dist = st.number_input("距离 (km)", min_value=0, value=800)
    with ct3:
        weight = st.number_input("运输重量 (吨)", min_value=0.0, value=0.0002, step=0.0001, format="%.4f")

    transport = {"type": t_type, "distance_km": dist, "weight_ton": weight} if dist > 0 else {}

    waste_pct = st.slider("生产废品率 (%)", 0.0, 20.0, 5.0)

    if st.button("计算碳足迹", type="primary"):
        result = calculate_product_footprint(product_name, materials, energy, transport, waste_pct)
        st.subheader("结果")
        st.metric("总碳足迹", f"{result['总碳足迹(tCO2/单位产品)']:.4f} tCO2/单位")

        # 分阶段
        stages = {
            "原材料": result["原材料碳排放(tCO2)"],
            "生产能耗": result["生产能耗碳排放(tCO2)"],
            "运输": result["运输碳排放(tCO2)"],
        }
        st.bar_chart(pd.Series(stages))

# ==================== Tab 4: 完整报告 ====================
with tab4:
    st.header("完整报告")
    if "results" in dir() and results is not None:
        report = full_report(df)
        st.code(report, language="text")
        st.download_button(
            "下载报告 (TXT)",
            report.encode("utf-8"),
            "carbon_report.txt",
        )
    else:
        st.info("请先在 Tab 1 上传数据或加载示例数据")
