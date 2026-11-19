"""Offline NBA model research: time isolation, source vintages and scoring."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from basketball_ai_lab.research import (
    MIN_LEAGUE_GAMES, _baseline, _historical_view, _verified_box,
    _score_rows, walkforward
)

START=datetime(2026,10,1,tzinfo=timezone.utc)
RETRIEVED=datetime(2027,2,1,tzinfo=timezone.utc)


def fixtures(count=65):
    games={}
    boxes={}
    for i in range(count):
        tip=START+timedelta(days=i)
        gid=f"G{i:03}"
        home,away=("ATL","BOS") if i%2==0 else ("BOS","ATL")
        # Mixed outcomes, stable statistical sample.
        hs=111+(i%11)
        aw=106+(i%9)
        row={"id":gid,"home":home,"away":away,"status":"FINAL",
             "home_score":hs,"away_score":aw,"start_utc":tip.isoformat()}
        games[gid]=row
        boxes[gid]={"id":gid,"home":home,"away":away,
                    "start_utc":tip.isoformat(),"retrieved_utc":RETRIEVED.isoformat(),
                    "teams":{home:{"threes":18+i%3,"rebounds":48+i%4,"assists":28+i%4},
                             away:{"threes":9+i%2,"rebounds":39+i%4,"assists":20+i%2}}}
    return games,boxes


class NBAResearchTests(unittest.TestCase):
    def setUp(self):
        self.games,self.boxes=fixtures()

    def test_explicit_vintages_and_no_future_game_or_target_leak(self):
        target=self.games["G050"]
        finals=list(self.games.values())
        at,prior,strict,late=_historical_view(finals,self.boxes,target,"strict_captured")
        self.assertNotIn("G050",prior)
        self.assertNotIn("G051",prior)
        self.assertEqual(len(strict),0)
        self.assertGreater(late,0)
        _,past,reconstructed,_=_historical_view(finals,self.boxes,target,"historical_reconstruction")
        self.assertIn("G049",past)
        self.assertIn("G049",reconstructed)
        self.assertEqual(self.boxes["G049"]["retrieved_utc"],RETRIEVED.isoformat())
        self.assertLess(datetime.fromisoformat(reconstructed["G049"]["retrieved_utc"]),at)

    def test_bad_team_or_start_time_boxscore_is_rejected(self):
        game=self.games["G000"]
        box=self.boxes["G000"]
        self.assertTrue(_verified_box(game,box))
        self.assertFalse(_verified_box(game,{**box,"away":"LAL"}))
        self.assertFalse(_verified_box(game,{**box,"start_utc":START.isoformat()+"0"}))

    def test_backtest_strict_has_no_late_fetched_team_stats(self):
        result=walkforward(self.games,self.boxes)
        strict=result["modes"]["strict_captured"]
        reconstructed=result["modes"]["historical_reconstruction"]
        self.assertGreater(strict["overall"]["evaluated"],0)
        self.assertGreater(reconstructed["overall"]["evaluated"],0)
        self.assertTrue(all(not r["market"].startswith("team_") for r in strict["rows"]))
        self.assertTrue(any(r["market"].startswith("team_") for r in reconstructed["rows"]))
        self.assertEqual(result["promotion"].split(":")[0],"BLOQUEADA")
        self.assertEqual(result["archive_isolation"],"No se leen ni modifican picks.json/extras.json ni cuotas.")

    def test_future_result_changes_cannot_change_earlier_forecasts(self):
        before=walkforward(self.games,self.boxes)
        earlier=[r for r in before["modes"]["historical_reconstruction"]["rows"]
                 if r["event_id"]=="G050"]
        self.assertTrue(earlier)
        changed=copy.deepcopy(self.games)
        changed["G064"]["home_score"]=199
        changed["G064"]["away_score"]=51
        after=walkforward(changed,self.boxes)
        later=[r for r in after["modes"]["historical_reconstruction"]["rows"]
               if r["event_id"]=="G050"]
        self.assertEqual(earlier,later)

    def test_baseline_matches_contract_and_calibration_counts_events(self):
        target=self.games["G055"]
        prior={k:g for k,g in self.games.items() if k<"G050"}
        home=target["home"]
        chosen={"contract":{"type":"winner","team":home}}
        probability,n=_baseline(chosen,target,prior,{})
        wins=sum(1 for game in prior.values() if game["home_score"]>game["away_score"])
        expected=(wins+5)/(len(prior)+10) if home==target["home"] else None
        self.assertAlmostEqual(probability,expected)
        self.assertEqual(n,len(prior))
        rows=[
            {"event_id":"A","p":.8,"result":1,"baseline_p":.6},
            {"event_id":"A","p":.8,"result":0,"baseline_p":.6},
            {"event_id":"B","p":.6,"result":1,"baseline_p":None}
        ]
        summary=_score_rows(rows)
        self.assertEqual(summary["evaluated"],3)
        self.assertEqual(summary["games_unique"],2)
        self.assertEqual(summary["baseline_matched"],2)
        self.assertEqual(summary["evidence"],"INSUFICIENTES_PARTIDOS")

    def test_no_data_no_fabricated_success(self):
        result=walkforward({}, {})
        self.assertEqual(result["modes"]["strict_captured"]["overall"]["evaluated"],0)
        self.assertEqual(result["modes"]["historical_reconstruction"]["overall"]["evidence"],"SIN_RESULTADOS")
        with self.assertRaises(ValueError):
            walkforward({}, {},max_games=0)


if __name__=="__main__":
    unittest.main()
