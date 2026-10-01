from __future__ import annotations
import urllib.request, xml.etree.ElementTree as ET, email.utils, html, re
from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass
class NewsItem:
    title: str
    summary: str
    published: datetime
    source: str
    url: str

def _clean(s):
    s=html.unescape(re.sub(r"<[^>]+>"," ",s or "")); return re.sub(r"\s+"," ",s).strip()

def fetch_feeds(urls, per_feed=30):
    items=[]
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; FuturesResearchBot/0.1)"})
            with urllib.request.urlopen(req,timeout=10) as r: root=ET.fromstring(r.read())
            channel=root.find("channel") or root
            src=channel.findtext("title") or url
            entries=channel.findall("item")
            if not entries:
                ns={"a":"http://www.w3.org/2005/Atom"}; entries=root.findall("a:entry",ns)
            for e in entries[:per_feed]:
                title=_clean(e.findtext("title"))
                summ=_clean(e.findtext("description") or e.findtext("summary"))
                link=e.findtext("link") or ""
                pub=e.findtext("pubDate") or e.findtext("published") or e.findtext("updated")
                try: ts=datetime(*email.utils.parsedate(pub)[:6],tzinfo=timezone.utc) if pub else datetime.now(timezone.utc)
                except Exception: ts=datetime.now(timezone.utc)
                items.append(NewsItem(title,summ,ts,src,link))
        except Exception:
            continue
    return sorted(items,key=lambda x:x.published,reverse=True)
