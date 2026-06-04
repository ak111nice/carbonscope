"""
Crawl4AI + Tavily 完整演示：搜索 → 抓取 → 导出
用法：python demo.py "你的搜索关键词"
"""
import asyncio
import os
import sys
import pandas as pd
from tavily import TavilyClient
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

TAVILY_KEY = "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"
os.environ["TAVILY_API_KEY"] = TAVILY_KEY


async def search_and_crawl(query: str, max_results: int = 5):
    """Tavily 搜索 -> Crawl4AI 抓取 -> 导出 CSV"""

    print("搜索: " + query)
    client = TavilyClient()
    search_result = client.search(query, max_results=max_results)
    results = search_result["results"]
    print("找到 " + str(len(results)) + " 条结果\n")

    if not results:
        print("无搜索结果")
        return

    browser_cfg = BrowserConfig(headless=True, verbose=False)
    crawl_cfg = CrawlerRunConfig(page_timeout=15000)
    rows = []

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for i, item in enumerate(results):
            url = item["url"]
            idx = str(i + 1) + "/" + str(len(results))
            print("[" + idx + "] " + url)
            try:
                result = await crawler.arun(url=url, config=crawl_cfg)
                markdown = (result.markdown or "")[:2000]
                rows.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "score": item.get("score", ""),
                    "content_preview": markdown,
                })
                print("   OK: " + str(len(markdown)) + " chars")
            except Exception as e:
                print("   FAIL: " + str(e))
                rows.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "score": item.get("score", ""),
                    "content_preview": "[ERROR: " + str(e) + "]",
                })

    df = pd.DataFrame(rows)
    csv_path = os.path.join(os.path.dirname(__file__), "output.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print("\n导出: " + csv_path + " (" + str(len(df)) + " 行)")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "AI agent 最新进展"
    asyncio.run(search_and_crawl(query))
