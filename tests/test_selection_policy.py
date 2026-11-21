"""2+1: real additional replaces exact Top 3 contract only in active accounting."""
import unittest
from basketball_ai_lab.selection_policy import same_outcome, active_top3
from basketball_ai_lab.reports import theoretical_top3_balance


def pick(event, market, contract, probability, result):
    return {
        "id": event + "|" + market, "event_id": event,
        "market": market, "contract": contract, "probability": probability,
        "result": result, "status": "ACIERTO" if result else "FALLO",
        "retrospective": False, "real_price": None,
    }


class ActiveSelectionTests(unittest.TestCase):
    def setUp(self):
        self.picks = {
            "G|winner": pick("G", "winner", {"type": "winner", "team": "ATL"}, .8, 1),
            "G|total": pick("G", "total", {"type": "total", "direction": "over", "line": 209.5}, .7, 0),
            "G|handicap": pick("G", "handicap", {"type": "handicap", "side": "home", "home_margin_line": -7.5}, .75, 1),
        }

    def test_exact_repeat_counts_two_plus_one_preserves_archive(self):
        real = {"G|extra": {
            "event_id": "G", "contract": {"type": "winner", "team": "ATL"},
            "real_price": 1.9, "status": "ACIERTO", "result": 1,
        }}
        active = active_top3(self.picks, real)
        self.assertEqual(set(active), {"G|total", "G|handicap"})
        self.assertEqual(len(self.picks), 3)
        self.assertEqual(theoretical_top3_balance(active)["settled"], 2)
        self.assertTrue(same_outcome(self.picks["G|winner"], real["G|extra"]))
        self.assertEqual(len(active)+len(real), 3)

    def test_different_line_or_match_is_not_a_duplicate(self):
        real = {"G|extra": {
            "event_id": "G", "contract": {"type": "total", "direction": "over", "line": 210.5}
        }}
        self.assertEqual(len(active_top3(self.picks, real)), 3)
        real["G|extra"]["contract"]["line"] = 209.5
        real["G|extra"]["event_id"] = "OTHER"
        self.assertEqual(len(active_top3(self.picks, real)), 3)
        real["G|extra"]["event_id"] = "G"
        self.assertEqual(len(active_top3(self.picks, real)), 2)

    def test_no_contract_cannot_silently_eliminate_top3(self):
        self.assertEqual(len(active_top3(self.picks, {"G|extra": {"event_id": "G"}})), 3)


if __name__ == "__main__":
    unittest.main()
