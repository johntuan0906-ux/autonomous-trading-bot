from __future__ import annotations
from datetime import datetime, timezone
from .feeds import NewsItem

def score_news(items, positive, negative, macro):
    pos=set(positive); neg=set(negative); macroset=set(macro)
    score=0.0; macro_hits=0; recent=0; reasons=[]
    now=datetime.now(timezone.utc)
    for x in items:
        age=(now-x.published).total_seconds()/3600
        if age>36: continue
        text=(x.title+" "+x.summary).lower(); recent += 1
        p=sum(1 for k in pos if k in text); n=sum(1 for k in neg if k in text)
        mh=sum(1 for k in macroset if k in text); macro_hits += mh
        decay=max(0.0,1-age/36)
        score += (p-n)*decay + 0.35*mh*decay
        if (p or n or mh) and len(reasons)<5: reasons.append(x.title)
    denom=max(1, recent)
    return max(-1,min(1,score/denom)), macro_hits, reasons
