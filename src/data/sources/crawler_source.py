import requests
from bs4 import BeautifulSoup
from typing import List, Dict


def fetch_crawler(config: Dict) -> List[Dict]:
    """从网页爬取资讯"""
    url = config.get("url", "")
    selector = config.get("selector", "")
    title_sel = config.get("title_sel", "h3")
    content_sel = config.get("content_sel", "p")

    resp = requests.get(url, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    resp.encoding = config.get("encoding", resp.apparent_encoding)
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    items = soup.select(selector) if selector else []
    for item in items[:30]:
        title_el = item.select_one(title_sel)
        content_el = item.select_one(content_sel)
        articles.append({
            "title": title_el.get_text(strip=True) if title_el else "",
            "content": content_el.get_text(strip=True) if content_el else "",
        })
    return articles
