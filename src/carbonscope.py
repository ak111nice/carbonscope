"""
CarbonScope 桌面版 — 双击即可运行的 Windows 窗口程序
基于 tkinter + matplotlib + Chart.js(通过内嵌浏览器)
"""
import sys
import os
import json
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# 确保能找到同级模块
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np

# ============================================================
# 数据层（同 carbon_v2.py 逻辑，精简版）
# ============================================================
EMISSION_FACTORS = {
    "电网电力": {"单位": "tCO2/MWh", "因子": 0.5810, "类型": "Scope 2"},
    "天然气":   {"单位": "tCO2/万m³", "因子": 21.62, "类型": "Scope 1"},
    "烟煤":     {"单位": "tCO2/吨", "因子": 2.53, "类型": "Scope 1"},
    "柴油":     {"单位": "tCO2/吨", "因子": 3.16, "类型": "Scope 1"},
    "汽油":     {"单位": "tCO2/吨", "因子": 2.99, "类型": "Scope 1"},
}

MATERIAL_FACTORS = {
    "钢材": 2.3, "铝材": 11.5, "铜": 5.8, "塑料": 3.1, "玻璃": 1.2,
    "水泥": 0.9, "木材": 0.3, "纸板": 0.8, "硅": 45, "锂电池(kg)": 120, "芯片(kg)": 2000,
}

TRANSPORT_FACTORS = {"海运": 0.015, "铁路": 0.025, "公路": 0.12, "空运": 0.60}

DEMO_DATA = pd.DataFrame([
    {"日期": "2025-01", "部门": "生产车间", "能源类型": "电网电力", "活动数据": 1200, "数据单位": "MWh"},
    {"日期": "2025-01", "部门": "生产车间", "能源类型": "天然气", "活动数据": 8.5, "数据单位": "万m³"},
    {"日期": "2025-01", "部门": "生产车间", "能源类型": "烟煤", "活动数据": 45, "数据单位": "吨"},
    {"日期": "2025-01", "部门": "办公楼", "能源类型": "电网电力", "活动数据": 300, "数据单位": "MWh"},
    {"日期": "2025-02", "部门": "生产车间", "能源类型": "电网电力", "活动数据": 1150, "数据单位": "MWh"},
    {"日期": "2025-02", "部门": "生产车间", "能源类型": "天然气", "活动数据": 9.1, "数据单位": "万m³"},
    {"日期": "2025-02", "部门": "生产车间", "能源类型": "烟煤", "活动数据": 42, "数据单位": "吨"},
    {"日期": "2025-02", "部门": "办公楼", "能源类型": "电网电力", "活动数据": 280, "数据单位": "MWh"},
    {"日期": "2025-02", "部门": "运输车队", "能源类型": "柴油", "活动数据": 3.5, "数据单位": "吨"},
    {"日期": "2025-03", "部门": "生产车间", "能源类型": "电网电力", "活动数据": 1300, "数据单位": "MWh"},
    {"日期": "2025-03", "部门": "生产车间", "能源类型": "天然气", "活动数据": 7.8, "数据单位": "万m³"},
    {"日期": "2025-03", "部门": "生产车间", "能源类型": "烟煤", "活动数据": 48, "数据单位": "吨"},
    {"日期": "2025-03", "部门": "办公楼", "能源类型": "电网电力", "活动数据": 310, "数据单位": "MWh"},
    {"日期": "2025-03", "部门": "运输车队", "能源类型": "柴油", "活动数据": 4.2, "数据单位": "吨"},
    {"日期": "2025-03", "部门": "运输车队", "能源类型": "汽油", "活动数据": 1.8, "数据单位": "吨"},
])


def calc_emissions(df):
    s1, s2, rows = 0, 0, []
    for _, r in df.iterrows():
        info = EMISSION_FACTORS.get(r["能源类型"])
        if not info:
            continue
        e = r["活动数据"] * info["因子"]
        rows.append({**r.to_dict(), "碳排放(tCO2)": round(e, 3), "排放范围": info["类型"]})
        if "Scope 2" in info["类型"]:
            s2 += e
        else:
            s1 += e
    return pd.DataFrame(rows), s1, s2


