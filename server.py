"""Local server and Google News RSS bridge for UltraWide Studio."""
from __future__ import annotations
import http.server
import json
import pathlib
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
PORT = 8765
RSS_URL = 'https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant'
CACHE = {'until': 0.0, 'items': []}

def fetch_news():
    if CACHE['until'] > time.monotonic() and CACHE['items']:
        return CACHE['items']
    request = urllib.request.Request(RSS_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; UltraWideShowcase/1.0)',
        'Accept': 'application/rss+xml, application/xml, text/xml',
    })
    with urllib.request.urlopen(request, timeout=8) as response:
        xml = response.read(2_000_000)
    root = ET.fromstring(xml)
    items = []
    for entry in root.findall('.//channel/item')[:9]:
        title = (entry.findtext('title') or '').strip()
        source = (entry.findtext('source') or 'Google News').strip()
        pubdate = (entry.findtext('pubDate') or '').strip()
        if title:
            items.append({'title': title, 'source': source, 'time': pubdate[:25]})
    if not items:
        raise ValueError('Empty Google News RSS')
    CACHE.update(until=time.monotonic() + 300, items=items)
    return items

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path == '/api/news':
            try:
                data = json.dumps({'items': fetch_news()}, ensure_ascii=False).encode()
                status = 200
            except Exception as e:
                data = json.dumps({'items': [], 'error': str(e)}, ensure_ascii=False).encode()
                status = 503
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()

if __name__ == '__main__':
    print(f'UltraWide Studio: http://127.0.0.1:{PORT}/')
    print('News uses Google News RSS; offline content is labeled as demonstration.')
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
