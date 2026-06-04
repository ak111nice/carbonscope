# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt
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

def H(text, level=1):
    doc.add_heading(text, level=level)

def P(text, bold=False, size=10.5):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    return p

def B(text):
    doc.add_paragraph(text, style='List Bullet')

H('CarbonScope v4 演示视频脚本', 1)
P('两个版本可选 | 演示文件已备好：data/演示数据_7-9月.csv + data/演示账单_2025年8月.pdf')

# ====== Version A ======
H('版本 A：30 秒极速版（推荐 — 附简历链接）', 2)
P('纯画面，不配音。配轻音乐。', size=9)

steps_a = [
    ('0-5', '首页加载演示 CSV → 显示 Scope 1/2/总排放三个数字卡片 + 柱状图'),
    ('5-10', '切【配额盈亏】→ 点计算 → 显示 3500 vs 3587，亏 87 吨，成本 7395 元'),
    ('10-15', '切【产品碳足迹】→ 默认数据直接点计算 → 总碳足迹出结果'),
    ('15-20', '切【PDF解析】→ 上传 data/演示账单_2025年8月.pdf → 确认表格弹出 → 勾选→导入'),
    ('20-25', '切【IoT仪表】→ 点采集 → 仪表读数更新 → 自动核算出结果'),
    ('25-30', '切【完整报告】→ 下载 TXT → 回到首页停在三个卡片。结束。'),
]
for t, action in steps_a:
    P(t + ' | ' + action, bold=True, size=10)

# ====== Version B ======
H('版本 B：60 秒讲解版（面试现场 / 发给技术主管）', 2)
P('一边操作一边说。节奏快，每步一句话。', size=9)

steps_b = [
    ('0-5', '首页', 'CarbonScope 碳盘查系统。Scope 1 直接排放、Scope 2 间接排放、总计。'),
    ('5-10', '配额盈亏', '政府给 3500 吨免费配额，实际排了 3587 吨，亏 87 吨，按每吨 85 元，履约成本约 7400。'),
    ('10-15', '产品碳足迹', 'ISO 14067 产品碳足迹。输入原材料、电力、运输，自动算一件产品的全生命周期碳排放。'),
    ('15-22', 'PDF 解析', '上传真实电费单 PDF。正则匹配中文关键词提取能耗。确认无误后导入核算。'),
    ('22-28', 'IoT 仪表', 'MODBUS 协议模拟工厂 7 块仪表实时采集。点一次采集就是读一次所有电表气表。'),
    ('28-35', '完整报告', '一键生成 GB/T 32150 标准报告，下载 TXT。回首页。纯前端 Web 版 + exe 桌面版。'),
]
for t, action, script in steps_b:
    P(t + ' ' + action, bold=True, size=10)
    P('    → ' + script, size=9.5)

H('录制方式', 2)
B('按 Win+G 打开 Game Bar → 录制（Win+Alt+R）→ 停止（Win+Alt+R）')
B('文件默认保存在 Videos/Captures 文件夹')
B('只录 CarbonScope 窗口，不要全桌面')
B('鼠标慢一点，说错停一秒接着说，后续可剪辑')

H('演示文件', 2)
B('CSV：data/演示数据_7-9月.csv（16 条真实格式能源数据）')
B('PDF：data/演示账单_2025年8月.pdf（英文账单，含电力/天然气/煤炭/柴油/汽油）')

out = r'C:\Users\周远林\Desktop\碳中和项目\docs\演示视频脚本.docx'
doc.save(out)
print('Done: ' + out)
