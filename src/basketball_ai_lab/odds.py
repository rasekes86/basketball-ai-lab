"""Disabled-by-default, budgeted The Odds API pregame quotations.

The free plan requires an API key. No key means NO requests. Free main-game
markets: h2h, spreads and totals. NBA player props need per-event queries
and are intentionally NOT queried here (protect free monthly credits).
"""
import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from .teams import canonical
from .transform import time_utc
from .model import normal_cdf

API_URL="https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
MARKETS=("h2h","spreads","totals")
REQUEST_COST_BUDGET=3
MAX_CREDITS_PER_MONTH=100  # local safeguard, not the provider limit (500)

def fetch_snapshot(key,now,state,fetch=None):
    """At most one three-market, one-region snapshot per UTC day."""
    if not key:return {"status":"SIN_CLAVE","quotes":[],"state":state}
    day=now.strftime("%Y-%m-%d");month=now.strftime("%Y-%m")
    spent=state.get("odds_budget",{})
    used=spent.get("used",0) if spent.get("month")==month else 0
    if state.get("odds_day")==day:
        return {"status":"YA_CONSULTADO_HOY","quotes":[],"state":state}
    if used+REQUEST_COST_BUDGET>MAX_CREDITS_PER_MONTH:
        return {"status":"CUPO_INTERNO_AGOTADO","quotes":[],"state":state}
    # Consume our internal budget conservatively even if the HTTP request fails.
    attempted={**state,"odds_day":day,"odds_budget":
               {"month":month,"used":used+REQUEST_COST_BUDGET}}
    query=urlencode({"apiKey":key,"regions":"us","markets":",".join(MARKETS),
                     "oddsFormat":"decimal","dateFormat":"iso"})
    try:
        if fetch:
            payload,headers=fetch(API_URL+"?"+query)
        else:
            req=Request(API_URL+"?"+query,headers={"Accept":"application/json",
                        "User-Agent":"BasketballAILab/0.3"})
            with urlopen(req,timeout=12) as response:
                payload=json.loads(response.read(2_000_000))
                headers=dict(response.headers.items())
    except Exception:
        return {"status":"PROVEEDOR_NO_DISPONIBLE","quotes":[],"state":attempted}
    if not isinstance(payload,list):
        return {"status":"RESPUESTA_INVALIDA","quotes":[],"state":attempted}
    usage={str(k).lower():v for k,v in headers.items()}
    try:credits=int(usage.get("x-requests-last",REQUEST_COST_BUDGET))
    except (TypeError,ValueError):credits=REQUEST_COST_BUDGET
    # Never reduce the internal debit below the expected three-market cost.
    credits=max(REQUEST_COST_BUDGET,credits)
    next_state={**state,"odds_day":day,
                "odds_budget":{"month":month,"used":used+credits,
                    "last_remaining":usage.get("x-requests-remaining")}}
    quotes=[]
    for event in payload:
        if not isinstance(event,dict):continue
        home=canonical(event.get("home_team"));away=canonical(event.get("away_team"))
        kick=time_utc(event.get("commence_time"))
        if not home or not away or home==away or not kick or kick<=now:continue
        for book in event.get("bookmakers") or []:
            if not isinstance(book,dict) or not book.get("key"):continue
            for market in book.get("markets") or []:
                if not isinstance(market,dict) or market.get("key") not in MARKETS:continue
                kind=market["key"]
                updated=time_utc(market.get("last_update") or book.get("last_update"))
                if not updated or updated>now or updated>=kick:continue
                for item in market.get("outcomes") or []:
                    if not isinstance(item,dict):continue
                    try:price=float(item.get("price"))
                    except (ValueError,TypeError):continue
                    if not 1.01<=price<=100:continue
                    quote={"provider":"The Odds API","event_id":str(event.get("id") or ""),
                        "home":home,"away":away,"start_utc":kick.isoformat(),
                        "bookmaker":book["key"],"market":kind,"price":price,
                        "updated_utc":updated.isoformat(),"captured_utc":now.isoformat(),
                        "source":"OFERTA_API_PREPARTIDO"}
                    if kind=="h2h":
                        team=canonical(item.get("name"))
                        if team not in (home,away):continue
                        quote["team"]=team
                    elif kind=="spreads":
                        team=canonical(item.get("name"))
                        if team not in (home,away):continue
                        try:point=float(item["point"])
                        except (KeyError,ValueError,TypeError):continue
                        if not -45<=point<=45:continue
                        quote.update(team=team,point=point)
                    else:
                        side=str(item.get("name") or "").lower()
                        if side not in ("over","under"):continue
                        try:point=float(item["point"])
                        except (KeyError,ValueError,TypeError):continue
                        if not 140<=point<=330:continue
                        quote.update(direction=side,point=point)
                    quotes.append(quote)
    return {"status":"OK","quotes":quotes,"state":next_state}

