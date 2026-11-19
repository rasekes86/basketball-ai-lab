"""Offline NBA walk-forward research, independent from all live 3+1 archives.

This intentionally does NOT alter forecasts, probabilities, real odds, site JSON
or archived picks. Reconstructed historical boxscores are NOT point-in-time
snapshots; read the quality warnings in every report before making claims.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
from math import log
from pathlib import Path

from .model import forecast, settle_one
from .store import load, save
from .teams import NBA_TEAMS
from .transform import time_utc

VERSION = "nba-walkforward-research-0.1"
MIN_LEAGUE_GAMES = 40
CUTOFF_BEFORE_TIP = timedelta(minutes=5)
PAST_GAME_EMBARGO = timedelta(hours=5)
MODES = ("strict_captured", "historical_reconstruction")
SMOOTHING = 10


def _valid_final(game):
    if not isinstance(game, dict) or game.get("status") != "FINAL":
        return False
    if game.get("home") not in NBA_TEAMS or game.get("away") not in NBA_TEAMS:
        return False
    if game["home"] == game["away"] or not time_utc(game.get("start_utc")):
        return False
    home, away = game.get("home_score"), game.get("away_score")
    return type(home) is int and type(away) is int and 50 <= home <= 200 and 50 <= away <= 200


def _verified_box(game, box):
    if not isinstance(box, dict) or box.get("id") != game.get("id"):
        return False
    if box.get("start_utc") != game.get("start_utc"):
        return False
    if (box.get("home"), box.get("away")) != (game.get("home"), game.get("away")):
        return False
    entries = box.get("teams")
    if not isinstance(entries, dict) or set(entries) != {game["home"], game["away"]}:
        return False
    return all(isinstance(entries[team], dict) for team in (game["home"], game["away"]))


def _historical_view(finals, boxes, target, mode):
    """Only earlier, already-plausibly-completed fixtures, grouped by event ID.

    Strict mode additionally checks captured_utc <= decision T.
    Reconstruction mode uses late-fetched historical stats in a sandboxed
    temporary view, explicitly labelled as an unverifiable availability
    assumption. The original box metadata is never changed.
    """
    tip = time_utc(target["start_utc"])
    at = tip - CUTOFF_BEFORE_TIP
    prior = {
        g["id"]: g for g in finals
        if g["id"] != target["id"] and time_utc(g["start_utc"]) + PAST_GAME_EMBARGO < at
    }
    eligible = {}
    late = 0
    for game_id, game in prior.items():
        box = boxes.get(game_id)
        if not _verified_box(game, box):
            continue
        captured = time_utc(box.get("retrieved_utc"))
        if not captured:
            continue
        if captured > at:
            late += 1
            if mode == "strict_captured":
                continue
            # Only a temporary research object. An assumed availability date
            # does NOT prove this archived data version existed at that time.
            eligible[game_id] = {**box, "retrieved_utc": (at-timedelta(seconds=1)).isoformat()}
        else:
            eligible[game_id] = box
    return at, prior, eligible, late


def _baseline(pick, target, prior, boxes):
    """A simple preregistered, matched-contract baseline using only earlier data.

    Winner: empirical NBA home win rate (or away complement).
    Total/handicap: league frequency for the exact selected threshold.
    Team stats: selected team's own prior game frequency for that threshold.
    Laplace-style 10 virtual observations at 50% prevent extreme zero/one.
    """
    contract = pick.get("contract") or {}
    kind = contract.get("type")
    outcomes = []
    for game in prior.values():
        if kind == "winner":
            if game["home_score"] == game["away_score"]:
                continue
            won_home = game["home_score"] > game["away_score"]
            value = won_home if contract.get("team") == target["home"] else not won_home
        elif kind == "team_stat":
            if contract.get("team") not in (game["home"], game["away"]):
                continue
            box = boxes.get(game["id"])
            if not box:
                continue
            value = settle_one(pick, game, box)
        else:
            value = settle_one(pick, game)
        if value is not None:
            outcomes.append(int(value))
    minimum = 5 if kind == "team_stat" else 20
    if len(outcomes) < minimum:
        return None, len(outcomes)
    return (sum(outcomes) + SMOOTHING*.5)/(len(outcomes)+SMOOTHING),len(outcomes)


def _score_rows(rows):
    n = len(rows)
    if not n:
        return {"evaluated":0,"games_unique":0,"hits":0,"accuracy":None,"mean_probability":None,
                "brier":None,"logloss":None,"ece":None,"calibration":[],
                "baseline_matched":0,"baseline_brier":None,"model_brier_matched":None,
                "delta_brier_baseline_minus_model":None,"evidence":"SIN_RESULTADOS"}
    brier = sum((r["p"]-r["result"])**2 for r in rows)/n
    logloss = -sum(log(max(1e-12, r["p"] if r["result"] else 1-r["p"])) for r in rows)/n
    buckets = defaultdict(list)
    for r in rows:
        buckets[min(4,int(r["p"]*5))].append(r)
    calib = []
    ece = 0.0
    for idx, bucket in sorted(buckets.items()):
        expected = sum(r["p"] for r in bucket)/len(bucket)
        actual = sum(r["result"] for r in bucket)/len(bucket)
        ece += len(bucket)/n*abs(expected-actual)
        calib.append({"bin":f"{idx*20}-{(idx+1)*20}","n":len(bucket),
                      "games_unique":len({r["event_id"] for r in bucket}),
                      "predicted_mean":round(expected,5),"observed_frequency":round(actual,5)})
    comparable = [r for r in rows if r["baseline_p"] is not None]
    b0 = sum((r["baseline_p"]-r["result"])**2 for r in comparable)/len(comparable) if comparable else None
    b1 = sum((r["p"]-r["result"])**2 for r in comparable)/len(comparable) if comparable else None
    ng = len({r["event_id"] for r in rows})
    return {
        "evaluated": n, "games_unique":ng,
        "hits":sum(r["result"] for r in rows),
        "accuracy":round(sum(r["result"] for r in rows)/n,5),
        "mean_probability":round(sum(r["p"] for r in rows)/n,5),
        "brier":round(brier,6),"logloss":round(logloss,6),
        "ece":round(ece,6),"calibration":calib,
        "baseline_matched":len(comparable),
        "baseline_brier":round(b0,6) if b0 is not None else None,
        "model_brier_matched":round(b1,6) if b1 is not None else None,
        "delta_brier_baseline_minus_model":round(b0-b1,6) if b0 is not None else None,
        "evidence":("INSUFICIENTES_PARTIDOS" if ng<30 else "EXPLORATORIO_NO_VALIDADO")
    }


def walkforward(games, boxscores, max_games=160):
    if not isinstance(games,dict) or not isinstance(boxscores,dict):
        raise ValueError("Se necesitan objetos games y boxscores JSON")
    if not isinstance(max_games,int) or max_games<1:
        raise ValueError("max_games debe ser un entero positivo")
    finals = sorted(
        (g for g in games.values() if _valid_final(g)),
        key=lambda g:(time_utc(g["start_utc"]), g["id"])
    )
    # Match whole calendar dates instead of slicing one game from a busy night.
    selected_dates = sorted({time_utc(g["start_utc"]).date() for g in finals})[-max_games:]
    selected = [g for g in finals if time_utc(g["start_utc"]).date() in selected_dates]
    reports = {}
    for mode in MODES:
        records = []
        exclusions = Counter()
        late_sources = 0
        evaluated_games = 0
        for target in selected:
            at, prior, prior_boxes, late = _historical_view(finals,boxscores,target,mode)
            late_sources += late
            if len(prior)<MIN_LEAGUE_GAMES:
                exclusions["SIN_HISTORICO_MINIMO"]+=1
                continue
            fictional_fixture = {**target,"status":"SCHEDULED","home_score":None,"away_score":None}
            picks, reason = forecast(fictional_fixture,prior,at,prior_boxes)
            if not picks:
                exclusions[reason]+=1
                continue
            evaluated_games += 1
            final_box = boxscores.get(target["id"])
            if not _verified_box(target,final_box):
                final_box = None
            for p in picks:
                settled = settle_one(p,target,final_box)
                if settled is None:
                    exclusions["ESTADISTICA_O_LINEA_NO_LIQUIDABLE"]+=1
                    continue
                baseline,base_n = _baseline(p,target,prior,prior_boxes)
                records.append({
                    "event_id":target["id"],"start_utc":target["start_utc"],
                    "decision_utc":at.isoformat(),"market":p["market"],
                    "selection":p["selection"],"p":p["probability"],
                    "result":int(settled),"baseline_p":round(baseline,6) if baseline is not None else None,
                    "baseline_n":base_n,
                    "fold":time_utc(target["start_utc"]).strftime("%Y-%m"),
                    "model":p.get("model"),"contract":p.get("contract"),
                    "quality":"RECONSTRUIDO_NO_VERIFICADO_AS_OF" if mode=="historical_reconstruction" else "CAPTURA_AS_OF",
                })
        groups = defaultdict(list)
        folds = defaultdict(list)
        for record in records:
            groups[record["market"]].append(record)
            folds[record["fold"]].append(record)
        reports[mode] = {
            "status":"RETROSPECTIVO_EXPLORATORIO_NO_PROSPECTIVO",
            "games_selected":len(selected),"games_with_forecasts":evaluated_games,
            "stat_snapshots_later_than_T_encountered":late_sources,
            "exclusions":dict(exclusions),
            "overall":_score_rows(records),
            "by_market":{k:_score_rows(v) for k,v in sorted(groups.items())},
            "by_fold":{k:_score_rows(v) for k,v in sorted(folds.items())},
            "rows":records
        }
    return {
        "version":VERSION,
        "source":"Solo archivos ESPN archivados en Basketball AI Lab, sin red",
        "data_provenance":"backfill de marcador/boxscore; la reconstrucción NO prueba versión disponible en T",
        "modes":reports,
        "split":"Rolling origin por fecha UTC; un partido y sus pronósticos en el mismo bloque; embargo 5 horas.",
        "training":"Solo partidos finalizados que comenzaron al menos cinco horas antes de T.",
        "cutoff":"T = inicio programado - 5 minutos",
        "baseline":"Frecuencia del contrato en partidos anteriores con suavizado 10 observaciones al 50%.",
        "promotion":"BLOQUEADA: validación prospectiva y auditoría manual requeridas.",
        "archive_isolation":"No se leen ni modifican picks.json/extras.json ni cuotas.",
        "notice":"Resultados exploratorios, no rendimiento prospectivo ni evidencia de rentabilidad. Las múltiples líneas seleccionadas de un partido están correlacionadas."
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="NBA: investigación retrospectiva offline sin alterar pronósticos")
    parser.add_argument("--games",type=Path,default=Path("data/games.json"))
    parser.add_argument("--boxscores",type=Path,default=Path("data/boxscores.json"))
    parser.add_argument("--output",type=Path,default=Path("research/walkforward_report.json"))
    parser.add_argument("--max-games",type=int,default=160,help="Número máximo de fechas UTC históricas")
    opts=parser.parse_args(argv)
    if not opts.games.is_file() or not opts.boxscores.is_file():
        parser.error("Faltan datos históricos reales; no se generan métricas falsas")
    result=walkforward(load(opts.games,{}),load(opts.boxscores,{}),opts.max_games)
    save(opts.output,result)
    print(json.dumps({
        "status":result["promotion"],
        "strict":{k:v for k,v in result["modes"]["strict_captured"].items() if k in ("overall","exclusions")},
        "reconstructed":{k:v for k,v in result["modes"]["historical_reconstruction"].items() if k in ("overall","exclusions")}
    },ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
