"""Explainable NBA model v0: regularized rolling team scoring.

Not calibrated for betting. A three-market Top3 is frozen BEFORE tip-off.
"""
from collections import defaultdict
from datetime import datetime,timezone
from math import erf,sqrt
from statistics import mean
from .advanced import matchup_form
from .transform import time_utc
from .model_v3 import cautious_probability, matchup_context, VERSION

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
    probability=cautious_probability(probability)
    return {"id":f'{game["id"]}|{market}',"event_id":game["id"],
            "start_utc":game["start_utc"],"created_utc":asof.isoformat(),
            "home":game["home"],"away":game["away"],"market":market,
            "selection":selection,"probability":round(probability,6),
            "fair_odds":round(1/probability,3),"contract":contract,
            "estimated":round(estimate,2),"status":"PENDIENTE",
            "result":None,"real_price":None,"real_price_status":"SIN_CUOTA_OFRECIDA",
            "model":"ROLLING_POINTS_CONTEXT_V3","model_version":VERSION,"quality":"EXPERIMENTAL_NO_CALIBRADO","retrospective":False}

# Same market-selection policy as Football AI Lab, adapted to NBA statistics.
# These are fixed/theoretical statistical lines, NOT sportsbook quotes.
MIN_TOP_PROBABILITY=.55
MIN_TOP_FAIR_ODDS=1.15
MAX_TOP=3

def _eligible_for_top(row):
    p=float(row.get("probability") or 0)
    return MIN_TOP_PROBABILITY<=p<1 and 1/p>=MIN_TOP_FAIR_ODDS

def _top_by_probability(candidates):
    """Three highest estimated probabilities; max one per distinct family.

    Unlike the old NBA algorithm, a winner is NEVER a mandatory anchor.
    A shortage of eligible candidates is shown honestly as fewer than 3.
    """
    best={}
    for row in candidates:
        if not _eligible_for_top(row):continue
        market=row["market"]  # One family per market, regardless of team/line.
        if market not in best or row["probability"]>best[market]["probability"]:
            best[market]=row
    return sorted(best.values(),key=lambda r:(-r["probability"],r["market"],r["selection"]))[:MAX_TOP]


def forecast(game,games,at,boxscores=None):
    start=time_utc(game.get("start_utc"))
    if game.get("status")=="FINAL" or not start or start<=at:
        return [],"FUERA_DE_VENTANA"
    league,team=ratings(games,at)
    home=team.get(game.get("home"));away=team.get(game.get("away"))
    if not home or not away or min(home["games"],away["games"])<MIN_GAMES:
        return [],"MUESTRA_INSUFICIENTE"
    ph=.48*home["offense"]+.52*away["defense"]+2.0
    pa=.48*away["offense"]+.52*home["defense"]-2.0
    rest_h,rest_a,sd_diff,sd_total=matchup_context(games,at,game)
    ph+=rest_h; pa+=rest_a
    diff=ph-pa
    combined=ph+pa
    win_prob=normal_cdf(diff/sd_diff)
    winner=game["home"] if win_prob>=.5 else game["away"]
    pwin=max(win_prob,1-win_prob)
    candidates=[_pick(game,"winner",f"Gana {winner}",pwin,
       {"type":"winner","team":winner},diff,at)]

    # Comparable half-point lines from a bounded grid of ordinary NBA totals.
    # The grid and selection are determined BEFORE tipoff; no price guessing.
    for line in (199.5,204.5,209.5,214.5,219.5,224.5,229.5,234.5,
                 239.5,244.5,249.5,254.5,259.5):
        if abs(combined-line)>1.10*sd_total:continue
        over=normal_cdf((combined-line)/sd_total)
        for direction,p in (("over",over),("under",1-over)):
            if not MIN_TOP_PROBABILITY<=p<1:continue
            candidates.append(_pick(game,"total",f"{direction.upper()} {line:g} puntos (teórico)",
                  p,{"type":"total","direction":direction,"line":line},combined,at))
    for line in (-15.5,-12.5,-9.5,-6.5,-3.5,-0.5,2.5,5.5,8.5,11.5,14.5):
        if abs(diff-line)>1.10*sd_diff:continue
        home_cover=normal_cdf((diff-line)/sd_diff)
        for side,p in (("home",home_cover),("away",1-home_cover)):
            if not MIN_TOP_PROBABILITY<=p<1:continue
            name=game["home"] if side=="home" else game["away"]
            # 'home_margin_line' is the required home-away margin, not the
            # bookmaker handicap point (see settle_one).
            candidates.append(_pick(game,"handicap",
                f"{name}: {'+' if (line if side=='away' else -line)>0 else ''}{(line if side=='away' else -line):g} puntos (hándicap teórico)",
                p,{"type":"handicap","side":side,"home_margin_line":line},diff,at))
    if boxscores:
        summaries=matchup_form(game,games,boxscores,at)
        for stat,market,caption,minimum_sd,lines in (
            ("threes","team_threes","triples del equipo",3.5,
             (7.5,9.5,11.5,13.5,15.5,17.5,19.5,21.5)),
            ("rebounds","team_rebounds","rebotes del equipo",5.5,
             (29.5,33.5,37.5,41.5,45.5,49.5,53.5,57.5)),
            ("assists","team_assists","asistencias del equipo",4.5,
             (16.5,19.5,22.5,25.5,28.5,31.5,34.5,37.5)),
        ):
            for code,opponent in ((game["home"],game["away"]),
                                  (game["away"],game["home"])):
                own=summaries.get(code,{}).get(stat)
                opp=summaries.get(opponent,{}).get(stat)
                if not own or not opp:continue
                expectation=.55*own["made"]+.45*opp["allowed"]
                sd=max(minimum_sd,float(own["sd"]))
                for line in lines:
                    if abs(expectation-line)>1.10*sd:continue
                    over=normal_cdf((expectation-line)/sd)
                    for direction,p in (("over",over),("under",1-over)):
                        if not MIN_TOP_PROBABILITY<=p<1:continue
                        row=_pick(game,market,
                          f"{code}: {direction.upper()} {line:g} {caption} (teórico)",
                          p,{"type":"team_stat","stat":stat,"team":code,
                             "direction":direction,"line":line},expectation,at)
                        row["model"]="ROLLING_TEAM_STATS_V2"
                        row["sample_games"]=min(own["n"],opp["n"])
                        candidates.append(row)
    picks=_top_by_probability(candidates)
    return picks,("ARCHIVABLE" if picks else "SIN_MERCADOS_APTOS")


