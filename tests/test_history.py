"""Offline regression tests: safe historical NBA statistics, no re-pricing."""
import unittest
from datetime import datetime, timedelta, timezone

from basketball_ai_lab.history import backfill_policy, historical_coverage, supersede_unstarted_picks

NOW = datetime(2026, 11, 18, 22, tzinfo=timezone.utc)


def final_game(number, away="BOS"):
    return {"id":str(number), "home":"ATL", "away":away, "status":"FINAL",
            "start_utc":(NOW-timedelta(days=20-number)).isoformat(),
            "home_score":110,"away_score":105}


def box(game, n, captured=NOW-timedelta(hours=1)):
    return {"id":game["id"], "home":game["home"], "away":game["away"],
            "start_utc":game["start_utc"], "retrieved_utc":captured.isoformat(),
            "teams":{"ATL":{"threes":12+n,"rebounds":44,"assists":23},
                     "BOS":{"threes":10,"rebounds":40,"assists":27}},
            "source":"ESPN summary"}


class HistoryPolicyTests(unittest.TestCase):
    def test_one_controlled_bootstrap_for_large_past_calendar(self):
        games={str(i):{"status":"FINAL"} for i in range(210)}
        policy=backfill_policy(games,{str(i):{} for i in range(35)})
        self.assertEqual(policy["mode"],"HISTORICAL_CATCHUP")
        self.assertEqual(policy["summary_limit"],85)
        self.assertEqual(policy["max_calls"],125)
        self.assertGreaterEqual(policy["min_interval"],.6)
        self.assertEqual(backfill_policy(games,{str(i):{} for i in range(110)})["mode"],"DAILY")

    def test_new_repository_does_not_overrequest(self):
        games={str(i):{"status":"FINAL"} for i in range(40)}
        self.assertEqual(backfill_policy(games,{})["summary_limit"],35)

    def test_coverage_requires_real_earlier_games_and_retrieval(self):
        games={str(i):final_game(i) for i in range(3)}
        boxes={str(i):box(games[str(i)],i) for i in range(3)}
        coverage=historical_coverage(games,boxes,NOW,min_sample=3)
        self.assertEqual(coverage["verified_games"],3)
        self.assertEqual(coverage["ready_teams_by_market"],
                         {"threes":2,"rebounds":2,"assists":2})
        self.assertEqual(coverage["fully_ready_teams"],2)
        self.assertEqual(coverage["by_team"]["ATL"]["threes"],3)
        self.assertEqual(coverage["by_team"]["MIL"]["threes"],0)

    def test_future_and_wrong_team_summaries_are_excluded(self):
        games={str(i):final_game(i) for i in range(3)}
        boxes={str(i):box(games[str(i)],i) for i in range(3)}
        boxes["1"]["retrieved_utc"]=(NOW+timedelta(minutes=5)).isoformat()
        boxes["2"]["away"]="LAL"
        cov=historical_coverage(games,boxes,NOW,min_sample=2)
        self.assertEqual(cov["verified_games"],1)
        self.assertEqual(cov["ready_teams_by_market"]["threes"],0)
        self.assertEqual(historical_coverage(games,boxes,NOW-timedelta(days=30))["verified_games"],0)

    def test_absent_metric_never_becomes_zero(self):
        g=final_game(0)
        record=box(g,0)
        record["teams"]["BOS"].pop("threes")
        record["teams"]["ATL"]["assists"]=None
        cov=historical_coverage({"0":g},{"0":record},NOW,min_sample=1)
        self.assertEqual(cov["ready_teams_by_market"],
                         {"threes":1,"rebounds":2,"assists":1})


    def test_user_refresh_preserves_started_and_scored_predictions(self):
        earlier=(NOW-timedelta(minutes=1)).isoformat()
        later=(NOW+timedelta(hours=2)).isoformat()
        picks={
            "old|winner":{"start_utc":earlier,"status":"PENDIENTE","result":None,"created_utc":earlier},
            "final|winner":{"start_utc":later,"status":"ACIERTO","result":1,"created_utc":earlier},
            "next|winner":{"start_utc":later,"status":"PENDIENTE","result":None,"created_utc":earlier},
        }
        archive={}
        self.assertEqual(supersede_unstarted_picks(picks,NOW,archive),1)
        self.assertEqual(set(picks),{"old|winner","final|winner"})
        self.assertEqual(len(archive),1)
        self.assertEqual(next(iter(archive.values()))["superseded_reason"],
                         "USER_REQUESTED_PREGAME_RESELECTION")
        self.assertEqual(supersede_unstarted_picks(picks,NOW,archive),0)



if __name__=="__main__":
    unittest.main()
