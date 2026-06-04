"""
PDF 解析 HTTP 服务 — CarbonScope 专用
启动: python pdf_server.py
端口: 8765
"""
import sys, os, json, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
import pdfplumber

# 中英文混合匹配规则
PATTERNS = [
    ("电网电力", r"(?:用电量|电力|电费|用电|Electricity\s*Consumption|Electricity|Consumption|Power).*?(\d+\.?\d*)\s*(MWh|兆瓦时|万度|kWh|千瓦时|度)", "MWh"),
    ("天然气", r"(?:天然气|用气|燃气|Natural\s*Gas|Gas\s*Usage).*?(\d+\.?\d*)\s*(万m³|万立方米|m³|立方米|x\s*10000\s*m3)", "万m³"),
    ("烟煤", r"(?:煤炭|用煤|燃煤|烟煤|Coal\s*Consumption|Coal).*?(\d+\.?\d*)\s*(吨|t|tons)", "吨"),
    ("柴油", r"(?:柴油|Diesel\s*Fuel|Diesel).*?(\d+\.?\d*)\s*(吨|t|tons|升|L)", "吨"),
    ("汽油", r"(?:汽油|Gasoline).*?(\d+\.?\d*)\s*(吨|t|tons|升|L)", "吨"),
]

UNIT_CONVERT = {
    "kWh": ("MWh", 0.001), "千瓦时": ("MWh", 0.001), "度": ("MWh", 0.001),
    "万度": ("MWh", 10), "m³": ("万m³", 0.0001), "立方米": ("万m³", 0.0001),
    "升": ("吨", 0.00085), "L": ("吨", 0.00085),
    "x 10000 m3": ("万m³", 1),
}


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PARSE_PAGES = 10


def parse_pdf_text(pdf_path: str) -> list:
    """解析 PDF 返回能耗数据列表"""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:MAX_PARSE_PAGES]:
            text = page.extract_text() or ""
            if not text.strip():
                continue
            for fuel_type, pattern_str, default_unit in PATTERNS:
                for match in re.finditer(pattern_str, text, re.IGNORECASE):
                    val = float(match.group(1))
                    unit = match.group(2) if len(match.groups()) >= 2 else default_unit
                    std_unit, factor = UNIT_CONVERT.get(unit, (unit, 1))
                    val = round(val * factor, 3)
                    # 去重
                    dup = False
                    for r in rows:
                        if r["fuel"] == fuel_type and abs(r["val"] - val) < 0.01:
                            dup = True
                            break
                    if not dup:
                        rows.append({"fuel": fuel_type, "val": val, "unit": std_unit, "source": "PDF提取"})
    return rows


class PDFHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/parse":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self._json_response({"ok": False, "error": "没有收到 PDF 文件"}, 400)
            return
        if content_length > MAX_UPLOAD_BYTES:
            self._json_response({"ok": False, "error": "PDF 文件超过 10MB，请压缩后再上传"}, 413)
            return

        self.connection.settimeout(60)
        data = self.rfile.read(content_length)

        # 保存临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            results = parse_pdf_text(tmp_path)
            resp = json.dumps({"ok": True, "rows": results, "count": len(results)})
        except Exception as e:
            resp = json.dumps({"ok": False, "error": str(e)})
        finally:
            os.unlink(tmp_path)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp.encode("utf-8"))

    def _json_response(self, payload, status=200):
        resp = json.dumps(payload, ensure_ascii=False)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp.encode("utf-8"))

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 静默


if __name__ == "__main__":
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), PDFHandler)
    print(f"PDF解析服务已启动: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
