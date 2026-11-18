"""Conservative historical NBA team-stat coverage and bootstrap policy.

All summaries are from real *completed* fixtures. Fetching a historical
box score today does not make an archived prediction historical: only future
predictions may use it, based on their own creation timestamp.
"""
from datetime import timedelta
from .teams import NBA_TEAMS
from .transform import time_utc

MARKETS = ("threes", "rebounds", "assists")
MIN_SAMPLE = 5


def backfill_policy(games, boxscores):
    """One controlled historical catch-up, then return to the small daily batch.

    The project already has a completed-game calendar. A one-time catch-up
    allows each team to reach a meaningful box-score sample without waiting
    for new games. ESPN is an undocumented public endpoint: retain a low
    request rate, cap requests, and honor the provider's circuit breaker.
    """
    finals = sum(game.get("status") == "FINAL" for game in games.values())
    bootstrap = finals >= 130 and len(boxscores) < 100
    return {
        "mode": "HISTORICAL_CATCHUP" if bootstrap else "DAILY",
        "summary_limit": 85 if bootstrap else 35,
        "max_calls": 125 if bootstrap else 65,
        "min_interval": .65 if bootstrap else .30,
    }


def historical_coverage(games, boxscores, asof, min_sample=MIN_SAMPLE):
    """Report only validated, time-eligible historical observations per team.

    Never counts games that started in the future, summaries captured after
    asof, team mismatches or statistics absent from the ESPN response.
    """
    asof = asof if asof.tzinfo else asof.replace(tzinfo=__import__("datetime").timezone.utc)
    counts = {team: {metric: 0 for metric in MARKETS} for team in NBA_TEAMS}
    eligible_games = 0
    for fixture_id, record in boxscores.items():
        fixture = games.get(fixture_id)
        if not fixture or fixture.get("status") != "FINAL":
            continue
        tip = time_utc(fixture.get("start_utc"))
        captured = time_utc(record.get("retrieved_utc"))
        if not tip or not captured or tip + timedelta(hours=5) >= asof or captured > asof:
            continue
        if record.get("id") != fixture_id or record.get("start_utc") != fixture.get("start_utc"):
            continue
        if (record.get("home"), record.get("away")) != (fixture.get("home"), fixture.get("away")):
            continue
        teams = record.get("teams")
        if not isinstance(teams, dict) or set(teams) != {fixture["home"], fixture["away"]}:
            continue
        eligible_games += 1
        for team in (fixture["home"], fixture["away"]):
            values = teams[team]
            if not isinstance(values, dict):
                continue
            for metric in MARKETS:
                value = values.get(metric)
                if type(value) is int and 0 <= value <= 120:
                    counts[team][metric] += 1
    ready = {metric: sum(data[metric] >= min_sample for data in counts.values()) for metric in MARKETS}
    return {
        "verified_games": eligible_games,
        "minimum_sample": min_sample,
        "ready_teams_by_market": ready,
        "fully_ready_teams": sum(all(data[m] >= min_sample for m in MARKETS)
                                 for data in counts.values()),
        "by_team": counts,
    }
