"""
CarbonScope 桌面版启动器
========================
作用：
  用 pywebview 创建一个原生 Windows 窗口，加载 index.html。
  PyInstaller 打包时作为入口文件，生成 dist/CarbonScope.exe。

路径查找逻辑（按优先级）：
  1. exe 同级目录的 index.html
  2. PyInstaller 临时解压目录的 index.html
  3. 项目根目录的 index.html

依赖：
  pywebview (pip install pywebview)

打包命令：
  python -m PyInstaller --onefile --windowed --name CarbonScope src/carbonscope_v3.py
"""

import os
import sys
import webview

def main():
    # 找到 index.html — 优先同级目录，其次 src 目录
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    html_path = os.path.join(base, "index.html")

    if not os.path.exists(html_path):
        # PyInstaller 打包后 __file__ 会在临时目录，回退到 exe 同级
        html_path = os.path.join(os.path.dirname(sys.executable), "index.html")

    if not os.path.exists(html_path):
        # 最终回退
        html_path = os.path.join(base, "src", "..", "index.html")

    # 转为 file:// URL
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/")

    win = webview.create_window(
        "CarbonScope v3 — AI 碳盘查系统",
        url=url,
        width=1100,
        height=750,
        resizable=True,
    )
    webview.start(debug=False)

if __name__ == "__main__":
    main()
