"""NBA selection follows Football AI Lab: probability-first, one per family."""
import unittest
from datetime import datetime, timedelta, timezone
from basketball_ai_lab.model import _top_by_probability,reference_forecast,forecast
from basketball_ai_lab.history import supersede_unstarted_picks

NOW=datetime(2026,11,18,23,55,tzinfo=timezone.utc)

def pick(m,p,selection=None):
    return {"market":m,"probability":p,"selection":selection or m}

class FootballStyleSelectorTests(unittest.TestCase):
    def test_no_forced_winner_when_other_markets_more_probable(self):
        rows=[pick("winner",.67),pick("team_threes",.81),pick("team_rebounds",.76),
              pick("team_assists",.74),pick("total",.63)]
        self.assertEqual([x["market"] for x in _top_by_probability(rows)],
            ["team_threes","team_rebounds","team_assists"])

    def test_one_per_family_probability_floor_fair_odds_floor(self):
        rows=[pick("winner",.54),pick("team_threes",.93),
              pick("team_rebounds",.79),pick("team_rebounds",.73,"alternative"),
              pick("team_assists",.61)]
        chosen=_top_by_probability(rows)
        self.assertEqual([x["market"] for x in chosen],["team_rebounds","team_assists"])
        self.assertTrue(all(1/x["probability"]>=1.15 for x in chosen))

    def test_short_top3_instead_of_padding(self):
        self.assertEqual(len(_top_by_probability([pick("winner",.56),pick("total",.51)])),1)
        self.assertEqual(_top_by_probability([pick("winner",.54)]),[])

    def test_today_scope_only_supersedes_pending_unstarted(self):
        early=(NOW-timedelta(minutes=4)).isoformat()
        soon=(NOW+timedelta(minutes=5)).isoformat()
        later=(NOW+timedelta(days=2)).isoformat()
        rows={
          "started|winner":{"event_id":"started","start_utc":early,"status":"PENDIENTE","result":None},
          "today|winner":{"event_id":"today","start_utc":soon,"status":"PENDIENTE","result":None},
          "future|winner":{"event_id":"future","start_utc":later,"status":"PENDIENTE","result":None},
          "settled|winner":{"event_id":"settled","start_utc":soon,"status":"ACIERTO","result":1}
        }
        archive={}
        self.assertEqual(supersede_unstarted_picks(rows,NOW,archive,{"started","today","settled"}),1)
        self.assertEqual(set(rows),{"started|winner","future|winner","settled|winner"})
        self.assertEqual(len(archive),1)
        self.assertEqual(next(iter(archive.values()))["event_id"],"today")

if __name__=="__main__":unittest.main()
