#!/usr/bin/env python3
"""Fetch Google News Taiwan RSS for a static GitHub Pages site.

Called by GitHub Actions, not by visitors. Uses the standard library only.
On network failure, preserves the previous news.json so the site can still deploy.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "news.json"
FEED = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
TAIWAN = timezone(timedelta(hours=8))


def get_news() -> list[dict[str, str]]:
    request = Request(FEED, headers={
        "User-Agent": "Mozilla/5.0 (compatible; UltraWideStudio/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    with urlopen(request, timeout=20) as response:
        xml = response.read(2_000_000)

    root = ET.fromstring(xml)
    seen: set[str] = set()
    articles = []
    for entry in root.findall("./channel/item"):
        title = " ".join((entry.findtext("title") or "").split())
        if not title or title in seen:
            continue
        seen.add(title)
        source = " ".join((entry.findtext("source") or "Google News").split())
        raw_date = entry.findtext("pubDate") or ""
        time_text = ""
        if raw_date:
            try:
                published = parsedate_to_datetime(raw_date)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                time_text = published.astimezone(TAIWAN).strftime("%m/%d %H:%M")
            except (ValueError, TypeError, OverflowError):
                pass
        articles.append({"title": title, "source": source, "time": time_text})
        if len(articles) >= 12:
            break
    if not articles:
        raise ValueError("Google News RSS returned no valid articles")
    return articles


def main() -> int:
    try:
        articles = get_news()
    except Exception as exc:
        print(f"WARNING: News update failed; keeping previous snapshot: {exc}", file=sys.stderr)
        if not OUTPUT.exists():
            OUTPUT.write_text(
                json.dumps({"source": "Google News RSS (Taiwan)", "updated_at": None, "items": []},
                           ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return 0

    snapshot = {
        "source": "Google News RSS (Taiwan)",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": articles,
    }
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {OUTPUT.name}: {len(articles)} articles at {snapshot['updated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
