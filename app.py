"""
AI 智能碳盘查系统 — Web 版
FastAPI 后端 + 碳排放自动核算引擎

基于 GB/T 32150-2025 | 排放因子：国家发改委指南

启动: python app.py
访问: http://localhost:8888
"""
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io
import os
import json
from datetime import datetime
import uuid

app = FastAPI(title="AI 智能碳盘查系统")

# =========== 排放因子库 ===========
EMISSION_FACTORS = {
    "电网电力": {"factor": 0.5810, "unit": "tCO2/MWh", "scope": "Scope 2"},
    "天然气":   {"factor": 21.62,  "unit": "tCO2/万m³", "scope": "Scope 1"},
    "烟煤":     {"factor": 2.53,   "unit": "tCO2/吨",  "scope": "Scope 1"},
    "柴油":     {"factor": 3.16,   "unit": "tCO2/吨",  "scope": "Scope 1"},
    "汽油":     {"factor": 2.99,   "unit": "tCO2/吨",  "scope": "Scope 1"},
    "水泥熟料": {"factor": 0.535,  "unit": "tCO2/吨熟料", "scope": "Scope 1"},
    "钢铁":     {"factor": 1.80,   "unit": "tCO2/吨钢", "scope": "Scope 1"},
    "蒸汽":     {"factor": 0.25,   "unit": "tCO2/吨蒸汽", "scope": "Scope 1"},
}

KNOWN_UNITS = {
    "kWh": "MWh", "度": "MWh", "千瓦时": "MWh",
    "万m3": "万m³", "万立方米": "万m³",
    "吨": "吨", "t": "吨",
}


def calc_emission(fuel_type: str, amount: float) -> dict:
    """核心计算"""
    ef = EMISSION_FACTORS.get(fuel_type)
    if not ef:
        return None
    co2 = round(amount * ef["factor"], 3)
    return {
        "energy": fuel_type,
        "amount": amount,
        "factor": ef["factor"],
        "factor_unit": ef["unit"],
        "co2": co2,
        "scope": ef["scope"],
    }


# =========== API ===========

