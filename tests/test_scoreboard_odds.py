"""Offline parser regressions for genuinely offered ESPN scoreboard prices."""
import unittest
from datetime import datetime, timedelta, timezone

from basketball_ai_lab.scoreboard_odds import scoreboard_quotes, _decimal_from_american
from basketball_ai_lab.odds import choose_extra

NOW=datetime(2026,11,18,23,15,tzinfo=timezone.utc)
START=(NOW+timedelta(hours=2)).isoformat()

def sample():
    game={"id":"4019","home":"ATL","away":"BOS","start_utc":START,
          "status":"SCHEDULED"}
    odds={"provider":{"id":"100","name":"DraftKings"},
          "moneyline":{"home":{"close":{"odds":"-110"}},"away":{"close":{"odds":"+102"}}},
          "pointSpread":{"home":{"close":{"line":"-3.5","odds":"-112"}},
                         "away":{"close":{"line":"+3.5","odds":"-108"}}},
          "total":{"over":{"close":{"line":"o230.5","odds":"-115"}},
                   "under":{"close":{"line":"u230.5","odds":"-105"}}}}
    event={"id":"4019","date":START,"competitions":[{"id":"4019","odds":[odds]}]}
    return {"events":[event]},{"4019":game},game

class ScoreboardOddsTests(unittest.TestCase):
    def test_american_price_conversion(self):
        self.assertAlmostEqual(_decimal_from_american("-110"),1.909091,places=5)
        self.assertEqual(_decimal_from_american("+150"),2.5)
        self.assertEqual(_decimal_from_american("EVEN"),2.0)
        self.assertIsNone(_decimal_from_american("unpriced"))
        self.assertIsNone(_decimal_from_american(0))

    def test_all_six_offered_markets_observed_pregame(self):
        payload,games,_=sample()
        quotes=scoreboard_quotes(payload,games,NOW)
        self.assertEqual(len(quotes),6)
        self.assertEqual({q["market"] for q in quotes},{"h2h","spreads","totals"})
        self.assertTrue(all(q["bookmaker"]=="DraftKings" for q in quotes))
        self.assertTrue(all(q["quote_time_basis"]=="OBSERVED_AT_CAPTURE" for q in quotes))
        self.assertIn(230.5,[q.get("point") for q in quotes])

    def test_reject_unknown_fixture_wrong_start_or_started(self):
        payload,games,_=sample()
        self.assertEqual(scoreboard_quotes(payload,games,NOW+timedelta(hours=3)),[])
        self.assertEqual(scoreboard_quotes(payload,{},NOW),[])
        payload["events"][0]["date"]=(NOW+timedelta(hours=3)).isoformat()
        self.assertEqual(scoreboard_quotes(payload,games,NOW),[])

    def test_real_espn_price_can_supply_fourth_selection(self):
        payload,games,game=sample()
        quotes=scoreboard_quotes(payload,games,NOW)
        primary=[{"market":"winner","contract":{"team":"ATL"},
                  "probability":.68,"estimated":7.0}]
        baseline=[*primary,{"market":"total","estimated":238.0}]
        extra=choose_extra(game,primary,quotes,NOW,baseline=baseline)
        self.assertIsNotNone(extra)
        self.assertGreater(extra["real_price"],1.5)
        self.assertEqual(extra["provider"],"ESPN scoreboard")
        self.assertEqual(extra["quote_time_basis"],"OBSERVED_AT_CAPTURE")
        self.assertEqual(extra["bookmaker"],"DraftKings")
        self.assertTrue(extra["created_utc"]<extra["start_utc"])

    def test_incomplete_quote_never_invents_price(self):
        payload,games,_=sample()
        odds=payload["events"][0]["competitions"][0]["odds"][0]
        for kind in ("moneyline","pointSpread","total"): odds.pop(kind)
        self.assertEqual(scoreboard_quotes(payload,games,NOW),[])

if __name__=="__main__":
    unittest.main()