def detect_anomalies(results):
    alerts = []
    for fuel in results["能源类型"].unique():
        subset = results[results["能源类型"] == fuel]["碳排放(tCO2)"]
        if len(subset) < 3:
            continue
        mean, std = subset.mean(), subset.std()
        if std == 0:
            continue
        for idx in subset.index:
            z = (subset[idx] - mean) / std
            if abs(z) > 2:
                row = results.loc[idx]
                alerts.append(
                    f"🔴 异常: {row['部门']} {row['能源类型']} ({row.get('日期','?')}) = {subset[idx]:.1f} tCO2, "
                    f"Z-score={z:.1f}, 月均值={mean:.1f}"
                )
    return alerts


def generate_recs(by_fuel, total):
    recs = []
    if by_fuel.empty:
        return recs
    top = by_fuel.index[0]
    pct = by_fuel.iloc[0] / total * 100
    if top == "电网电力" and pct > 50:
        recs.append(f"🎯 最大排放源「电网电力」({pct:.0f}%)。建议: ① 安装屋顶光伏 ② 采购绿证 ③ 排查高耗能设备")
    elif top == "天然气":
        recs.append(f"🎯 最大排放源「天然气」({pct:.0f}%)。建议: 评估电锅炉替代 + 余热回收")
    elif top == "烟煤":
        recs.append(f"🎯 最大排放源「烟煤」({pct:.0f}%)。建议: 天然气替代 或 高效煤粉锅炉")
    if total > 26000:
        recs.append("⚖️ 年排放 >26,000 tCO2 → 需强制纳入全国碳市场履约")
    elif total > 5000:
        recs.append("📈 年排放 5,000-26,000 tCO2 → 建议提前建立 MRV 能力")
    return recs


