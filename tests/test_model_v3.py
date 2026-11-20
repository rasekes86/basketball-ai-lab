"""V3 regression checks: cautious estimates, source chronology, paired odds."""
import unittest
from datetime import datetime, timedelta, timezone

from basketball_ai_lab.model_v3 import cautious_probability, matchup_context
from basketball_ai_lab.odds import market_consensus_probability

NOW = datetime(2026, 11, 20, 8, 0, tzinfo=timezone.utc)

class V3RegressionTests(unittest.TestCase):
    def test_confidence_shrink_is_symmetric_and_bounded(self):
        self.assertAlmostEqual(cautious_probability(.9), .78)
        self.assertAlmostEqual(cautious_probability(.1), .22)
        self.assertAlmostEqual(cautious_probability(.5), .5)

    def test_rest_uses_only_results_known_at_archive(self):
        future={"id":"f","home":"ATL","away":"BOS","start_utc":(NOW+timedelta(days=1)).isoformat()}
        recent={"id":"r","home":"ATL","away":"BOS","status":"FINAL",
                "start_utc":(NOW-timedelta(hours=10)).isoformat(),
                "home_score":110,"away_score":100}
        malicious={"id":"bad","home":"ATL","away":"BOS","status":"FINAL",
                   "start_utc":(NOW+timedelta(hours=2)).isoformat(),
                   "home_score":190,"away_score":50}
        baseline=matchup_context({"r":recent},NOW,future)
        self.assertEqual(baseline,matchup_context({"r":recent,"bad":malicious},NOW,future))
        self.assertEqual(baseline[0],-1.5)
        self.assertEqual(baseline[1],-1.5)

    def test_needs_two_independently_paired_bookmakers(self):
        q={"event_id":"e","home":"ATL","away":"BOS","market":"totals","point":225.5,
           "direction":"over","start_utc":NOW.isoformat(),"bookmaker":"one","price":1.9}
        a={**q,"direction":"under","price":1.95}
        self.assertIsNone(market_consensus_probability(q,[q,a]))
        b={**q,"bookmaker":"two","price":1.88}
        c={**b,"direction":"under","price":1.97}
        p=market_consensus_probability(q,[q,a,b,c])
        self.assertIsNotNone(p)
        self.assertGreater(p,.49)
        self.assertLess(p,.52)
        wrong={**c,"point":226.5}
        self.assertIsNone(market_consensus_probability(q,[q,a,b,wrong]))

if __name__=="__main__":
    unittest.main()
