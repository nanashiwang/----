import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

from loguru import logger

from backend.services.settings_service import SettingsService
from backend.services.source_service import SourceService
from src.data.db.sqlite_client import SQLiteClient
from src.data.sources.cninfo_source import fetch_cninfo_announcements
from src.data.sources.crawler_source import fetch_crawler
from src.data.sources.rss_source import fetch_rss
from src.data.sources.tushare_api import TushareAPI


def _normalize_datetime(value) -> Optional[str]:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")

    if isinstance(value, (int, float)):
        try:
            if value > 10_000_000_000:
                value = value / 1000
            return datetime.fromtimestamp(value).isoformat(sep=" ", timespec="seconds")
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y%m%d %H:%M:%S",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(text, fmt).isoformat(sep=" ", timespec="seconds")
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat(sep=" ", timespec="seconds")
    except ValueError:
        return None


def _json_list(value) -> List[str]:
    if value in (None, "", "null"):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            parts = [part.strip() for part in text.replace("，", ",").split(",")]
            return [part for part in parts if part]
    return [str(value).strip()]


class NewsService:
    def __init__(self, db: SQLiteClient):
        self.db = db
        self.sources = SourceService(db)
        self.settings = SettingsService(db)
        self.article_table = db.LEGACY_NEWS_ARTICLES_TABLE

    def list_articles(
        self,
        keyword: str = "",
        source_id: Optional[int] = None,
        date_from: str = "",
        date_to: str = "",
        limit: int = 100,
    ) -> List[Dict]:
        sql = """
            SELECT
                na.*,
                ns.name AS source_name,
                ns.type AS source_type,
                ns.market AS source_market,
                ns.category AS source_category,
                ns.priority AS source_priority,
                ns.credibility AS source_credibility
            FROM {article_table} na
            LEFT JOIN news_sources ns ON ns.id = na.source_id
            WHERE 1 = 1
        """.format(article_table=self.article_table)
        values: List = []

        if keyword:
            sql += " AND (na.title LIKE ? OR na.summary LIKE ? OR na.content LIKE ?)"
            pattern = f"%{keyword}%"
            values.extend([pattern, pattern, pattern])
        if source_id:
            sql += " AND na.source_id = ?"
            values.append(source_id)
        if date_from:
            sql += " AND COALESCE(na.published_at, na.created_at) >= ?"
            values.append(f"{date_from} 00:00:00" if len(date_from) == 10 else date_from)
        if date_to:
            sql += " AND COALESCE(na.published_at, na.created_at) <= ?"
            values.append(f"{date_to} 23:59:59" if len(date_to) == 10 else date_to)

        sql += " ORDER BY COALESCE(na.published_at, na.created_at) DESC LIMIT ?"
        values.append(max(1, min(limit, 500)))

        with self.db.get_connection() as conn:
            rows = conn.execute(sql, values).fetchall()
            return [self._article_row_to_dict(row) for row in rows]

    def list_briefs(self, limit: int = 30) -> List[Dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM event_briefs
                WHERE source = 'news_digest'
                ORDER BY date DESC, created_at DESC
                LIMIT ?
                """,
                (max(1, min(limit, 120)),),
            ).fetchall()
            return [dict(row) for row in rows]

    def fetch_source(self, source_id: int) -> Dict:
        source = self.sources.get_by_id(source_id)
        if not source:
            raise ValueError("资讯源不存在")
        return self.fetch_source_record(source)

    def fetch_source_record(self, source: Dict) -> Dict:
        articles = self._fetch_raw_articles(source)
        normalized = [self._normalize_article(source, item) for item in articles]
        normalized = [item for item in normalized if item["title"]]
        inserted = self.store_articles(source["id"], normalized)
        duplicates = max(len(normalized) - inserted, 0)
        self.sources.update_last_fetched(source["id"])
        digest_dates = {
            (item.get("published_at") or datetime.now().strftime("%Y-%m-%d"))[:10]
            for item in normalized
        }
        for date_str in digest_dates:
            self.refresh_daily_brief(date_str)
        return {
            "source_id": source["id"],
            "source_name": source["name"],
            "fetched": len(normalized),
            "inserted": inserted,
            "duplicates": duplicates,
            "articles": normalized[:5],
        }

    def sync_enabled_sources(self, only_due: bool = False) -> Dict:
        targets = self.sources.list_due_sources() if only_due else self.sources.list_enabled()
        fetched_sources = 0
        inserted_total = 0
        duplicate_total = 0
        errors = []

        for source in targets:
            try:
                result = self.fetch_source_record(source)
                fetched_sources += 1
                inserted_total += result["inserted"]
                duplicate_total += result["duplicates"]
            except Exception as exc:
                logger.warning("资讯源抓取失败: {} - {}", source["name"], exc)
                errors.append(f"{source['name']}: {exc}")

        message = "同步完成"
        if errors:
            message = "；".join(errors[:5])
        return {
            "success": not errors,
            "fetched_sources": fetched_sources,
            "inserted_articles": inserted_total,
            "duplicate_articles": duplicate_total,
            "message": message,
        }

    def store_articles(self, source_id: int, articles: List[Dict]) -> int:
        inserted = 0
        with self.db.get_connection() as conn:
            for article in articles:
                try:
                    conn.execute(
                        f"""
                        INSERT INTO {self.article_table} (
                            source_id, title, summary, content, url, published_at,
                            content_hash, symbols, tags, importance, raw_payload
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_id,
                            article["title"],
                            article.get("summary", ""),
                            article.get("content", ""),
                            article.get("url", ""),
                            article.get("published_at"),
                            article["content_hash"],
                            json.dumps(article.get("symbols", []), ensure_ascii=False),
                            json.dumps(article.get("tags", []), ensure_ascii=False),
                            article.get("importance", 0.5),
                            json.dumps(article.get("raw_payload", {}), ensure_ascii=False),
                        ),
                    )
                    inserted += 1
                except Exception:
                    continue
            conn.commit()
        return inserted

    def refresh_daily_brief(self, target_date: Optional[str] = None):
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    na.title,
                    na.summary,
                    na.importance,
                    na.published_at,
                    ns.name AS source_name,
                    ns.category AS source_category
                FROM {article_table} na
                LEFT JOIN news_sources ns ON ns.id = na.source_id
                WHERE date(COALESCE(na.published_at, na.created_at)) = ?
                ORDER BY na.importance DESC, COALESCE(na.published_at, na.created_at) DESC
                LIMIT 12
                """.format(article_table=self.article_table),
                (date_str,),
            ).fetchall()

            if not rows:
                return

            source_counts = {}
            highlights = []
            for row in rows:
                source_name = row["source_name"] or "未知来源"
                source_counts[source_name] = source_counts.get(source_name, 0) + 1
                summary = row["summary"] or row["title"]
                highlights.append(f"- [{source_name}] {row['title']} | {summary[:80]}")

            source_lines = [f"- {name}: {count} 条" for name, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))]
            content = "\n".join(
                [
                    f"## 每日资讯简报 {date_str}",
                    "",
                    f"今日共收录 {len(rows)} 条高优先级资讯，覆盖 {len(source_counts)} 个资讯源。",
                    "",
                    "### 重点资讯",
                    *highlights[:8],
                    "",
                    "### 来源分布",
                    *source_lines,
                ]
            )

            conn.execute("DELETE FROM event_briefs WHERE date = ? AND source = 'news_digest'", (date_str,))
            conn.execute(
                "INSERT INTO event_briefs (date, content, source) VALUES (?, ?, ?)",
                (date_str, content, "news_digest"),
            )
            conn.commit()

    def _fetch_raw_articles(self, source: Dict) -> List[Dict]:
        source_type = source["type"]
        config = source.get("config", {}) or {}

        if source_type == "rss":
            return fetch_rss(config["url"], max_items=int(config.get("max_items", 30)))
        if source_type == "crawler":
            return fetch_crawler(config)
        if source_type == "cninfo":
            return fetch_cninfo_announcements(config)
        if source_type == "tushare":
            return self._fetch_tushare(config)
        if source_type == "rsshub":
            return self._fetch_rsshub(config)
        raise ValueError(f"暂不支持的资讯源类型: {source_type}")

    def _fetch_tushare(self, config: Dict) -> List[Dict]:
        token = self.settings.get_raw_value("tushare", "token")
        if not token:
            raise ValueError("请先配置 Tushare Token")

        api_url = self.settings.get_raw_value("tushare", "api_url") or ""
        api = TushareAPI(token, api_url=api_url)
        datasets = config.get("datasets", []) or [{"name": "news", "params": {"src": "sina"}}]
        articles = []
        for dataset in datasets:
            dataset_name = dataset.get("name", "news")
            params = dataset.get("params", {})
            try:
                frame = api.fetch_dataset(dataset_name, params)
            except Exception as exc:
                logger.warning("Tushare 数据集抓取失败: {} - {}", dataset_name, exc)
                continue
            if frame is None or frame.empty:
                continue
            for row in frame.to_dict("records"):
                row["_dataset"] = dataset_name
                articles.append(row)
        return articles

    def _fetch_rsshub(self, config: Dict) -> List[Dict]:
        base_url = (config.get("base_url") or "").rstrip("/")
        if not base_url or "127.0.0.1:1200" in base_url and os.getenv("RSSHUB_BASE_URL"):
            base_url = os.getenv("RSSHUB_BASE_URL", base_url)
        if not base_url:
            raise ValueError("请先配置 RSSHub Base URL")

        articles = []
        for route in config.get("routes", []):
            path = route.get("path", "")
            label = route.get("label", "")
            if not path:
                continue
            feed_url = urljoin(f"{base_url}/", path.lstrip("/"))
            for item in fetch_rss(feed_url, max_items=int(route.get("max_items", config.get("max_items", 20)))):
                tags = item.get("tags", [])
                if label:
                    tags = [label, *tags]
                item["tags"] = tags
                item["raw_payload"] = {
                    "route": path,
                    "feed_url": feed_url,
                    "payload": item.get("raw_payload", {}),
                }
                articles.append(item)
        return articles

    def _normalize_article(self, source: Dict, item: Dict) -> Dict:
        title = str(item.get("title") or item.get("announcementTitle") or "").strip()
        summary = str(item.get("summary") or item.get("desc") or item.get("content") or "").strip()
        content = str(item.get("content") or summary or title).strip()
        url = str(
            item.get("url")
            or item.get("link")
            or item.get("adjunctUrl")
            or item.get("news_url")
            or ""
        ).strip()
        published = _normalize_datetime(
            item.get("published")
            or item.get("datetime")
            or item.get("pub_time")
            or item.get("announcementTime")
            or item.get("trade_date")
            or item.get("ann_date")
            or item.get("date")
        )
        symbols = _json_list(item.get("symbols") or item.get("ts_code") or item.get("secCode"))
        tags = _json_list(item.get("tags") or item.get("channels") or item.get("_dataset") or source.get("category"))
        importance = float(source.get("priority", 0.5) * source.get("credibility", 0.5))

        hash_base = "||".join(
            [
                title,
                summary,
                content[:500],
                url,
                published or "",
            ]
        )
        content_hash = hashlib.sha256(hash_base.encode("utf-8")).hexdigest()

        return {
            "title": title,
            "summary": summary or title,
            "content": content,
            "url": url,
            "published_at": published,
            "content_hash": content_hash,
            "symbols": symbols,
            "tags": tags,
            "importance": round(min(max(importance, 0.1), 1.0), 3),
            "raw_payload": item,
        }

    def _article_row_to_dict(self, row) -> Dict:
        item = dict(row)
        item["symbols"] = _json_list(item.get("symbols"))
        item["tags"] = _json_list(item.get("tags"))
        return item
