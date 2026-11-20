"""Conservative, pregame-only NBA context and uncertainty model.

The adjustments below are deliberately modest. They are NOT statistically
calibrated betting probabilities; no player availability is fabricated.
"""
from statistics import pstdev
from .transform import time_utc

VERSION = "NBA_CONTEXT_V3"
PROBABILITY_SHRINK = 0.70  # conservative uncertainty penalty, NOT a fitted calibration

def cautious_probability(raw):
    """Reduce unsupported confidence without claiming trained calibration."""
    return max(0.001, min(0.999, .5 + PROBABILITY_SHRINK * (float(raw)-.5)))

def matchup_context(games, at, fixture):
    """Use only verified results available before the prediction timestamp.

    Returns (home-point adjustment, away-point adjustment, margin SD, total SD).
    Rest is based on the actual upcoming tipoff, but prior games must already
    be FINAL before 'at'. Missing rest/box scores produce neutral adjustments.
    """
    tip = time_utc(fixture.get("start_utc"))
    eligible = []
    for game in games.values():
        played = time_utc(game.get("start_utc"))
        if (game.get("status") != "FINAL" or played is None or played >= at
                or type(game.get("home_score")) is not int
                or type(game.get("away_score")) is not int):
            continue
        eligible.append((played, game))
    eligible.sort(key=lambda item: item[0])
    last = {}
    for when, game in eligible:
        for code in (game["home"], game["away"]):
            last[code] = when
    def fatigue(code):
        if tip is None or code not in last: return 0.0
        rest = (tip - last[code]).total_seconds() / 86400
        if rest < 0: return 0.0
        if rest < 1.65: return -1.5  # back-to-back
        if rest < 2.5: return -0.5
        if rest > 4.0: return 0.4
        return 0.0
    recent = [game for _, game in eligible[-120:]]
    margins = [game["home_score"]-game["away_score"] for game in recent]
    totals = [game["home_score"]+game["away_score"] for game in recent]
    # Strong shrink to league priors: season samples are short and volatile.
    margin_sd = (0.7 * 15.5**2 + 0.3 * pstdev(margins)**2)**.5 if len(margins)>=30 else 15.5
    total_sd = (0.7 * 18.5**2 + 0.3 * pstdev(totals)**2)**.5 if len(totals)>=30 else 18.5
    return (fatigue(fixture.get("home")), fatigue(fixture.get("away")),
            max(14.0, min(24.0, margin_sd)),
            max(17.0, min(29.0, total_sd)))
