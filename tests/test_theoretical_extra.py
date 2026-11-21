"""Regression: a model-only fourth pick never masquerades as bookmaker odds."""
import unittest
from datetime import datetime,timezone,timedelta

from basketball_ai_lab.odds import choose_theoretical_extra

NOW=datetime(2026,11,20,8,tzinfo=timezone.utc)
GAME={"id":"N123","home":"ATL","away":"BOS",
      "start_utc":(NOW+timedelta(hours=9)).isoformat(),"status":"SCHEDULED"}
BASE=[{"market":"winner","estimated":4.0,
       "contract":{"type":"winner","team":"ATL"},"probability":.61},
      {"market":"total","estimated":223.0,
       "contract":{"type":"total","direction":"over","line":224.5},"probability":.47}]

class TheoreticalExtraTests(unittest.TestCase):
    def test_extra_has_fair_only_and_is_different_from_top3(self):
        picks=[{"contract":{"type":"total","direction":"over","line":224.5}},
               {"contract":{"type":"winner","team":"ATL"}},
               {"contract":{"type":"handicap","side":"home","home_margin_line":0.5}}]
        extra=choose_theoretical_extra(GAME,picks,BASE,NOW)
        self.assertIsNotNone(extra)
        self.assertEqual(extra["id"],"N123|extra_teorica")
        self.assertTrue(1.5<extra["fair_odds"])
        self.assertIsNone(extra["real_price"])
        self.assertEqual(extra["real_price_status"],"CUOTA_JUSTA_TEORICA_NO_OFRECIDA")
        self.assertNotIn(extra["contract"],[p["contract"] for p in picks])
        self.assertEqual(extra["status"],"PENDIENTE")
        self.assertLess(extra["created_utc"],extra["start_utc"])
    def test_no_retroactive_or_no_baseline(self):
        self.assertIsNone(choose_theoretical_extra(GAME,[],BASE,NOW+timedelta(days=1)))
        self.assertIsNone(choose_theoretical_extra(GAME,[],[],NOW))

if __name__=="__main__":unittest.main()
