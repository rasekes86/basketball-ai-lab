"""Idempotent NBA ingestion + immutable prospective archives + postgame audit."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import os
from .provider import Client,SourceError
from .transform import normalize_games,normalize_teams,time_utc
from .model import forecast,settle_one
from .odds import fetch_snapshot,choose_extra
from .store import load,save
from .teams import NBA_TEAMS
from .reports import publish

DATA_FILES=("games.json","teams.json","picks.json","extras.json","odds_state.json","review_flags.json","status.json")

def days_for_update(now,initial):
    past=45 if initial else 4
    future=7
    today=now.date()
    return [today+timedelta(days=x) for x in range(-past,future+1)]

def update(output=Path("data"),site=Path("site/data"),now=None,client=None,env=None):
    output=Path(output);site=Path(site)
    env=os.environ if env is None else env
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    client=client or Client(max_calls=65)
    games=load(output/"games.json",{})
    logos=load(output/"teams.json",{})
    picks=load(output/"picks.json",{})
    extras=load(output/"extras.json",{})
    odds_state=load(output/"odds_state.json",{})
    review_flags=load(output/"review_flags.json",{})
    initial=not bool(games)
    successes=0
    provider_failures=[]
    fresh_game_ids=set()
    schedule_events=0
    # Catalogue is refreshed once every 30d (or if absent).
    last=time_utc(logos.get("retrieved_utc"))
    if not logos.get("teams") or not last or (now-last).days>=30:
        try:
            parsed=normalize_teams(client.teams())
            if parsed:
                logos={"retrieved_utc":now.isoformat(),"teams":parsed,"source":"ESPN"}
        except SourceError as exc:
            provider_failures.append("equipos: "+str(exc))
    for day in days_for_update(now,initial):
        try:
            payload=client.scoreboard(day)
            if not isinstance(payload.get("events"),list):
                client.blocked_reason="ESQUEMA_CALENDARIO_INESPERADO"
                raise SourceError("calendario sin lista de eventos")
            current=normalize_games(payload)
            successes+=1
            fresh_game_ids.update(current)
            schedule_events+=len(current)
        except SourceError as exc:
            provider_failures.append(day.isoformat()+": "+str(exc))
            # A 403/429 or 3 network errors trip the provider circuit breaker.
            # No further provider requests until the NEXT daily workflow run.
            if client.blocked_reason:
                break
            continue
        for id_,row in current.items():
            previous=games.get(id_)
            if previous and id_ in review_flags:
                continue  # fail closed until reviewed; never auto-reprice
            has_archive=any(k.startswith(id_+"|") for k in picks) or id_+"|extra" in extras
            if previous:
                altered_sides=(previous.get("home"),previous.get("away")) != (row["home"],row["away"])
                older=time_utc(previous.get("start_utc"))
                newer=time_utc(row.get("start_utc"))
                rescheduled=bool(older and newer and abs((newer-older).total_seconds())>7200)
                changed_final=(previous.get("status")=="FINAL" and row.get("status")=="FINAL"
                               and (previous.get("home_score"),previous.get("away_score"))
                               != (row.get("home_score"),row.get("away_score")))
                if has_archive and (altered_sides or rescheduled or changed_final):
                    reason=("RIVALES_CAMBIADOS" if altered_sides else
                            "FECHA_REPROGRAMADA" if rescheduled else "MARCADOR_FINAL_CORREGIDO")
                    review_flags[id_]={"code":reason,"detected_utc":now.isoformat(),
                                        "start_utc_archived":previous.get("start_utc"),
                                        "start_utc_provider":row.get("start_utc")}
                    # Maintain the original fixture and avoid new settlement.
                    continue
                if previous.get("status")=="FINAL" and row.get("status")!="FINAL":
                    continue
            games[id_]=row
        # Logo fallback comes from the provider's actual event payload.
        team_data=logos.setdefault("teams",{})
        for row in current.values():
            for code,img in (row.get("logos") or {}).items():
                item=team_data.setdefault(code,{"abbr":code,"name":NBA_TEAMS.get(code,code),
                                                "source":"ESPN","id":"","logo":None})
                if img and not item.get("logo"):
                    item["logo"]=img
    if not successes:
        # Critical safety invariant: NEVER archive new picks or pretend the
        # ingestion succeeded when the provider was entirely unavailable.
        raise SourceError("Sin calendarios comprobables: se conserva el estado anterior")
    if not games and not schedule_events:
        raise SourceError("El proveedor respondió, pero no devolvió partidos NBA verificables")
    # A prospective forecast is generated only from already-final games,
    # at the actual creation time, and can never be recalculated in place.
    upcoming=sorted((g for g in games.values() if
          (start:=time_utc(g.get("start_utc"))) and start>now
          and start<now+timedelta(days=7) and g.get("status")=="SCHEDULED"
          and g["id"] not in review_flags),
          key=lambda g:g["start_utc"])
    exclusions={}
    archived=0
    for game in upcoming:
        if all(f'{game["id"]}|{m}' in picks for m in ("winner","total","handicap")):
            continue
        # ESPN's `dates` uses US date buckets: a 01:00 UTC game can appear
        # under the PREVIOUS calendar day in America. Require the fixture ID
        # itself in this run, not a guessed UTC date equivalence.
        if game["id"] not in fresh_game_ids:
            exclusions[game["id"]]="PARTIDO_NO_VERIFICADO_EN_LA_RONDA"
            continue
        proposed,reason=forecast(game,games,now)
        if not proposed:
            exclusions[game["id"]]=reason
            continue
        # All three markets frozen in the same instant; never re-write prior rows.
        for row in proposed:
            if row["id"] not in picks:
                picks[row["id"]]=row
                archived+=1
    # Optional real prices are explicitly off until the user sets one secret.
    odds_status="DESACTIVADO"
    quotes=[]
    if str(env.get("ENABLE_ODDS","")).lower() in ("1","true","yes"):
        feed=fetch_snapshot(str(env.get("ODDS_API_KEY","")).strip(),now,odds_state,
                            fetch=env.get("_ODDS_FETCH_TEST"))
        odds_status=feed["status"]
        quotes=feed["quotes"]
        odds_state=feed["state"]
    new_extras=0
    # If real offers arrive AFTER the main picks but BEFORE start, they may
    # freeze ONE independent extra; after kickoff this is prohibited.
    for game in upcoming:
        id_=game["id"]
        if id_+"|extra" in extras:continue
        game_picks=[picks.get(id_+"|"+m) for m in ("winner","total","handicap")]
        if any(not p for p in game_picks):continue
        candidate=choose_extra(game,game_picks,quotes,now)
        if candidate:
            extras[candidate["id"]]=candidate
            new_extras+=1
    settled=0
    # Settle only the 3 archived markets and the one frozen extra, never
    # every candidate considered during scoring or valuation.
    for row in list(picks.values())+list(extras.values()):
        if row.get("status")!="PENDIENTE":continue
        game=games.get(row.get("event_id"))
        if not game or row.get("event_id") in review_flags:continue
        result=settle_one(row,game)
        if result is not None:
            row["status"]="ACIERTO" if result else "FALLO"
            row["result"]=int(result)
            row["settled_utc"]=now.isoformat()
            settled+=1
    checked=[p for p in picks.values() if p.get("result") in (0,1)]
    extra_checked=[p for p in extras.values() if p.get("result") in (0,1)]
    verified_extra=[p for p in extra_checked if p.get("real_price_status")=="OFRECIDA_API_REGISTRADA"]
    unit_profit=sum(float(p["real_price"])-1 if p["result"]==1 else -1 for p in verified_extra)
    final_count=sum(1 for g in games.values() if g.get("status")=="FINAL")
    market_metrics={}
    for name in ("winner","total","handicap"):
        rows=[p for p in checked if p.get("market")==name]
        market_metrics[name]={
            "evaluated":len(rows),
            "hits":sum(p.get("result")==1 for p in rows),
            "accuracy":round(sum(p.get("result")==1 for p in rows)/len(rows),4) if rows else None,
            "brier":round(sum((float(p["probability"])-int(p["result"]))**2 for p in rows)/len(rows),5) if rows else None
        }
    brier=(sum((float(p["probability"])-int(p["result"]))**2 for p in checked)/len(checked)) if checked else None
    # Only published, non-sensitive facts; no credentials or bookmaker API keys.
    status={"updated_utc":now.isoformat(),"provider":"ESPN (public, undocumented)",
        "source_requests":client.calls,"source_successful_days":successes,
        "source_distinct_games_returned":schedule_events,
        "source_circuit_breaker":client.blocked_reason,
        "source_failures":provider_failures[:15],"source_failed_days":len(provider_failures),
        "games":len(games),"final_games":final_count,"upcoming":len(upcoming),
        "logo_coverage":sum(bool(x.get("logo")) for x in (logos.get("teams") or {}).values()),
        "logo_teams":len(logos.get("teams") or {}),"new_top3_picks":archived,
        "top3_archived":len(picks),"top3_evaluated":len(checked),
        "top3_hits":sum(p["result"]==1 for p in checked),
        "top3_accuracy":round(sum(p["result"]==1 for p in checked)/len(checked),4) if checked else None,
        "top3_brier":round(brier,5) if brier is not None else None,
        "market_metrics":market_metrics,
        "extras_archived":len(extras),"extras_evaluated":len(extra_checked),
        "extras_unit_profit":round(unit_profit,3),"extras_verified_priced":len(verified_extra),
        "new_extras":new_extras,"new_settlements":settled,"odds_status":odds_status,
        "odds_calls_month":(odds_state.get("odds_budget") or {}).get("used",0),
        "no_historical_repricing":True,"quality":"EXPERIMENTAL_NO_CALIBRADO",
        "review_required_count":len(review_flags),
        "review_required":review_flags,
        "notice":"No son apuestas recomendadas; sin garantías. Los Top 3 usan líneas teóricas; ROI solo de cuotas prepartido ofrecidas y registradas.",
        "no_top3_reasons":exclusions}
    # CSV downloads are linked from /site/reports/, NOT /site/data/reports/.
    status.update(publish(output,site.parent,games,picks,extras))
    save(output/"games.json",games)
    save(output/"teams.json",logos)
    save(output/"picks.json",picks)
    save(output/"extras.json",extras)
    save(output/"odds_state.json",odds_state)
    save(output/"review_flags.json",review_flags)
    save(output/"status.json",status)
    # Export sanitized, static JSON for GitHub Pages (no keys and no raw tokens).
    for name,document in (("games.json",games),("teams.json",logos),
                          ("picks.json",picks),("extras.json",extras),
                          ("status.json",status)):
        save(site/name,document)
    return status
