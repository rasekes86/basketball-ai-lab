"""Capture publicly visible NBA pregame sportsbook quotes from ESPN scoreboard.

This is a no-key secondary source for *observed* offered prices, not an
official odds feed. No network requests beyond the existing calendar query.
The provider does not publish a reliable last-updated timestamp here:
do not mislabel capture time as a sportsbook change time.
"""
from .transform import time_utc

def _decimal_from_american(raw):
    if raw is None or isinstance(raw,bool): return None
    word=str(raw).strip().upper()
    if word in ("EVEN","EVENS"): return 2.0
    try:
        number=int(word)
    except (ValueError,TypeError):
        return None
    if number==0 or abs(number)>10000: return None
    result=1+number/100 if number>0 else 1+100/abs(number)
    return round(result,6) if 1.01<=result<=100 else None

def _source_line(market, side, field):
    if not isinstance(market,dict): return None
    entry=market.get(side)
    if not isinstance(entry,dict): return None
    for phase in ("current","close"):
        record=entry.get(phase)
        if isinstance(record,dict) and record.get(field) is not None:
            return record[field]
    return None

def _number(raw, prefix=None):
    if isinstance(raw,bool) or raw is None: return None
    s=str(raw).strip().lower()
    if prefix and s.startswith(prefix): s=s[1:]
    try:
        value=float(s)
    except (TypeError,ValueError):
        return None
    if value!=value or not -10000<value<10000: return None
    return value

def scoreboard_quotes(payload,games,now):
    """Validated provider-labelled snapshots; only unstarted ESPN fixtures."""
    if not isinstance(payload,dict) or not isinstance(payload.get("events"),list):
        return []
    rows=[]
    for event in payload["events"]:
        if not isinstance(event,dict):continue
        eid=str(event.get("id") or "")
        game=games.get(eid)
        if not game or game.get("status")!="SCHEDULED":continue
        start=time_utc(game.get("start_utc"))
        event_start=time_utc(event.get("date"))
        if not start or not event_start or start!=event_start or now>=start:
            continue
        for comp in event.get("competitions") or []:
            if not isinstance(comp,dict) or str(comp.get("id"))!=eid:continue
            for offer in comp.get("odds") or []:
                if not isinstance(offer,dict):continue
                provider=offer.get("provider") or {}
                name=provider.get("name") if isinstance(provider,dict) else None
                if not isinstance(name,str) or not 1<=len(name)<=70:continue
                # Valid sportsbook display, not verified availability in Spain.
                base={"event_id":eid,"home":game["home"],"away":game["away"],
                    "start_utc":game["start_utc"],"bookmaker":name,
                    "provider":"ESPN scoreboard",
                    "captured_utc":now.isoformat(),"updated_utc":now.isoformat(),
                    "quote_time_basis":"OBSERVED_AT_CAPTURE",
                    "source":"OFERTA_ESPN_PREPARTIDO"}
                def add(market,price,**other):
                    if price is None:return
                    rows.append({**base,"market":market,"price":price,**other})
                ml=offer.get("moneyline") or {}
                for side,team in (("home",game["home"]),("away",game["away"])):
                    add("h2h",_decimal_from_american(_source_line(ml,side,"odds")),team=team)
                spread=offer.get("pointSpread") or {}
                for side,team in (("home",game["home"]),("away",game["away"])):
                    point=_number(_source_line(spread,side,"line"))
                    if point is None or not -45<=point<=45:continue
                    add("spreads",_decimal_from_american(_source_line(spread,side,"odds")),
                        team=team,point=point)
                totals=offer.get("total") or {}
                for side,prefix in (("over","o"),("under","u")):
                    point=_number(_source_line(totals,side,"line"),prefix)
                    if point is None or not 140<=point<=330:continue
                    add("totals",_decimal_from_american(_source_line(totals,side,"odds")),
                        direction=side,point=point)
    # Repeat date buckets may contain the same event: never multiply a price.
    unique={}
    for q in rows:
        key=(q["event_id"],q["bookmaker"],q["market"],q.get("team"),
             q.get("direction"),q.get("point"))
        unique[key]=q
    return list(unique.values())