def choose_extra(game,picks,quotes,now,baseline=None):
    """One offered >1.50, unambiguous pregame selection; never a fake price.

    As a safeguard, a genuinely independent market is preferred over
    duplicating the frozen winner pick. Experimental probabilities/EV are
    NOT calibrated and should not be interpreted as a validated edge.
    """
    start=time_utc(game.get("start_utc"))
    if not start or now>=start:return None
    primary=next((p for p in picks if p.get("market")=="winner"),None)
    baseline=baseline or picks
    anchor=next((p for p in baseline if p.get("market")=="winner"),None)
    hp=next((p for p in baseline if p.get("market")=="handicap"),None)
    tp=next((p for p in baseline if p.get("market")=="total"),None)
    if not anchor:return None
    winner=anchor.get("contract",{}).get("team")
    win_prob=float(anchor.get("probability") or 0)
    if winner not in (game["home"],game["away"]):return None
    full_diff=float(hp.get("estimated") if hp else anchor.get("estimated")) if (hp and hp.get("estimated") is not None) or anchor.get("estimated") is not None else None
    # Winner rows store projected home-away point margin.
    full_total=float(tp["estimated"]) if tp else None
    eligible=[]
    for q in quotes:
        if q.get("home")!=game["home"] or q.get("away")!=game["away"]:continue
        quote_start=time_utc(q.get("start_utc"))
        if not quote_start or abs((quote_start-start).total_seconds())>3600:continue
        stamp=time_utc(q.get("updated_utc"));captured=time_utc(q.get("captured_utc"))
        if not q.get("event_id") or not stamp or not captured:continue
        if not (stamp<=captured<=now<start):continue
        try:price=float(q.get("price"))
        except (TypeError,ValueError):continue
        if not 1.50<price<=30:continue
        kind=q.get("market","h2h")
        if kind=="h2h":
            team=q.get("team")
            if team not in (game["home"],game["away"]):continue
            p=win_prob if team==winner else 1-win_prob
            contract={"type":"winner","team":team}
            selection="Gana "+team
        elif kind=="spreads":
            if full_diff is None:continue
            team=q.get("team")
            if team not in (game["home"],game["away"]):continue
            point=q.get("point")
            if not isinstance(point,(int,float)):continue
            if team==game["home"]:
                p=normal_cdf((full_diff+point)/15.5)
            else:
                p=normal_cdf((-full_diff+point)/15.5)
            margin=-point if team==game["home"] else point
            contract={"type":"handicap","side":"home" if team==game["home"] else "away",
                      "home_margin_line":margin}
            selection=f"{team} {point:+g} puntos (hándicap)"
        elif kind=="totals":
            if full_total is None:continue
            direction=q.get("direction");point=q.get("point")
            if direction not in ("over","under") or not isinstance(point,(float,int)):continue
            p=normal_cdf((full_total-point)/18.5)
            if direction=="under":p=1-p
            contract={"type":"total","direction":direction,"line":point}
            selection=f"{direction.upper()} {point:g} puntos totales"
        else:continue
        if not .0<p<1.0:continue
        ev=p*price-1
        if p>=.53 and ev>=.025:eligible.append((ev,p,q,selection,contract))
    if not eligible:return None
    ev,p,q,selection,contract=max(eligible,key=lambda x:(x[0],x[1],x[2]["bookmaker"]))
    return {"id":game["id"]+"|extra","event_id":game["id"],
        "created_utc":now.isoformat(),"start_utc":game["start_utc"],
        "home":game["home"],"away":game["away"],
        "market":"extra_"+q.get("market","h2h"),"selection":selection,
        "probability":round(p,6),"contract":contract,
        "real_price":q["price"],"real_price_status":"OFRECIDA_API_REGISTRADA",
        "bookmaker":q["bookmaker"],"provider":q["provider"],
        "quote_updated_utc":q["updated_utc"],"captured_utc":q["captured_utc"],
        "quote_event_id":q["event_id"],"estimated_ev":round(ev,4),
        "status":"PENDIENTE","result":None,"quality":"NO_CALIBRADO",
        "retrospective":False}
