# -*- coding: utf-8 -*-
"""生成碳管理技术岗简历"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from lxml import etree

doc = Document()
style = doc.styles['Normal']
font = style.font
font.name = 'Microsoft YaHei'
font.size = Pt(10.5)
rPr = style.element.get_or_add_rPr()
rFonts = etree.SubElement(rPr, qn('w:rFonts'))
rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

def H(text, level=2):
    h = doc.add_heading(text, level=level)

def P(text, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(10.5)
    return p

def B(text):
    doc.add_paragraph(text, style='List Bullet')

# ====== 头部 ======
name = doc.add_paragraph()
name.alignment = 1
r = name.add_run('周远林')
r.font.size = Pt(18)
r.bold = True

info = doc.add_paragraph()
info.alignment = 1
r = info.add_run('电子科学与技术 本科 | 2026届 | 碳管理SaaS / 能源IoT方向')
r.font.size = Pt(10)
r.font.color.rgb = RGBColor(100, 100, 100)

# ====== 求职意向 ======
intent = doc.add_paragraph()
intent.alignment = 1
r = intent.add_run('求职意向：碳数据工程师 / 碳管理平台开发 / Python后端开发 | 期望城市：不限')
r.font.size = Pt(9)
r.font.color.rgb = RGBColor(80, 80, 80)

# ====== 专业技能 ======
H('专业技能', 2)

P('碳管理与数据', bold=True)
B('熟练企业碳排放核算方法（GB/T 32150-2025），掌握 Scope 1/2 排放因子匹配与数据质量校验')
B('理解碳市场运行机制（配额制、CCER、履约周期）与欧盟 CBAM 法规框架')
B('熟悉ISO 14067产品碳足迹LCA计算方法，掌握原材料/制造/运输全生命周期建模')

P('Python 与数据处理', bold=True)
B('熟练 Python 编程，掌握 Pandas、NumPy、pdfplumber，独立完成能源数据清洗/异常检测/因子匹配')
B('掌握正则表达式、JSON 数据处理、CSV 解析，能将工厂非结构化数据批量转化')
B('有 PyInstaller 打包桌面应用经验，能将 Python 项目交付为非技术用户双击即用的 exe')

P('Web 与前端', bold=True)
B('掌握 HTML/CSS/JavaScript，熟练使用 Chart.js、pdf.js 构建数据可视化仪表盘')
B('了解 Streamlit 框架，具备独立搭建数据应用 Web 界面的能力')

P('嵌入式与 IoT（底层采集）', bold=True)
B('精通 STM32 (F1/F4)、MSPM0G3507 等 MCU 开发，掌握 Keil MDK、C/C++')
B('熟悉 SPI、I2C、USART、CAN 等通信协议，理解 MODBUS RTU/TCP 工业标准')
B('具备从传感器数据采集 → 清洗 → 核算的完整数据管道搭建能力')

# ====== 项目经历 ======
H('项目经历', 2)

P('CarbonScope v4 — 企业碳盘查自动化系统 | 独立开发 | 2026.06', bold=True)
P('基于 GB/T 32150-2025 和 ISO 14067 的 AI 碳核算工具，包含碳排放核算、配额盈亏模拟、产品碳足迹 LCA、PDF 能源账单解析、IoT 仪表采集、报告导出六大模块。')
B('技术栈：Python + Pandas + pdfplumber + JavaScript + Chart.js + pdf.js + Streamlit')
B('实现 PDF 中文能源账单自动解析，正则匹配关键词"用电量/天然气/煤炭"提取能耗数据，含人工确认机制防止误读')
B('IoT 模块基于 MODBUS 协议设计仪表数据自动采集接口，模拟 8 路电表/流量计实时读数 → 自动核算碳排放')
B('部署方式：纯前端 Web 版（index.html 双击即开）+ PyInstaller 打包桌面 exe，零依赖交付')
B('GitHub 仓库: github.com/ak111nice/carbonscope')
B('在线演示: ak111nice.github.io/carbonscope')

P('全国大学生电子设计竞赛（TI 杯）— 简易自行瞄准装置 | 2025.08', bold=True)
P('技术栈：MSPM0G3507 + OpenMV + PID 控制，72 小时封闭竞赛独立完成全流程从 0 到 1。')
B('负责硬件电路设计、传感器调试与 PID 参数整定，具备嵌入式系统架构设计与现场排故能力')
B('采用增量式 PID 将线速度提升至 1m/s，横向误差控制在 8mm 以内')

# ====== 教育背景 ======
H('教育背景', 2)
P('三江学院  电子科学与技术  本科 | 2022.09 - 2026.06')
P('主修：C语言、数据结构、模拟/数字电路、单片机原理、嵌入式系统设计、PCB设计')

# ====== 证书 ======
H('证书与语言', 2)
P('CET-4（英语四级）| 全国计算机等级考试二级 | 普通话二级乙等')

# 保存
out = r'C:\Users\周远林\Desktop\碳中和项目\docs\周远林-碳管理技术岗简历.docx'
doc.save(out)
print('Done: ' + out)
