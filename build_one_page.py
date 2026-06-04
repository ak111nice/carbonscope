# -*- coding: utf-8 -*-
"""完美一页简历 — 碳管理技术岗（精确一页）"""
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from lxml import etree

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.2)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)

style = doc.styles['Normal']
font = style.font
font.name = 'Microsoft YaHei'
font.size = Pt(10.5)
rPr = style.element.get_or_add_rPr()
rFonts = etree.SubElement(rPr, qn('w:rFonts'))
rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

def R(para, text, size=10.5, bold=False, color=None):
    run = para.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    return run

def new_p(gap_before=3, gap_after=3):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(gap_before)
    p.paragraph_format.space_after = Pt(gap_after)
    return p

def section_header(text):
    p = new_p(10, 4)
    R(p, text, 11.5, True, (34, 211, 238))
    pPr = p._element.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="3" w:color="22d3ee"/></w:pBdr>'
    )
    pPr.append(pBdr)
    return p

def bullet(text, size=10):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.clear()
    R(p, '', size)
    R(p, text, size)
    return p


# ═══════════════ 头部 ═══════════════
table = doc.add_table(rows=1, cols=2)
table.autofit = True

left = table.rows[0].cells[0]
lp = left.paragraphs[0]
lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = lp.add_run()
run.add_picture('C:/Users/周远林/Desktop/66a49a2dcb8ed1a2a8e3bb963eb02aee.jpg', width=Inches(1.1))

right = table.rows[0].cells[1]
rp = right.paragraphs[0]
rp.alignment = WD_ALIGN_PARAGRAPH.LEFT
R(rp, '周远林', 20, True)
R(rp, '    24岁 | 电子科学与技术 本科 | 2026届', 10)

rp2 = right.add_paragraph()
rp2.paragraph_format.space_before = Pt(3)
R(rp2, '📧 1074146990@qq.com  |  📱 17348077782  |  碳数据工程师 / 碳管理平台开发', 9.5)


# ═══════════════ 个人优势 ═══════════════
section_header('个人优势')

adv = new_p(3, 3)
R(adv, '碳核算 + 开发落地 复合型技术背景。', 10.5, True)
R(adv, '独立开发了基于 GB/T 32150 和 ISO 14067 的企业碳盘查自动化系统（CarbonScope v4），实现 PDF 账单智能解析、碳排放自动核算、配额盈亏模拟、IoT 仪表数据采集与 Web 可视化仪表盘全流程自动化。项目已打包为纯前端 Web 版和桌面 exe，面试官扫码即可完整体验。', 10)


# ═══════════════ 核心项目 ═══════════════
section_header('核心项目')

p1 = new_p(6, 2)
R(p1, 'CarbonScope v4 — AI 碳盘查自动化系统（全栈独立开发） | 2026.06', 10.5, True)

bullet('六大模块：碳排放核算 · 碳配额盈亏模拟 · 产品碳足迹 LCA · PDF 账单解析 · IoT 仪表采集 · 报告导出', 10)
bullet('技术栈：Python（pandas · pdfplumber · Streamlit · PyInstaller）+ JavaScript（Chart.js · pdf.js 纯前端）', 10)
bullet('PDF 引擎：正则匹配中文关键词 + 人工确认防误读，从电费单/燃气单自动提取能耗数据', 10)
bullet('IoT 模块：MODBUS 协议 7 通道仪表模拟器，模拟电表/气表/地磅实时采集 → 自动核算', 10)
bullet('部署：纯前端 Web 版（index.html）+ PyInstaller .exe，零依赖双击即用', 10)
bullet('GitHub: github.com/ak111nice/carbonscope ｜ 在线演示: ak111nice.github.io/carbonscope', 10)

p2 = new_p(6, 2)
R(p2, '全国大学生电子设计竞赛（TI 杯）— 自行瞄准装置 | 2025.08', 10.5, True)

bullet('MSPM0G3507 + OpenMV + 增量式 PID + 8 路灰度传感器，72h 封闭竞赛独立完成全流程', 10)
bullet('线速度 1m/s，横向误差 ≤ 8mm，现场三次全部命中；负责硬件电路设计、传感器标定与 PID 整定', 10)


# ═══════════════ 专业技能 ═══════════════
section_header('专业技能')

s1 = new_p(3, 3)
R(s1, '碳管理', 10.5, True)
R(s1, '：GB/T 32150 · ISO 14067 · CBAM · 碳配额/CCER    ', 10)
R(s1, '开发', 10.5, True)
R(s1, '：Python · Pandas · pdfplumber · Streamlit · JavaScript · Chart.js · pdf.js', 10)

s2 = new_p(1, 3)
R(s2, 'IoT / 嵌入式', 10.5, True)
R(s2, '：STM32 · MSPM0 · Keil · C · SPI/I2C/UART/CAN · MODBUS    ', 10)
R(s2, 'AI 工具', 10.5, True)
R(s2, '：GitHub Copilot · Claude Code · Tavily API · LLM Prompt Engineering', 10)


# ═══════════════ 教育背景 ═══════════════
section_header('教育背景')
edu = new_p(5, 3)
R(edu, '三江学院    电子科学与技术    本科    |    2022.09 – 2026.06', 10.5, True)
R(edu, '    |    CET-4 · 全国计算机二级 · 普通话二级乙等', 10, False, (148, 163, 184))


# ═══════════════ 保存 ═══════════════
out = r'C:\Users\周远林\Desktop\周远林-碳管理技术岗-一页版.docx'
doc.save(out)
print('Done: ' + out)
