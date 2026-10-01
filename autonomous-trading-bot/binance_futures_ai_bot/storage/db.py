import sqlite3
from datetime import datetime, timezone
class Journal:
    def __init__(self,path="trades.db"):
        self.con=sqlite3.connect(path); self.con.execute("create table if not exists trades(id integer primary key, ts text, symbol text, direction text, entry real, stop real, target real, qty real, score real, reason text)"); self.con.commit()
    def log(self,**kw):
        self.con.execute("insert into trades(ts,symbol,direction,entry,stop,target,qty,score,reason) values(?,?,?,?,?,?,?,?,?)",(datetime.now(timezone.utc).isoformat(),kw["symbol"],kw["direction"],kw["entry"],kw["stop"],kw["target"],kw["qty"],kw["score"],kw["reason"])); self.con.commit()
