import feedparser
from typing import List, Dict


def fetch_rss(url: str, encoding: str = "utf-8") -> List[Dict]:
    """从RSS源抓取文章"""
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:30]:
        articles.append({
            "title": entry.get("title", ""),
            "content": entry.get("summary", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
        })
    return articles
