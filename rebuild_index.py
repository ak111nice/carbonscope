# -*- coding: utf-8 -*-
"""生成干净的 index.html——PDF用本地文件、Chart.js内嵌极简版"""
import os

# Read current index.html to extract just the non-pdf.js parts
base = r'C:\Users\周远林\Desktop\碳中和项目'
with open(os.path.join(base, 'index.html'), 'r', encoding='utf-8') as f:
    content = f.read()

# Find the actual app HTML: everything between <!DOCTYPE and the first </style>
# plus the body content and script WITHOUT the pdf.js blob
doctype_end = content.find('</head>')
body_start = content.find('<body>')
script_start = content.find('<script>\n// ====================== 数据层')
script_end = content.find('</html>')

head = content[:doctype_end]
body = content[body_start:script_start]
app_js = content[script_start:script_end]

# Add local pdf.js reference in head
head = head.replace('</title>', '</title>\n<script src="data/pdf.min.js"></script>', 1)

# Combine
clean_html = head + '\n</head>\n' + body + app_js + '\n</body>\n</html>'

out_path = os.path.join(base, 'index_clean.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(clean_html)

print(f'Clean: {len(clean_html)} bytes')

# Replace original
import shutil
shutil.move(out_path, os.path.join(base, 'index.html'))
print('index.html replaced')
