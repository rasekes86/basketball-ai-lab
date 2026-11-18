"""Fair-odds payout is hypothetical and separate from actual sportsbook quotes."""
import unittest

from basketball_ai_lab.reports import theoretical_top3_balance, _one

def pick(name,market,p,result,status):
    return {"id":name,"market":market,"probability":p,
            "result":result,"status":status,"retrospective":False,
            "real_price":None}

class FairOddsBalanceTests(unittest.TestCase):
    def test_exact_price_and_one_euro_settlement(self):
        bets={
            "a":pick("a","winner",.5,1,"ACIERTO"),
            "b":pick("b","team_threes",.8,0,"FALLO"),
            "c":pick("c","team_rebounds",.65,None,"PENDIENTE"),
        }
        result=theoretical_top3_balance(bets)
        self.assertEqual(result["settled"],2)
        self.assertEqual(result["total_staked_eur"],2)
        self.assertEqual(result["net_eur"],0)
        self.assertEqual(result["roi_pct"],0)
        self.assertEqual(result["price_basis"],"MATHEMATICAL_1_OVER_P_NOT_OFFERED")
        self.assertEqual(result["by_market"]["winner"]["net_eur"],1)
        self.assertEqual(result["by_market"]["team_threes"]["net_eur"],-1)

    def test_wins_are_not_bookmaker_profits(self):
        win=pick("a","team_assists",.6,1,"ACIERTO")
        result=theoretical_top3_balance({"a":win})
        self.assertAlmostEqual(result["net_eur"],.667,places=3)
        self.assertAlmostEqual(result["roi_pct"],66.67,places=2)

    def test_missing_and_retrospective_excluded(self):
        no=pick("a","winner",.7,None,"PENDIENTE")
        retro=pick("b","winner",.7,1,"ACIERTO");retro["retrospective"]=True
        bad=pick("c","winner",0,1,"ACIERTO")
        result=theoretical_top3_balance({"a":no,"b":retro,"c":bad})
        self.assertEqual(result["settled"],0)
        self.assertIsNone(result["roi_pct"])

    def test_csv_uses_theoretical_only_when_settled(self):
        win=pick("a","winner",.5,1,"ACIERTO")
        self.assertEqual(_one(win)["balance_simulado_1_eur"],1)
        self.assertEqual(_one(pick("b","winner",.5,None,"PENDIENTE"))["balance_simulado_1_eur"],"")
        extra=pick("c","extra_h2h",.5,1,"ACIERTO")
        extra["real_price"]=1.8
        self.assertEqual(_one(extra)["balance_simulado_1_eur"],"")

if __name__=="__main__":
    unittest.main()
