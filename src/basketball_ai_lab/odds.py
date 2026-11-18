"""Optional, disabled-by-default single daily price snapshot from The Odds API.

No key = ZERO calls. One market/region request costs provider credits;
actual free-plan market availability must be checked when enabled.
"""
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from .teams import canonical
from .transform import time_utc

API_URL="https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
MAX_CREDITS_PER_MONTH=100  # budget, NOT a guarantee of cost; fail closed

def fetch_snapshot(key,now,state,fetch=None):
    """One request a day; h2h only; never log the secret."""
    if not key:return {"status":"SIN_CLAVE","quotes":[],"state":state}
    day=now.strftime("%Y-%m-%d")
    month=now.strftime("%Y-%m")
    last=state.get("odds_day")
    spent=state.get("odds_budget",{})
    used=spent.get("used",0) if spent.get("month")==month else 0
    if last==day:return {"status":"YA_CONSULTADO_HOY","quotes":[],"state":state}
    if used>=MAX_CREDITS_PER_MONTH:
        return {"status":"CUPO_INTERNO_AGOTADO","quotes":[],"state":state}
    attempted={**state,"odds_day":day,"odds_budget":{"month":month,"used":used+1}}
    query=urlencode({"apiKey":key,"regions":"us","markets":"h2h","oddsFormat":"decimal","dateFormat":"iso"})
    # The provider URL contains a secret: never print exceptions, URLs or headers.
    try:
        if fetch:
            payload,headers=fetch(API_URL+"?"+query)
        else:
            req=Request(API_URL+"?"+query,headers={"Accept":"application/json","User-Agent":"BasketballAILab/0.1"})
            with urlopen(req,timeout=12) as response:
                payload=json.loads(response.read(2_000_000))
                headers=dict(response.headers.items())
    except Exception:
        return {"status":"PROVEEDOR_NO_DISPONIBLE","quotes":[],"state":attempted}
    if not isinstance(payload,list):
        return {"status":"RESPUESTA_INVALIDA","quotes":[],"state":attempted}
    usage={str(k).lower():v for k,v in headers.items()}
    try: credits=int(usage.get("x-requests-last",1))
    except (TypeError,ValueError): credits=1
    credits=max(1,credits)
    next_state={**state,"odds_day":day,"odds_budget":{"month":month,"used":used+credits,
                   "last_remaining":usage.get("x-requests-remaining")}}
    quotes=[]
    for event in payload:
        home=canonical(event.get("home_team"));away=canonical(event.get("away_team"))
        kick=time_utc(event.get("commence_time"))
        if not home or not away or home==away or not kick or kick<=now:continue
        for bookmaker in event.get("bookmakers") or []:
            if not bookmaker.get("key"):continue
            for market in bookmaker.get("markets") or []:
                if market.get("key")!="h2h":continue
                updated=time_utc(market.get("last_update") or bookmaker.get("last_update"))
                if not updated or updated>=kick:continue
                for item in market.get("outcomes") or []:
                    team=canonical(item.get("name"))
                    try: price=float(item.get("price"))
                    except (TypeError,ValueError):continue
                    if team not in (home,away) or not 1.01<=price<=100:continue
                    quotes.append({"provider":"The Odds API","event_id":str(event.get("id") or ""),
                       "home":home,"away":away,"start_utc":kick.isoformat(),
                       "bookmaker":bookmaker["key"],"market":"h2h","team":team,
                       "price":price,"updated_utc":updated.isoformat(),
                       "captured_utc":now.isoformat(),"source":"OFERTA_API_PREPARTIDO"})
    return {"status":"OK","quotes":quotes,"state":next_state}

def choose_extra(game,picks,quotes,now):
    """Freeze at most one fully identified real pregame moneyline >1.50.

    This is experimental, not evidence of a profitable investment.
    """
    start=time_utc(game.get("start_utc"))
    if not start or now>=start:return None
    win=next((p for p in picks if p["market"]=="winner"),None)
    if not win:return None
    selected=win["contract"]["team"]
    p=float(win["probability"])
    # No stale/crossed matches; price is associated to the EXACT matchup.
    eligible=[]
    for q in quotes:
        if q.get("home")!=game["home"] or q.get("away")!=game["away"]:continue
        quote_start=time_utc(q.get("start_utc"))
        if not quote_start or abs((quote_start-start).total_seconds())>3600:continue
        stamp=time_utc(q.get("updated_utc"))
        captured=time_utc(q.get("captured_utc"))
        # An API price is admissible only with a real source event identifier
        # and a capture made AFTER the provider timestamp but BEFORE tip-off.
        if not q.get("event_id") or not stamp or not captured:continue
        if not (stamp<=captured<=now<start):continue
        try:price=float(q.get("price"))
        except (TypeError,ValueError):continue
        if q.get("team")!=selected or not 1.50<price<=30:continue
        # Price from this bookmaker on this market only, not a synthetic best price.
        ev=p*price-1
        if p>=.53 and ev>=.025:eligible.append((ev,q))
    if not eligible:return None
    _,q=max(eligible,key=lambda x:(x[0],x[1]["bookmaker"]))
    return {"id":game["id"]+"|extra","event_id":game["id"],
        "created_utc":now.isoformat(),"start_utc":game["start_utc"],
        "home":game["home"],"away":game["away"],"market":"extra_h2h",
        "selection":"Gana "+selected,"probability":p,"contract":{"type":"winner","team":selected},
        "real_price":q["price"],"real_price_status":"OFRECIDA_API_REGISTRADA",
        "bookmaker":q["bookmaker"],"provider":q["provider"],"quote_updated_utc":q["updated_utc"],
        "captured_utc":q["captured_utc"],"quote_event_id":q["event_id"],
        "estimated_ev":round(p*q["price"]-1,4),"status":"PENDIENTE","result":None,
        "quality":"NO_CALIBRADO","retrospective":False}