# ============================================================
# GUI 主窗口
# ============================================================
class CarbonScopeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CarbonScope v2 — AI 碳盘查系统")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # 设置深色主题
        self.bg = "#0f172a"
        self.card = "#1e293b"
        self.text = "#e2e8f0"
        self.accent = "#22d3ee"
        self.border = "#334155"
        root.configure(bg=self.bg)

        self.data = DEMO_DATA.copy()
        self.setup_ui()

    def setup_ui(self):
        # 标题栏
        header = tk.Frame(self.root, bg="#1e293b", height=50)
        header.pack(fill="x")
        tk.Label(header, text="🌍 CarbonScope v2", font=("Microsoft YaHei", 14, "bold"),
                 fg="#22d3ee", bg="#1e293b").pack(side="left", padx=20, pady=10)
        tk.Label(header, text="企业碳盘查自动化系统 · GB/T 32150-2025",
                 font=("Microsoft YaHei", 9), fg="#94a3b8", bg="#1e293b").pack(side="left", pady=12)

        # Tab 按钮
        tab_bar = tk.Frame(self.root, bg="#1e293b")
        tab_bar.pack(fill="x")

        self.tab_buttons = {}
        tabs = [("📊 碳排放核算", "calc"), ("🏭 产品碳足迹", "product"), ("📋 完整报告", "report")]
        self.tab_frames = {}

        for i, (text, name) in enumerate(tabs):
            btn = tk.Button(tab_bar, text=text, font=("Microsoft YaHei", 10),
                            bg="#1e293b", fg="#94a3b8", bd=0, padx=16, pady=8,
                            activebackground="#1e293b", activeforeground="#22d3ee",
                            cursor="hand2", relief="flat",
                            command=lambda n=name: self.switch_tab(n))
            btn.pack(side="left", padx=2)
            self.tab_buttons[name] = btn

        # 内容区
        self.content = tk.Frame(self.root, bg=self.bg)
        self.content.pack(fill="both", expand=True, padx=20, pady=10)

        # 初始化各 Tab
        self.setup_calc_tab()
        self.setup_product_tab()
        self.setup_report_tab()

        self.switch_tab("calc")

    def switch_tab(self, name):
        for n, btn in self.tab_buttons.items():
            btn.configure(fg="#22d3ee" if n == name else "#94a3b8")
        for n, f in self.tab_frames.items():
            f.pack_forget()
        self.tab_frames[name].pack(fill="both", expand=True)
        if name == "report":
            self.generate_report()

    # ==================== TAB 1: 碳排放核算 ====================
    def setup_calc_tab(self):
        frame = tk.Frame(self.content, bg=self.bg)
        self.tab_frames["calc"] = frame

        # 工具栏
        toolbar = tk.Frame(frame, bg=self.bg)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Button(toolbar, text="📂 加载 CSV", font=("Microsoft YaHei", 9),
                  bg=self.accent, fg="#0f172a", bd=0, padx=14, pady=6, cursor="hand2",
                  command=self.load_csv).pack(side="left", padx=(0, 6))
        tk.Button(toolbar, text="🔄 加载演示数据", font=("Microsoft YaHei", 9),
                  bg=self.card, fg=self.text, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self.load_demo).pack(side="left")

        # 数据卡片
        self.metrics_frame = tk.Frame(frame, bg=self.bg)
        self.metrics_frame.pack(fill="x", pady=4)

        # 数据表
        self.tree_frame = tk.Frame(frame, bg=self.card, bd=1, relief="solid")
        self.tree_frame.pack(fill="both", expand=True, pady=8)

        # AI 分析
        self.ai_frame = tk.Frame(frame, bg=self.bg)
        self.ai_frame.pack(fill="x", pady=4)

        # 首次加载
        self.run_calc()

    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            self.data = pd.read_csv(path)
            self.run_calc()
            messagebox.showinfo("成功", f"加载 {len(self.data)} 条数据")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def load_demo(self):
        self.data = DEMO_DATA.copy()
        self.run_calc()
        messagebox.showinfo("演示数据", f"已加载 {len(self.data)} 条演示数据")

    def run_calc(self):
        if self.data.empty:
            return

        results, s1, s2 = calc_emissions(self.data)
        total = s1 + s2

        # 更新指标卡片
        for w in self.metrics_frame.winfo_children():
            w.destroy()

        cards = [
            ("🔴 Scope 1 (直接)", f"{s1:.1f} tCO2", "#ef4444"),
            ("🟡 Scope 2 (间接)", f"{s2:.1f} tCO2", "#f59e0b"),
            ("🌍 总排放", f"{total:.1f} tCO2", "#10b981"),
        ]
        for title, value, color in cards:
            card = tk.Frame(self.metrics_frame, bg=self.card, bd=1, relief="solid")
            card.pack(side="left", expand=True, fill="both", padx=4)
            tk.Label(card, text=value, font=("Consolas", 20, "bold"), fg=color, bg=self.card).pack(pady=(10, 0))
            tk.Label(card, text=title, font=("Microsoft YaHei", 9), fg="#94a3b8", bg=self.card).pack(pady=(0, 10))

        # 更新数据表
        for w in self.tree_frame.winfo_children():
            w.destroy()

        tree = ttk.Treeview(self.tree_frame, columns=list(results.columns), show="headings", height=10)
        for col in results.columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")
        for _, row in results.iterrows():
            tree.insert("", "end", values=list(row))
        tree.pack(fill="both", expand=True)

        # AI 分析
        for w in self.ai_frame.winfo_children():
            w.destroy()

        by_fuel = results.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values(ascending=False)
        structure_text = "排放结构:  " + " | ".join(
            [f"{fuel} {val:.1f}t ({val/total*100:.0f}%)" for fuel, val in by_fuel.items()]
        )

        anomalies = detect_anomalies(results)
        anomaly_text = "\n".join(anomalies) if anomalies else "✅ 未检测到异常排放"

        recs = generate_recs(by_fuel, total)
        rec_text = "\n".join(recs) if recs else ""

        ai_text = f"【排放结构】\n{structure_text}\n\n【AI 异常检测】\n{anomaly_text}"
        if rec_text:
            ai_text += f"\n\n【AI 减排建议】\n{rec_text}"

        ai_label = tk.Label(self.ai_frame, text=ai_text, font=("Microsoft YaHei", 9),
                            fg=self.text, bg=self.card, justify="left", wraplength=1000, padx=12, pady=10)
        ai_label.pack(fill="x")

        self._last_results = results
        self._last_s1 = s1
        self._last_s2 = s2

    # ==================== TAB 2: 产品碳足迹 ====================
    def setup_product_tab(self):
        frame = tk.Frame(self.content, bg=self.bg)
        self.tab_frames["product"] = frame

        # 右半：输入
        left = tk.Frame(frame, bg=self.bg)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left, text="产品名称", font=("Microsoft YaHei", 9), fg=self.text, bg=self.bg).pack(anchor="w", pady=(0, 2))
        self.prod_name = tk.Entry(left, font=("Microsoft YaHei", 10), bg=self.card, fg=self.text,
                                  insertbackground=self.text, relief="solid", bd=1)
        self.prod_name.insert(0, "智能手机")
        self.prod_name.pack(fill="x", pady=(0, 8))

        tk.Label(left, text="原材料 (JSON: {\"钢材\":50,\"铝材\":10})", font=("Microsoft YaHei", 9),
                 fg=self.text, bg=self.bg).pack(anchor="w", pady=(0, 2))
        self.prod_mats = tk.Text(left, font=("Consolas", 9), bg=self.card, fg=self.text,
                                 insertbackground=self.text, relief="solid", bd=1, height=4, wrap="word")
        self.prod_mats.insert("1.0", '{"钢材":50,"铝材":10,"塑料":20,"芯片(kg)":1}')
        self.prod_mats.pack(fill="x", pady=(0, 8))

        row1 = tk.Frame(left, bg=self.bg)
        row1.pack(fill="x", pady=(0, 4))
        tk.Label(row1, text="电力(MWh)", font=("Microsoft YaHei", 9), fg=self.text, bg=self.bg).pack(side="left")
        self.prod_elec = tk.Entry(row1, font=("Consolas", 10), bg=self.card, fg=self.text,
                                  insertbackground=self.text, relief="solid", bd=1, width=10)
        self.prod_elec.insert(0, "0.5")
        self.prod_elec.pack(side="left", padx=8)

        tk.Label(row1, text="运输方式", font=("Microsoft YaHei", 9), fg=self.text, bg=self.bg).pack(side="left", padx=(16, 0))
        self.prod_transport = ttk.Combobox(row1, values=["公路", "铁路", "海运", "空运"],
                                           font=("Microsoft YaHei", 9), width=8, state="readonly")
        self.prod_transport.set("公路")
        self.prod_transport.pack(side="left", padx=4)

        row2 = tk.Frame(left, bg=self.bg)
        row2.pack(fill="x", pady=(0, 4))
        tk.Label(row2, text="距离(km)", font=("Microsoft YaHei", 9), fg=self.text, bg=self.bg).pack(side="left")
        self.prod_dist = tk.Entry(row2, font=("Consolas", 10), bg=self.card, fg=self.text,
                                  insertbackground=self.text, relief="solid", bd=1, width=8)
        self.prod_dist.insert(0, "800")
        self.prod_dist.pack(side="left", padx=4)
        tk.Label(row2, text="重量(吨)", font=("Microsoft YaHei", 9), fg=self.text, bg=self.bg).pack(side="left", padx=(12, 0))
        self.prod_weight = tk.Entry(row2, font=("Consolas", 10), bg=self.card, fg=self.text,
                                    insertbackground=self.text, relief="solid", bd=1, width=8)
        self.prod_weight.insert(0, "0.1")
        self.prod_weight.pack(side="left", padx=4)

        row3 = tk.Frame(left, bg=self.bg)
        row3.pack(fill="x", pady=(0, 8))
        tk.Label(row3, text="废品率(%)", font=("Microsoft YaHei", 9), fg=self.text, bg=self.bg).pack(side="left")
        self.prod_waste = tk.Entry(row3, font=("Consolas", 10), bg=self.card, fg=self.text,
                                   insertbackground=self.text, relief="solid", bd=1, width=6)
        self.prod_waste.insert(0, "5")
        self.prod_waste.pack(side="left", padx=4)

        tk.Button(left, text="🖩 计算碳足迹", font=("Microsoft YaHei", 10, "bold"),
                  bg=self.accent, fg="#0f172a", bd=0, padx=18, pady=8, cursor="hand2",
                  command=self.calc_product).pack(pady=(8, 0))

        # 右半：结果
        right = tk.Frame(frame, bg=self.bg)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self.prod_result = tk.Text(right, font=("Consolas", 9), bg=self.card, fg=self.text,
                                   relief="solid", bd=1, wrap="word", state="disabled")
        self.prod_result.pack(fill="both", expand=True)

    def calc_product(self):
        try:
            mats = json.loads(self.prod_mats.get("1.0", "end-1c"))
            elec = float(self.prod_elec.get())
            trans = self.prod_transport.get()
            dist = float(self.prod_dist.get())
            weight = float(self.prod_weight.get())
            waste = float(self.prod_waste.get())

            mat_co2 = 0
            detail = []
            for m, kg in mats.items():
                f = MATERIAL_FACTORS.get(m, 1.0)
                co2 = kg * f / 1000
                mat_co2 += co2
                detail.append(f"  {m}: {kg}kg × {f} kgCO2/kg = {co2:.4f} tCO2")

            energy_co2 = elec * 0.581
            trans_f = TRANSPORT_FACTORS.get(trans, 0.12)
            trans_co2 = dist * weight * trans_f / 1000
            total = (mat_co2 + energy_co2 + trans_co2) * (1 + waste / 100)

            txt = f"""产品碳足迹报告 (ISO 14067)
{'='*50}
产品: {self.prod_name.get()}

【原材料阶段】
{chr(10).join(detail)}

【生产制造】
  电力: {elec} MWh × 0.581 = {energy_co2:.4f} tCO2

【运输】
  方式: {trans} ({trans_f} kgCO2/吨km)
  距离: {dist} km × 重量: {weight} 吨
  排放: {trans_co2:.4f} tCO2

【废品率加成】{waste}%

{'─'*50}
总碳足迹: {total:.4f} tCO2/单位产品
等效: {total*1000:.0f} kg CO2 ≈ {total/2.3:.0f} 辆轿车年排放"""

            self.prod_result.configure(state="normal")
            self.prod_result.delete("1.0", "end")
            self.prod_result.insert("1.0", txt)
            self.prod_result.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("计算错误", str(e))

    # ==================== TAB 3: 完整报告 ====================
    def setup_report_tab(self):
        frame = tk.Frame(self.content, bg=self.bg)
        self.tab_frames["report"] = frame

        toolbar = tk.Frame(frame, bg=self.bg)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Button(toolbar, text="💾 保存为 TXT", font=("Microsoft YaHei", 9),
                  bg=self.accent, fg="#0f172a", bd=0, padx=14, pady=6, cursor="hand2",
                  command=self.save_report).pack(side="left")

        self.report_text = tk.Text(frame, font=("Consolas", 9), bg=self.card, fg=self.text,
                                   relief="solid", bd=1, wrap="word", state="disabled")
        self.report_text.pack(fill="both", expand=True)

    def generate_report(self):
        if not hasattr(self, "_last_results"):
            return
        results = self._last_results
        s1, s2 = self._last_s1, self._last_s2
        total = s1 + s2

        by_fuel = results.groupby("能源类型")["碳排放(tCO2)"].sum().sort_values(ascending=False)
        anomalies = detect_anomalies(results)
        recs = generate_recs(by_fuel, total)

        txt = f"""\
{'='*60}
       企业温室气体排放核算报告
       标准: GB/T 32150-2025
       生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

一、排放总量
{'─'*40}
  Scope 1:  {s1:>15.3f} tCO2e
  Scope 2:  {s2:>15.3f} tCO2e
  总计:     {total:>15.3f} tCO2e

二、排放结构
"""
        for fuel, val in by_fuel.items():
            txt += f"  {fuel:<12} {val:>8.3f} t  ({val/total*100:>5.1f}%)\n"

        txt += "\n三、排放明细\n"
        for _, row in results.iterrows():
            txt += f"  {row['日期']} {row['部门']} {row['能源类型']}: {row['活动数据']} {row['数据单位']} → {row['碳排放(tCO2)']} tCO2\n"

        txt += "\n四、AI 分析\n"
        txt += "\n".join(anomalies) if anomalies else "  ✅ 未检测到异常\n"

        if recs:
            txt += "\n五、减排建议\n"
            txt += "\n".join(recs)

        txt += f"\n{'='*60}\n"

        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", txt)
        self.report_text.configure(state="disabled")
        self._report_txt = txt

    def save_report(self):
        if not hasattr(self, "_report_txt"):
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._report_txt)
            messagebox.showinfo("已保存", f"报告保存至:\n{path}")


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = CarbonScopeApp(root)
    root.mainloop()