def reference_forecast(game,games,at):
    """The existing independent score model for pricing an optional extra.

    The Top 3 selector may not contain winner/total/handicap; pricing the
    fourth selection must not depend on which categories won that ranking.
    This reference is never archived as an additional Top 3 candidate.
    """
    start=time_utc(game.get("start_utc"))
    if not start or start<=at:return []
    _,team=ratings(games,at)
    h,a=team.get(game.get("home")),team.get(game.get("away"))
    if not h or not a or min(h["games"],a["games"])<MIN_GAMES:return []
    ph=.48*h["offense"]+.52*a["defense"]+2.0
    pa=.48*a["offense"]+.52*h["defense"]-2.0
    rest_h,rest_a,sd_diff,sd_total=matchup_context(games,at,game)
    ph+=rest_h;pa+=rest_a
    diff=ph-pa
    combined=ph+pa
    probability=normal_cdf(diff/sd_diff)
    winner=game["home"] if probability>=.5 else game["away"]
    result=[_pick(game,"winner",f"Gana {winner}",max(probability,1-probability),
        {"type":"winner","team":winner},diff,at)]
    total_line=5*round((combined-.5)/5)+.5
    direction="over" if combined>total_line else "under"
    p=normal_cdf((combined-total_line)/sd_total)
    result.append(_pick(game,"total",f"{direction.upper()} {total_line:g} puntos (referencia)",
        max(p,1-p),{"type":"total","direction":direction,"line":total_line},combined,at))
    return result

def is_void_line(pick,game,boxscore=None):
    """A verified exact push refunds the stake, not a missing result.

    Main-market integer totals and integer handicap margins can push. For a
    team-stat market, require the exact verified ESPN team count first.
    """
    if game.get("status")!="FINAL":return False
    h,a=game.get("home_score"),game.get("away_score")
    if type(h) is not int or type(a) is not int:return False
    c=pick.get("contract") or {}
    kind=c.get("type")
    if kind=="total":
        return isinstance(c.get("line"),(int,float)) and h+a==c["line"]
    if kind=="handicap":
        return isinstance(c.get("home_margin_line"),(int,float)) and h-a==c["home_margin_line"]
    if kind=="team_stat":
        if not boxscore or boxscore.get("id")!=game.get("id") or boxscore.get("start_utc")!=game.get("start_utc"):
            return False
        team,metric=c.get("team"),c.get("stat")
        if team not in (game.get("home"),game.get("away")) or metric not in ("threes","rebounds","assists"):
            return False
        value=(boxscore.get("teams") or {}).get(team,{}).get(metric)
        return type(value) is int and isinstance(c.get("line"),(int,float)) and value==c["line"]
    return False


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
