@echo off
chcp 65001 >nul
echo ==========================================
echo  CarbonScope PDF解析服务
echo  端口: 8765 | 基于 pdfplumber
echo ==========================================
cd /d "C:\Users\周远林\Desktop\碳中和项目"
py -3.14 -c "import pdfplumber" >nul 2>nul
if errorlevel 1 (
  echo 缺少 PDF 解析依赖，请先运行:
  echo py -3.14 -m pip install -r requirements.txt
  pause
  exit /b 1
)
py -3.14 src/pdf_server.py
pause
