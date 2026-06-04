"""
因子库自动更新爬虫
==================
用途：
  定期抓取发改委、生态环境部等官方网站，通过页面指纹（MD5）对比
  检测排放因子和碳价是否更新。发现变化后提醒人工确认。

抓取目标（CHECK_URLS）：
  1. 全国碳市场行情 (ets.sceex.com.cn)        → 碳价
  2. 生态环境部 核算指南 (mee.gov.cn)          → 排放因子
  3. 国家发改委 因子公告 (ndrc.gov.cn)          → 电网排放因子

工作流程：
  1. fetch_page()     — HTTP 抓取页面 HTML
  2. check_for_updates() — MD5 哈希计算页面指纹
  3. compare_fingerprints() — 对比上次保存的指纹 JSON
  4. save_fingerprints() — 保存本次指纹到 data/fingerprints.json

使用：
  python factor_updater.py           # 首次运行，保存指纹
  python factor_updater.py           # 再次运行，检测变化

限制：
  - 当前为 HTTP 请求 + 正则关键词匹配，非完整 HTML 解析
  - 仅检测页面是否变化，不自动提取具体数值
  - 后续可集成 Tavily API 实现动态搜索+结构化提取

依赖（标准库）：
  urllib.request, hashlib, json, datetime
"""

import json
import os
import hashlib
from datetime import datetime

# 硬编码抓取目标（后续可集成 Tavily 做动态搜索）
CHECK_URLS = [
    {
        "name": "全国碳市场行情",
        "url": "https://ets.sceex.com.cn/index",
        "keywords": ["碳价", "成交价", "收盘价"],
        "type": "carbon_price"
    },
    {
        "name": "生态环境部 核算指南",
        "url": "https://www.mee.gov.cn/ywgz/ydqhbh/",
        "keywords": ["排放因子", "核算指南", "温室气体", "电网"],
        "type": "emission_factor"
    },
    {
        "name": "国家电网排放因子公告",
        "url": "https://www.ndrc.gov.cn/xwdt/tzgg/",
        "keywords": ["电网排放因子", "碳排放因子", "基准年"],
        "type": "emission_factor"
    },
]


def fetch_page(url):
    """静默抓取（不依赖外部库）"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "CarbonScope/3.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def check_for_updates():
    """检测所有目标页面是否有更新"""
    results = []
    for item in CHECK_URLS:
        html = fetch_page(item["url"])
        if not html:
            continue

        # 数据指纹（检测页面是否变了）
        fp = hashlib.md5(html.encode()).hexdigest()

        found_keywords = [kw for kw in item["keywords"] if kw in html]
        results.append({
            "name": item["name"],
            "url": item["url"],
            "fingerprint": fp,
            "keywords_found": found_keywords,
            "has_content": len(html) > 500,
            "checked_at": datetime.now().isoformat(),
        })

    return results


def compare_fingerprints(previous_result_path="data/fingerprints.json"):
    """对比上次抓取结果，发现变化"""
    if not os.path.exists(previous_result_path):
        return []

    with open(previous_result_path, "r", encoding="utf-8") as f:
        previous = json.load(f)

    current = check_for_updates()
    changes = []

    for curr in current:
        for prev in previous:
            if curr["name"] == prev["name"]:
                if curr["fingerprint"] != prev["fingerprint"]:
                    changes.append({
                        "name": curr["name"],
                        "url": curr["url"],
                        "change": "页面内容已更新",
                        "previous_fp": prev["fingerprint"],
                        "current_fp": curr["fingerprint"],
                    })
                break

    return changes


def save_fingerprints():
    """保存当前抓取状态"""
    current = check_for_updates()
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(base_dir, exist_ok=True)
    with open(os.path.join(base_dir, "fingerprints.json"), "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return os.path.join(base_dir, "fingerprints.json")


if __name__ == "__main__":
    results = check_for_updates()
    print(f"因子库爬虫 v1.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"检测 {len(CHECK_URLS)} 个目标页面\n")

    for r in results:
        status = "✅" if r["has_content"] else "❌"
        kws = ", ".join(r["keywords_found"]) if r["keywords_found"] else "无匹配关键词"
        print(f"  {status} {r['name']}")
        print(f"     URL: {r['url']}")
        print(f"     关键词: {kws}")
        print(f"     指纹: {r['fingerprint'][:16]}...\n")

    save_fingerprints()
    print("指纹已保存至 data/fingerprints.json")
    print("下次运行时对比指纹即可发现页面更新")
