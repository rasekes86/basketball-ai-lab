"""Conservative, key-free ESPN NBA *team* box-score enrichment.

Never infer a statistic that is absent from a provider response. Historical
statistics are eligible for a prediction only if the game finished well before
that prediction and the summary was captured before the prediction timestamp.
"""
from collections import defaultdict
from datetime import timedelta
from statistics import mean, stdev
from .teams import canonical
from .transform import time_utc

STAT_KEYS={
    "threes": ("threePointFieldGoalsMade", "threePointFieldGoalsMade-threePointFieldGoalsAttempted", "threePointersMade"),
    "rebounds": ("totalRebounds", "rebounds"),
    "assists": ("assists",),
}

def _count(value, split_pair=False):
    if isinstance(value, bool) or value is None:return None
    raw=str(value).strip()
    if split_pair:raw=raw.split('-',1)[0].strip()
    if not raw.isdigit():return None
    n=int(raw)
    return n if 0<=n<=120 else None

def parse_summary(payload, fixture, captured):
    """Return None on any structural/team mismatch, never a synthetic box score."""
    if not isinstance(payload,dict) or fixture.get('status')!='FINAL':return None
    header=payload.get('header') or {}
    if header.get('id') is not None and str(header['id'])!=str(fixture['id']):return None
    box=(payload.get('boxscore') or {}).get('teams') or []
    if not isinstance(box,list):return None
    teams={}
    for record in box:
        if not isinstance(record,dict):continue
        t=record.get('team') or {}
        code=canonical(t.get('abbreviation') or t.get('displayName')) if isinstance(t,dict) else None
        if code not in (fixture.get('home'),fixture.get('away')) or code in teams:continue
        values={}
        for entry in record.get('statistics') or []:
            if isinstance(entry,dict) and isinstance(entry.get('name'),str):
                values[entry['name']]=entry.get('displayValue',entry.get('value'))
        stats={}
        for metric,keys in STAT_KEYS.items():
            for key in keys:
                val=_count(values.get(key),'-' in key)
                if val is not None:
                    stats[metric]=val;break
        if stats:teams[code]=stats
    if set(teams)!={fixture['home'],fixture['away']}:return None
    return {'id':str(fixture['id']),'start_utc':fixture['start_utc'],
            'retrieved_utc':captured.isoformat(),'home':fixture['home'],
            'away':fixture['away'],'teams':teams,'source':'ESPN summary'}

def matchup_form(fixture,games,boxscores,now,min_games=5):
    """One record per confirmed past match; no post-archive or future leakage."""
    history=defaultdict(list)
    for id_,b in boxscores.items():
        g=games.get(id_)
        if not g or g.get('status')!='FINAL' or id_!=b.get('id'):continue
        tip=time_utc(g.get('start_utc'));captured=time_utc(b.get('retrieved_utc'))
        if not tip or not captured or tip+timedelta(hours=5)>=now or captured>now:continue
        if b.get('start_utc')!=g.get('start_utc'):continue
        if (b.get('home'),b.get('away'))!=(g.get('home'),g.get('away')):continue
        team_stats=b.get('teams') or {}
        if not isinstance(team_stats,dict):continue
        for code,other in ((g['home'],g['away']),(g['away'],g['home'])):
            if not isinstance(team_stats.get(code),dict) or not isinstance(team_stats.get(other),dict):continue
            history[code].append((tip,team_stats[code],team_stats[other]))
    estimates={}
    for code in (fixture['home'],fixture['away']):
        data=sorted(history[code],key=lambda row:row[0])[-12:]
        estimates[code]={}
        for stat in STAT_KEYS:
            scored=[float(x[1][stat]) for x in data if stat in x[1] and stat in x[2]]
            allowed=[float(x[2][stat]) for x in data if stat in x[1] and stat in x[2]]
            if len(scored)>=min_games and len(allowed)>=min_games:
                estimates[code][stat]={'made':mean(scored),'allowed':mean(allowed),
                                        'n':len(scored),'sd':max(2.5,stdev(scored)) if len(scored)>1 else 4.0}
    return estimates
