"""入口脚本：启动 Streamlit 仪表盘"""
import subprocess, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
subprocess.run([sys.executable, "-m", "streamlit", "run",
    os.path.join(os.path.dirname(__file__), "src", "app.py")])
