"""Explainable NBA model v0: regularized rolling team scoring.

Not calibrated for betting. A three-market Top3 is frozen BEFORE tip-off.
"""
from collections import defaultdict
from datetime import datetime,timezone
from math import erf,sqrt
from statistics import mean
from .transform import time_utc

MIN_GAMES=5
HALF_LIFE_DAYS=24

def normal_cdf(value):
    return .5*(1+erf(value/sqrt(2)))

def weighted(values):
    total=sum(weight for value,weight in values)
    return sum(value*weight for value,weight in values)/total if total else None

def ratings(games, at):
    history=defaultdict(list)
    totals=[]
    at=at.astimezone(timezone.utc)
    for game in games.values():
        date=time_utc(game.get("start_utc"))
        if game.get("status")!="FINAL" or not date or date>=at:continue
        a,b=game.get("home_score"),game.get("away_score")
        if not isinstance(a,int) or not isinstance(b,int):continue
        if not 50<=a<=200 or not 50<=b<=200:continue
        home,away=game["home"],game["away"]
        age=max(0,(at-date).total_seconds()/86400)
        w=2**(-age/HALF_LIFE_DAYS)
        history[home].append((date,a,b,w));history[away].append((date,b,a,w))
        totals.extend((a,b))
    baseline=mean(totals) if len(totals)>=40 else 112.0
    outcome={}
    for team,rows in history.items():
        latest=sorted(rows,key=lambda row:row[0])[-14:]
        # Prior equivalent to ~7 matches to resist early-season noise.
        weight=sum(x[3] for x in latest)
        off=(sum(x[1]*x[3] for x in latest)+7*baseline)/(weight+7)
        defense=(sum(x[2]*x[3] for x in latest)+7*baseline)/(weight+7)
        outcome[team]={"games":len(rows),"offense":off,"defense":defense}
    return baseline,outcome

def _pick(game,market,selection,probability,contract,estimate,asof):
    return {"id":f'{game["id"]}|{market}',"event_id":game["id"],
            "start_utc":game["start_utc"],"created_utc":asof.isoformat(),
            "home":game["home"],"away":game["away"],"market":market,
            "selection":selection,"probability":round(probability,6),
            "fair_odds":round(1/probability,3),"contract":contract,
            "estimated":round(estimate,2),"status":"PENDIENTE",
            "result":None,"real_price":None,"real_price_status":"SIN_CUOTA_OFRECIDA",
            "model":"ROLLING_POINTS_V1","quality":"NO_CALIBRADO","retrospective":False}

def forecast(game,games,at):
    start=time_utc(game.get("start_utc"))
    if game.get("status")=="FINAL" or not start or start<=at:
        return [],"FUERA_DE_VENTANA"
    league,team=ratings(games,at)
    home=team.get(game.get("home"));away=team.get(game.get("away"))
    if not home or not away or min(home["games"],away["games"])<MIN_GAMES:
        return [],"MUESTRA_INSUFICIENTE"
    # Predict each club using its own attack and opponent defensive strength.
    ph=.48*home["offense"]+.52*away["defense"]+2.0
    pa=.48*away["offense"]+.52*home["defense"]-2.0
    diff=ph-pa
    combined=ph+pa
    sd_diff=15.5
    sd_total=18.5
    win_prob=normal_cdf(diff/sd_diff)
    winner=game["home"] if win_prob>=.5 else game["away"]
    pwin=max(win_prob,1-win_prob)
    picks=[_pick(game,"winner",f"Gana {winner}",pwin,
       {"type":"winner","team":winner},diff,at)]
    # Theoretical lines are 5-point steps, NOT bookmaker prices.
    total_line=5*round((combined-.5)/5)+.5
    over=normal_cdf((combined-total_line)/sd_total)
    direction="over" if over>=.5 else "under"
    picks.append(_pick(game,"total",f"{direction.upper()} {total_line:g} puntos",
            max(over,1-over),{"type":"total","direction":direction,"line":total_line},combined,at))
    handicap_line=5*round((diff-.5)/5)+.5
    home_cover=normal_cdf((diff-handicap_line)/sd_diff)
    cover="home" if home_cover>=.5 else "away"
    picks.append(_pick(game,"handicap",f"{cover.upper()} {handicap_line:+g} margen (teórico)",
            max(home_cover,1-home_cover),
            {"type":"handicap","side":cover,"home_margin_line":handicap_line},diff,at))
    return picks,"ARCHIVABLE"

def settle_one(pick,game):
    if game.get("status")!="FINAL":return None
    h,a=game.get("home_score"),game.get("away_score")
    if not isinstance(h,int) or not isinstance(a,int):return None
    c=pick.get("contract") or {}
    if c.get("type")=="winner":
        if h==a:return None
        win=(game["home"] if h>a else game["away"])==c.get("team")
    elif c.get("type")=="total":
        total=h+a
        if total==c.get("line"):return None
        win=total>c["line"] if c.get("direction")=="over" else total<c["line"]
    elif c.get("type")=="handicap":
        diff=h-a
        if diff==c.get("home_margin_line"):return None
        home_covers=diff>c["home_margin_line"]
        win=home_covers if c.get("side")=="home" else not home_covers
    else:return None
    return bool(win)
