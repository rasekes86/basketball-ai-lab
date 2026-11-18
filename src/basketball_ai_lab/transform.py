"""Normalize ESPN schedule + team catalogue defensively."""
from datetime import datetime,timezone
from urllib.parse import urlsplit
from .teams import canonical,NBA_TEAMS

ALLOWED_LOGO_HOSTS={"a.espncdn.com", "a1.espncdn.com", "cdn.nba.com"}

def time_utc(value):
    if not value: return None
    try:
        result=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError,ValueError,OverflowError): return None

def logo_url(value):
    """Trust exact known image hosts; reject fragments, credentials and unsafe URLs."""
    if not isinstance(value,str) or len(value)>2048: return None
    try:
        parsed=urlsplit(value)
        return (value if parsed.scheme=="https"
                and parsed.hostname in ALLOWED_LOGO_HOSTS
                and not parsed.username and not parsed.password
                and parsed.port in (None,443)
                and not parsed.fragment and parsed.path.startswith("/")
                else None)
    except ValueError:
        return None

def game_score(value):
    """ESPN returns text scores in scoreboard, objects in some newer feeds."""
    if isinstance(value,dict):
        value=value.get("value",value.get("displayValue"))
    if isinstance(value,bool) or value in (None,""):return None
    try:
        parsed=float(value)
        return int(parsed) if parsed.is_integer() and 0<=parsed<=250 else None
    except (TypeError,ValueError,OverflowError):
        return None

def _regular_or_playoffs(event):
    # Preseason/summer league scorelines must NEVER alter a regular-season model.
    season=event.get("season") or {}
    phase=season.get("type")
    if isinstance(phase,dict):phase=phase.get("id")
    if phase is not None and str(phase) not in ("2","3"):
        return False
    return True

def normalize_teams(payload):
    """Use actual provider-supplied logo URL; never construct an unverified image."""
    if not isinstance(payload,dict):return {}
    root=payload.get("sports") or []
    items=[]
    for sport in root if isinstance(root,list) else []:
        if not isinstance(sport,dict):continue
        for league in sport.get("leagues") or []:
            if isinstance(league,dict) and isinstance(league.get("teams"),list):
                items.extend(league["teams"])
    if not items: items=payload.get("teams") or []
    result={}
    for item in items if isinstance(items,list) else []:
        if not isinstance(item,dict):continue
        t=item.get("team") or item
        if not isinstance(t,dict):continue
        abbreviation=canonical(t.get("abbreviation") or t.get("displayName"))
        if not abbreviation: continue
        logos=t.get("logos") or []
        candidates=(x.get("href") for x in logos if isinstance(x,dict)) if isinstance(logos,list) else ()
        image=next((url for item_url in candidates if (url:=logo_url(item_url))),None)
        image=image or logo_url(t.get("logo"))
        result[abbreviation]={"id":str(t.get("id") or ""),"abbr":abbreviation,
               "name":NBA_TEAMS[abbreviation],"logo":image,"source":"ESPN"}
    return result

def normalize_games(payload):
    games={}
    for event in (payload.get("events") or []) if isinstance(payload.get("events"),list) else []:
        if not isinstance(event,dict) or not _regular_or_playoffs(event):continue
        comps=event.get("competitions") or []
        if not isinstance(comps,list):continue
        if len(comps)!=1: continue
        comp=comps[0]
        if not isinstance(comp,dict):continue
        teams={}
        for competitor in comp.get("competitors") or []:
            if not isinstance(competitor,dict):continue
            team=competitor.get("team") or {}
            if not isinstance(team,dict):continue
            key=canonical(team.get("abbreviation") or team.get("displayName"))
            side=competitor.get("homeAway")
            if not key or side not in ("home","away") or side in teams: continue
            score=game_score(competitor.get("score"))
            teams[side]={"abbr":key,"name":NBA_TEAMS[key],"score":score,
                         "logo":logo_url(team.get("logo"))}
        if len(teams)!=2 or teams["home"]["abbr"]==teams["away"]["abbr"]: continue
        dt=time_utc(event.get("date") or comp.get("date"))
        if not dt: continue
        event_status=event.get("status") or {}
        comp_status=comp.get("status") or {}
        status=(event_status if isinstance(event_status,dict) else {}).get("type") or {}
        if not status:status=(comp_status if isinstance(comp_status,dict) else {}).get("type") or {}
        if not isinstance(status,dict):status={}
        completed=status.get("completed") is True
        label=str(status.get("name") or "").upper()
        if label and ("FINAL" not in label and "END" not in label):
            completed=False  # postponed, cancelled, suspended, etc.
        home=teams["home"];away=teams["away"]
        # ESPN can report games as completed with no scores: never settle those.
        is_final=completed and home["score"] is not None and away["score"] is not None
        games[str(event.get("id") or "")]={
            "id":str(event.get("id") or ""),"start_utc":dt.isoformat(),
            "home":home["abbr"],"away":away["abbr"],
            "home_score":home["score"] if is_final else None,
            "away_score":away["score"] if is_final else None,
            "status":"FINAL" if is_final else ("FINISHED_UNVERIFIED" if completed else "SCHEDULED"),
            "logos":{home["abbr"]:home["logo"],away["abbr"]:away["logo"]},
            "source":"ESPN"
        }
    return {k:v for k,v in games.items() if k and k!="None"}
