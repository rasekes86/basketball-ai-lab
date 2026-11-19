"""Automatic NBA postgame verification, safe retries and immutable Top3."""
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit,parse_qs
from basketball_ai_lab.history import needs_stat_verification,should_retry_summary
from basketball_ai_lab.model import is_void_line
from basketball_ai_lab.pipeline import update
from basketball_ai_lab.provider import Client
from basketball_ai_lab.store import save,load

NOW=datetime(2026,11,20,12,0,tzinfo=timezone.utc)
TIP=NOW-timedelta(hours=8)
GAME={"id":"401999001","home":"ATL","away":"BOS","start_utc":TIP.isoformat(),
      "status":"FINAL","home_score":120,"away_score":112}
PICK={"id":GAME["id"]+"|team_threes","event_id":GAME["id"],"home":"ATL","away":"BOS",
      "start_utc":GAME["start_utc"],"created_utc":(TIP-timedelta(hours=2)).isoformat(),
      "market":"team_threes","selection":"ATL: OVER 14.5 triples","probability":.65,
      "fair_odds":1/.65,"status":"PENDIENTE","result":None,
      "retrospective":False,"real_price":None,"contract":{"type":"team_stat",
       "team":"ATL","stat":"threes","direction":"over","line":14.5}}
PARTIAL={"id":GAME["id"],"home":"ATL","away":"BOS",
         "start_utc":GAME["start_utc"],"retrieved_utc":(NOW-timedelta(hours=5)).isoformat(),
         "teams":{"ATL":{"assists":25},"BOS":{"assists":27}}}


def source(url):
    parsed=urlsplit(url)
    if parsed.path.endswith("/scoreboard"):
        day=parse_qs(parsed.query)["dates"][0]
        if day!=TIP.strftime("%Y%m%d"):return {"events":[]}
        return {"events":[{"id":GAME["id"],"date":GAME["start_utc"],
          "status":{"type":{"completed":True}},
          "competitions":[{"competitors":[
           {"homeAway":"home","team":{"abbreviation":"ATL"},"score":"120"},
           {"homeAway":"away","team":{"abbreviation":"BOS"},"score":"112"}]}]}]}
    if parsed.path.endswith("/summary"):
        return {"header":{"id":GAME["id"]},"boxscore":{"teams":[
          {"team":{"abbreviation":"ATL"},"statistics":[
           {"name":"threePointFieldGoalsMade-threePointFieldGoalsAttempted","displayValue":"16-32"},
           {"name":"totalRebounds","displayValue":"45"},
           {"name":"assists","displayValue":"25"}]},
          {"team":{"abbreviation":"BOS"},"statistics":[
           {"name":"threePointFieldGoalsMade-threePointFieldGoalsAttempted","displayValue":"12-30"},
           {"name":"totalRebounds","displayValue":"44"},
           {"name":"assists","displayValue":"27"}]}
        ]}}
    if parsed.path.endswith("/teams"):return {"sports":[]}
    raise AssertionError("Unexpected URL "+url)


class PostmatchTests(unittest.TestCase):
    def test_exact_total_is_void_not_error_or_pending(self):
        final={**GAME,"home_score":112,"away_score":117}
        extra={"contract":{"type":"total","direction":"under","line":229}}
        self.assertTrue(is_void_line(extra,final))
        self.assertFalse(is_void_line(extra,{**final,"status":"SCHEDULED"}))
        self.assertFalse(is_void_line({"contract":{"type":"total","direction":"under","line":229.5}},final))

    def test_automatic_push_settlement_refunds_without_counting_in_roi(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp)/"data";web=Path(tmp)/"site"/"data"
            final={**GAME,"home_score":112,"away_score":117}
            extra={"id":GAME["id"]+"|extra","event_id":GAME["id"],
              "home":"ATL","away":"BOS","start_utc":GAME["start_utc"],
              "created_utc":(TIP-timedelta(hours=2)).isoformat(),
              "market":"extra_totals","selection":"UNDER 229 puntos",
              "probability":.55,"status":"PENDIENTE","result":None,
              "real_price":1.93,"real_price_status":"OFRECIDA_API_REGISTRADA",
              "contract":{"type":"total","direction":"under","line":229}}
            save(base/"games.json",{GAME["id"]:final})
            save(base/"extras.json",{extra["id"]:extra})
            update(base,web,NOW,Client(fetch=source,max_calls=65),env={})
            actual=load(base/"extras.json",{})[extra["id"]]
            self.assertEqual(actual["status"],"ANULADA")
            self.assertIsNone(actual["result"])
            status=load(base/"status.json",{})
            self.assertEqual(status["extras_voided"],1)
            self.assertEqual(status["extras_evaluated"],0)
            self.assertEqual(status["extras_unit_profit"],0)
            self.assertEqual(status["pending_postmatch_selections"],0)

    def test_recent_pending_gets_four_hour_retry(self):
        self.assertTrue(should_retry_summary(GAME,(NOW-timedelta(hours=5)).isoformat(),NOW,True))
        self.assertFalse(should_retry_summary(GAME,(NOW-timedelta(hours=3)).isoformat(),NOW,True))
        self.assertFalse(should_retry_summary(GAME,(NOW-timedelta(hours=5)).isoformat(),NOW,False))
        self.assertTrue(should_retry_summary(GAME,None,NOW,True))

    def test_partial_box_does_not_masquerade_as_verified(self):
        picks={PICK["id"]:PICK}
        self.assertTrue(needs_stat_verification(GAME,picks,PARTIAL))
        full={**PARTIAL,"teams":{"ATL":{"assists":25,"threes":16},"BOS":{"assists":27}}}
        self.assertFalse(needs_stat_verification(GAME,picks,full))
        self.assertFalse(needs_stat_verification(GAME,{PICK["id"]:{**PICK,"status":"ACIERTO"}},PARTIAL))

    def test_automatic_second_run_settles_without_changing_original_selection(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp)/"data";web=Path(tmp)/"site"/"data"
            save(base/"games.json",{GAME["id"]:GAME})
            save(base/"picks.json",{PICK["id"]:PICK})
            save(base/"boxscores.json",{GAME["id"]:PARTIAL})
            save(base/"boxscore_attempts.json",{GAME["id"]:(NOW-timedelta(hours=5)).isoformat()})
            result=update(base,web,NOW,Client(fetch=source,max_calls=65),env={"ENABLE_ADVANCED_STATS":"true"})
            actual=load(base/"picks.json",{})[PICK["id"]]
            self.assertEqual(actual["status"],"ACIERTO")
            self.assertEqual(actual["created_utc"],PICK["created_utc"])
            self.assertEqual(actual["probability"],PICK["probability"])
            self.assertEqual(result["pending_postmatch_team_stats"],0)
            self.assertEqual(result["pending_postmatch_selections"],0)
            self.assertEqual(result["top3_evaluated"],1)

if __name__=="__main__":unittest.main()
