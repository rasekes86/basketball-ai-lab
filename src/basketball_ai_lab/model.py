"""Explainable NBA model v0: regularized rolling team scoring.

Not calibrated for betting. A three-market Top3 is frozen BEFORE tip-off.
"""
from collections import defaultdict
from datetime import datetime,timezone
from math import erf,sqrt
from statistics import mean
from .advanced import matchup_form
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

def forecast(game,games,at,boxscores=None):
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
    # Existing (already archived) selections are immutable in the pipeline.
    # For future fixtures with sufficient *verified* team box scores, offer
    # genuinely different categories, not three renamed points predictions.
    if boxscores:
        summaries=matchup_form(game,games,boxscores,at)
        candidates=[]
        for stat,market,caption,floor_sd in (
            ("threes","team_threes","triples del equipo",3.5),
            ("rebounds","team_rebounds","rebotes del equipo",5.5),
            ("assists","team_assists","asistencias del equipo",4.5),
        ):
            for code,opponent in ((game["home"],game["away"]),
                                  (game["away"],game["home"])):
                own=summaries.get(code,{}).get(stat)
                opp=summaries.get(opponent,{}).get(stat)
                if not own or not opp:continue
                expectation=.55*own["made"]+.45*opp["allowed"]
                # Theoretical half-integer line. Never call this a bookmaker line.
                line=round(expectation)+.5
                sd=max(floor_sd,float(own["sd"]))
                over=normal_cdf((expectation-line)/sd)
                direction="over" if over>=.5 else "under"
                probability=max(over,1-over)
                if probability<.525:continue  # No spurious weak prop.
                selection=f"{code}: {direction.upper()} {line:g} {caption} (teórico)"
                candidate=_pick(game,market,selection,probability,
                    {"type":"team_stat","stat":stat,"team":code,
                     "direction":direction,"line":line},expectation,at)
                candidate["model"]="ROLLING_TEAM_STATS_V2"
                candidate["sample_games"]=min(own["n"],opp["n"])
                candidates.append(candidate)
        # Keep the winner as a comparable anchor and diversify the other two.
        # Do not forcibly publish a prop without a usable team-stat sample.
        if candidates:
            best={}
            for row in candidates:
                kind=row["market"]
                if kind not in best or row["probability"]>best[kind]["probability"]:
                    best[kind]=row
            # A small diversification bonus breaks ties, not probability claims.
            ranked=sorted([*best.values(),*picks[1:]],
                 key=lambda row:(row["probability"]+(.025 if row["market"].startswith("team_") else 0),
                                 row["probability"]),reverse=True)
            selected=[picks[0]]
            if best:
                selected.append(max(best.values(),key=lambda x:x["probability"]))
            for row in ranked:
                if row["market"] not in {p["market"] for p in selected}:
                    selected.append(row)
                if len(selected)==3:break
            picks=selected
    return picks,"ARCHIVABLE"

def settle_one(pick,game,boxscore=None):
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
    elif c.get("type")=="team_stat":
        if not boxscore or boxscore.get("id")!=game.get("id"):
            return None
        if boxscore.get("start_utc")!=game.get("start_utc"):
            return None
        team=c.get("team");metric=c.get("stat")
        if team not in (game.get("home"),game.get("away")) or metric not in ("threes","rebounds","assists"):
            return None
        value=(boxscore.get("teams") or {}).get(team,{}).get(metric)
        if not isinstance(value,int) or isinstance(value,bool):return None
        line=c.get("line")
        if not isinstance(line,(int,float)) or value==line:return None
        win=value>line if c.get("direction")=="over" else value<line
    else:return None
    return bool(win)