@app.post("/api/calculate")
async def api_calculate(request: Request):
    """接收 JSON 数据，返回计算结果"""
    try:
        body = await request.json()
        items = body.get("data", body)
        results = []
        total_scope1 = 0.0
        total_scope2 = 0.0
        for item in items:
            r = calc_emission(item["fuel"], float(item["amount"]))
            if r:
                r["label"] = item.get("label", item["fuel"])
                results.append(r)
                if "Scope 1" in r["scope"]:
                    total_scope1 += r["co2"]
                else:
                    total_scope2 += r["co2"]

        total = total_scope1 + total_scope2
        by_fuel = {}
        for r in results:
            f = r["energy"]
            by_fuel[f] = by_fuel.get(f, 0) + r["co2"]

        # 合规建议
        alert = ""
        if total > 26000:
            alert = "⚠️ 已触发全国碳市场纳入门槛（>26,000 tCO2），须强制履约。"
        elif total > 5000:
            alert = "⚡ 排放量 >5,000 tCO2，建议主动建立碳管理体系。"
        else:
            alert = "📋 暂不强制履约，可提前建立碳核算能力。"

        return JSONResponse({
            "items": results,
            "total_scope1": round(total_scope1, 3),
            "total_scope2": round(total_scope2, 3),
            "total": round(total, 3),
            "by_fuel": {k: round(v, 3) for k, v in sorted(by_fuel.items(), key=lambda x: -x[1])},
            "alert": alert,
            "top_emitter": max(by_fuel, key=by_fuel.get) if by_fuel else "",
            "top_pct": round(max(by_fuel.values()) / total * 100, 1) if total > 0 else 0,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """上传 CSV/Excel 自动解析"""
    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        # 尝试自动映射列名
        col_map = {}
        for col in df.columns:
            cl = col.strip().lower()
            if any(k in cl for k in ["能源", "fuel", "类型", "type", "名称", "name"]):
                col_map["fuel"] = col
            elif any(k in cl for k in ["活动", "用量", "数量", "amount", "value", "数值"]):
                col_map["amount"] = col
            elif any(k in cl for k in ["标签", "label", "部门", "备注", "note"]):
                col_map["label"] = col

        data = []
        for _, row in df.iterrows():
            fuel_col = col_map.get("fuel", df.columns[0])
            amt_col = col_map.get("amount", df.columns[1])
            lbl_col = col_map.get("label", df.columns[2] if len(df.columns) > 2 else fuel_col)
            data.append({
                "fuel": str(row[fuel_col]).strip(),
                "amount": float(row[amt_col]),
                "label": str(row[lbl_col]).strip() if lbl_col in df.columns else "",
            })
        return JSONResponse({"data": data, "count": len(data)})
    except Exception as e:
        return JSONResponse({"error": f"文件解析失败: {e}"}, status_code=400)


# =========== 前端 ===========

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 智能碳盘查系统</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body class="bg-gray-50 min-h-screen">
<header class="bg-emerald-700 text-white p-4 shadow-lg">
  <div class="max-w-5xl mx-auto flex items-center gap-3">
    <span class="text-2xl">🌱</span>
    <div>
      <h1 class="text-xl font-bold">AI 智能碳盘查系统</h1>
      <p class="text-emerald-200 text-sm">GB/T 32150-2025 · AI 驱动 · 自动核算</p>
    </div>
  </div>
</header>

<main class="max-w-5xl mx-auto p-4 space-y-6">

<!-- 输入区 -->
<div class="bg-white rounded-xl shadow p-6">
  <h2 class="text-lg font-bold mb-4">📥 数据录入</h2>

  <!-- 快速上传 -->
  <div class="mb-4 flex gap-3 items-center">
    <label class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg cursor-pointer text-sm font-medium">
      📁 上传 CSV/Excel
      <input type="file" id="fileInput" accept=".csv,.xlsx,.xls" class="hidden" onchange="uploadFile()">
    </label>
    <span id="uploadStatus" class="text-sm text-gray-500"></span>
  </div>

  <!-- 手动输入 -->
  <div id="manualInput" class="space-y-2">
    <div class="flex gap-2 items-end" id="inputRow">
      <div class="flex-1">
        <label class="text-xs text-gray-500">能源类型</label>
        <select id="fuel_type" class="w-full border rounded p-2 text-sm">
          <option value="电网电力">⚡ 电网电力</option>
          <option value="天然气">🔥 天然气</option>
          <option value="烟煤">🪨 烟煤</option>
          <option value="柴油">⛽ 柴油</option>
          <option value="汽油">🚗 汽油</option>
          <option value="水泥熟料">🏗 水泥熟料</option>
          <option value="钢铁">🏭 钢铁</option>
          <option value="蒸汽">💨 蒸汽</option>
        </select>
      </div>
      <div>
        <label class="text-xs text-gray-500">用量</label>
        <input id="fuel_amount" type="number" step="0.01" placeholder="如 1200" class="w-32 border rounded p-2 text-sm">
      </div>
      <div>
        <label class="text-xs text-gray-500">备注</label>
        <input id="fuel_label" type="text" placeholder="如 生产车间" class="w-40 border rounded p-2 text-sm">
      </div>
      <button onclick="addEntry()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ 添加</button>
    </div>
  </div>

  <!-- 已添加列表 -->
  <div class="mt-4">
    <table class="w-full text-sm" id="dataTable">
      <thead class="text-gray-500 border-b">
        <tr><th class="text-left py-1">能源</th><th class="text-left">用量</th><th class="text-left">备注</th><th></th></tr>
      </thead>
      <tbody id="dataBody"></tbody>
    </table>
  </div>

  <div class="mt-4 flex gap-3">
    <button onclick="calculate()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg font-bold">
      🔢 开始核算
    </button>
    <button onclick="clearAll()" class="border border-gray-300 px-4 py-2 rounded-lg text-sm">清空</button>
    <span id="calcStatus" class="text-sm text-gray-500 self-center"></span>
  </div>
</div>

<!-- 结果区 -->
<div id="resultArea" class="hidden space-y-4">

  <!-- 总览卡片 -->
  <div class="grid grid-cols-3 gap-4">
    <div class="bg-white rounded-xl shadow p-4 text-center">
      <div class="text-3xl font-bold text-emerald-600" id="totalEmissions">--</div>
      <div class="text-sm text-gray-500 mt-1">总排放 (tCO2e)</div>
    </div>
    <div class="bg-white rounded-xl shadow p-4 text-center">
      <div class="text-3xl font-bold text-orange-500" id="scope1Emissions">--</div>
      <div class="text-sm text-gray-500 mt-1">直接排放 Scope 1</div>
    </div>
    <div class="bg-white rounded-xl shadow p-4 text-center">
      <div class="text-3xl font-bold text-blue-500" id="scope2Emissions">--</div>
      <div class="text-sm text-gray-500 mt-1">间接排放 Scope 2</div>
    </div>
  </div>

  <!-- 告警 -->
  <div id="alertBox" class="bg-amber-50 border-l-4 border-amber-400 p-3 rounded-r text-sm"></div>

  <!-- 图表 -->
  <div class="bg-white rounded-xl shadow p-6">
    <h3 class="font-bold mb-3">📊 排放结构</h3>
    <div class="max-w-md mx-auto"><canvas id="pieChart"></canvas></div>
  </div>

  <!-- 明细表 -->
  <div class="bg-white rounded-xl shadow p-6">
    <h3 class="font-bold mb-3">📋 排放明细</h3>
    <div class="overflow-x-auto">
      <table class="w-full text-sm" id="detailTable">
        <thead class="bg-gray-50 border-b">
          <tr><th class="text-left p-2">能源类型</th><th class="text-right p-2">用量</th><th class="text-right p-2">排放因子</th><th class="text-right p-2">碳排放(tCO2)</th><th class="text-center p-2">范围</th></tr>
        </thead>
        <tbody id="detailBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 导出 -->
  <div class="flex gap-3">
    <button onclick="exportReport()" class="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium">
      📄 导出报告
    </button>
  </div>

</div>
</main>

<footer class="text-center text-xs text-gray-400 pb-6">
  AI 碳盘查系统 · 排放因子来源：国家发改委 · 核算标准：GB/T 32150-2025
</footer>

<script>
let entries = [];
let chart = null;

function addEntry() {
  const fuel = document.getElementById('fuel_type').value;
  const amount = parseFloat(document.getElementById('fuel_amount').value);
  const label = document.getElementById('fuel_label').value || fuel;
  if (!amount || amount <= 0) return;
  entries.push({fuel, amount, label});
  renderTable();
  document.getElementById('fuel_amount').value = '';
  document.getElementById('fuel_label').value = '';
  document.getElementById('fuel_amount').focus();
}

function removeEntry(i) { entries.splice(i, 1); renderTable(); }

function clearAll() {
  entries = [];
  renderTable();
  document.getElementById('resultArea').classList.add('hidden');
}

function renderTable() {
  const tbody = document.getElementById('dataBody');
  tbody.innerHTML = entries.map((e, i) =>
    `<tr class="border-b"><td class="py-1">${e.fuel}</td><td>${e.amount}</td><td>${e.label}</td>
     <td><button onclick="removeEntry(${i})" class="text-red-400 hover:text-red-600 text-xs">删除</button></td></tr>`
  ).join('');
  document.getElementById('uploadStatus').textContent = '';
}

async function uploadFile() {
  const file = document.getElementById('fileInput').files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  document.getElementById('uploadStatus').textContent = '解析中...';
  const res = await fetch('/api/upload', {method:'POST', body:form});
  const json = await res.json();
  if (json.error) {
    document.getElementById('uploadStatus').textContent = '❌ ' + json.error;
  } else {
    entries = json.data.map(d => ({fuel:d.fuel, amount:d.amount, label:d.label||d.fuel}));
    renderTable();
    document.getElementById('uploadStatus').textContent = `✅ 导入 ${json.count} 条数据`;
  }
}

async function calculate() {
  if (entries.length === 0) return;
  document.getElementById('calcStatus').textContent = '计算中...';
  const res = await fetch('/api/calculate', {
    method:'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({data: entries})
  });
  const d = await res.json();
  document.getElementById('calcStatus').textContent = '';

  document.getElementById('totalEmissions').textContent = d.total;
  document.getElementById('scope1Emissions').textContent = d.total_scope1;
  document.getElementById('scope2Emissions').textContent = d.total_scope2;
  document.getElementById('alertBox').innerHTML = `<strong>合规建议：</strong>${d.alert} 最大排放源「${d.top_emitter}」占 ${d.top_pct}%。`;

  // 明细表
  document.getElementById('detailBody').innerHTML = d.items.map(r =>
    `<tr class="border-b">
      <td class="p-2">${r.energy}</td>
      <td class="text-right p-2">${r.amount}</td>
      <td class="text-right p-2 text-gray-500">${r.factor} ${r.factor_unit}</td>
      <td class="text-right p-2 font-medium">${r.co2}</td>
      <td class="text-center p-2"><span class="${r.scope.includes('1')?'text-orange-500':'text-blue-500'} text-xs font-medium">${r.scope}</span></td>
    </tr>`
  ).join('');

  // 饼图
  if (chart) chart.destroy();
  const ctx = document.getElementById('pieChart').getContext('2d');
  const labels = Object.keys(d.by_fuel);
  const values = Object.values(d.by_fuel);
  const colors = ['#059669','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#ec4899','#14b8a6','#f97316'];
  chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
      }]
    },
    options: {
      plugins: {
        legend: { position: 'bottom' },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} tCO2` }}
      }
    }
  });

  document.getElementById('resultArea').classList.remove('hidden');
  window._lastResult = d;
}

function exportReport() {
  const d = window._lastResult;
  if (!d) return;
  const report = [
    '============================================',
    '  企业温室气体排放核算报告',
    '  基于 GB/T 32150-2025',
    `  生成时间：${new Date().toLocaleString()}`,
    '============================================',
    '',
    `一、排放总量`,
    `  总排放：${d.total} tCO2e`,
    `  直接排放(Scope 1)：${d.total_scope1} tCO2e`,
    `  间接排放(Scope 2)：${d.total_scope2} tCO2e`,
    '',
    '二、排放明细',
    ...d.items.map(r => `  ${r.energy} × ${r.amount} = ${r.co2} tCO2 (${r.scope})`),
    '',
    '三、合规建议',
    `  ${d.alert}`,
    '',
    '============================================',
    '  本报告由 AI 智能碳盘查系统自动生成',
    '============================================',
  ].join('\n');
  const blob = new Blob([report], {type:'text/plain;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '碳盘查报告_' + new Date().toISOString().slice(0,10) + '.txt';
  a.click();
}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML

# 静态文件
os.makedirs("static", exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    print("\n🌱 AI 智能碳盘查系统启动中...")
    print("   访问: http://localhost:8888\n")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="warning")
