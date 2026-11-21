import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from basketball_ai_lab.teams import NBA_TEAMS,canonical
from basketball_ai_lab.transform import normalize_games,normalize_teams,logo_url
from basketball_ai_lab.provider import Client,SourceError
from basketball_ai_lab.model import ratings,forecast,settle_one
from basketball_ai_lab.odds import fetch_snapshot,choose_extra
from basketball_ai_lab.pipeline import update
from basketball_ai_lab.store import load

NOW=datetime(2026,11,18,13,tzinfo=timezone.utc)

def event(ident,dt,home="ATL",away="BOS",score=None):
    completed=score is not None
    return {"id":str(ident),"date":dt.isoformat(),
      "status":{"type":{"completed":completed}},
      "competitions":[{"competitors":[
        {"homeAway":"home","team":{"abbreviation":home,"logo":f"https://a.espncdn.com/i/teamlogos/nba/500/{home.lower()}.png"},"score":str(score[0]) if completed else ""},
        {"homeAway":"away","team":{"abbreviation":away,"logo":f"https://a.espncdn.com/i/teamlogos/nba/500/{away.lower()}.png"},"score":str(score[1]) if completed else ""}]}]}

def mock_source(events_by_day):
    def fetch(url):
        if "/teams" in url:
            return {"sports":[{"leagues":[{"teams":[
               {"team":{"id":str(i),"abbreviation":abbr,
                "displayName":name,"logos":[{"href":f"https://a.espncdn.com/i/teamlogos/nba/500/{abbr.lower()}.png"}]}}
               for i,(abbr,name) in enumerate(NBA_TEAMS.items(),1)]}]}]}
        from urllib.parse import urlsplit,parse_qs
        key=parse_qs(urlsplit(url).query)["dates"][0]
        return {"events":events_by_day.get(key,[])}
    return fetch

def game_batch(now=NOW):
    events={}
    for i in range(13):
        dt=now-timedelta(days=15-i)
        # Include 13 previous finals with varying outcomes and plausible scores.
        events.setdefault(dt.strftime("%Y%m%d"),[]).append(event(f"G{i}",dt,"ATL","BOS",(116+i%6,106+i%5)))
    dt=now+timedelta(days=2)
    events.setdefault(dt.strftime("%Y%m%d"),[]).append(event("FUTURE",dt))
    return events

class NormalizationTests(unittest.TestCase):
    def test_all_thirty_teams_unique(self):
        self.assertEqual(len(NBA_TEAMS),30)
        for abbr,name in NBA_TEAMS.items():
            self.assertEqual(canonical(abbr),abbr)
            self.assertEqual(canonical(name),abbr)
        self.assertEqual(canonical("Los Angeles Clippers"),"LAC")
        self.assertIsNone(canonical("Los Angeles"))
    def test_logos_only_provider_supplied_and_safe_https_hosts(self):
        teams=normalize_teams(mock_source({})("/teams"))
        self.assertEqual(len(teams),30)
        self.assertEqual(sum(bool(t["logo"]) for t in teams.values()),30)
        self.assertIsNone(logo_url("javascript:alert(1)"))
        self.assertIsNone(logo_url("https://evil.example.com/logo.png"))
        self.assertIsNone(logo_url("https://a.espncdn.com.evil.com/team.png"))
    def test_malformed_score_no_false_final(self):
        obj=event("X",NOW,score=None)
        obj["status"]["type"]["completed"]=True
        games=normalize_games({"events":[obj]})
        self.assertEqual(games["X"]["status"],"FINISHED_UNVERIFIED")
        self.assertIsNone(games["X"]["home_score"])
    def test_duplicate_or_non_nba_game_rejected(self):
        self.assertFalse(normalize_games({"events":[event("X",NOW,"ATL","ATL")]}))
        self.assertFalse(normalize_games({"events":[event("X",NOW,"XXX","ATL")]}))

class ModelTests(unittest.TestCase):
    def setUp(self):
        self.games={}
        for i in range(13):
            x=event("G"+str(i),NOW-timedelta(days=15-i),score=(116+i%6,106+i%5))
            self.games.update(normalize_games({"events":[x]}))
        self.future=normalize_games({"events":[event("FUTURE",NOW+timedelta(days=2))]})["FUTURE"]
    def test_exactly_three_distinct_markets_and_no_real_prices(self):
        picks,reason=forecast(self.future,self.games,NOW)
        self.assertEqual(reason,"ARCHIVABLE")
        self.assertEqual({p["market"] for p in picks},{"winner","total","handicap"})
        self.assertTrue(all(.5<=p["probability"]<=1 for p in picks))
        self.assertTrue(all(p["real_price"] is None for p in picks))
        self.assertTrue(all(p["created_utc"]==NOW.isoformat() for p in picks))
    def test_no_picks_without_five_prior_games_each(self):
        p,reason=forecast(self.future,{},NOW)
        self.assertEqual(p,[])
        self.assertEqual(reason,"MUESTRA_INSUFICIENTE")
    def test_full_three_market_settlement(self):
        picks,_=forecast(self.future,self.games,NOW)
        final={**self.future,"status":"FINAL","home_score":120,"away_score":110}
        self.assertEqual(set(p["market"] for p in picks),{"winner","total","handicap"})
        self.assertTrue(all(settle_one(p,final) in (True,False) for p in picks))
        self.assertTrue(all(settle_one(p,{**final,"status":"SCHEDULED"}) is None for p in picks))
    def test_history_cannot_use_games_after_prediction_time(self):
        another={**self.future,"id":"LATE","status":"FINAL","home_score":199,"away_score":50}
        before=ratings(self.games,NOW)
        self.games["LATE"]=another  # future-dated fake result must be ignored
        self.assertEqual(before,ratings(self.games,NOW))

class OptionalOddsTests(unittest.TestCase):
    def test_no_key_means_no_provider_calls(self):
        def forbidden(url):raise AssertionError("No network without secret")
        self.assertEqual(fetch_snapshot("",NOW,{},forbidden)["status"],"SIN_CLAVE")
    def test_one_per_day_and_internal_monthly_budget(self):
        stamp=(NOW-timedelta(minutes=30)).isoformat()
        fake=[{"id":"odds-event", "home_team":"Atlanta Hawks","away_team":"Boston Celtics", "commence_time":(NOW+timedelta(days=1)).isoformat(),
            "bookmakers":[{"key":"book123","last_update":stamp,"markets":[{"key":"h2h","last_update":stamp,"outcomes":[{"name":"Atlanta Hawks","price":1.75},{"name":"Boston Celtics","price":2.2}]}]}]}]
        count=[]
        def mock(url):count.append(url);return fake,{"x-requests-last":"1","x-requests-remaining":"499"}
        first=fetch_snapshot("fake-key",NOW,{},mock)
        self.assertEqual(first["status"],"OK")
        self.assertEqual(len(first["quotes"]),2)
        self.assertEqual(fetch_snapshot("fake-key",NOW,first["state"],mock)["status"],"YA_CONSULTADO_HOY")
        self.assertEqual(len(count),1)
        self.assertEqual(fetch_snapshot("fake-key",NOW,{"odds_budget":{"month":"2026-11","used":100}},mock)["status"],"CUPO_INTERNO_AGOTADO")
        self.assertEqual(len(count),1)
    def test_extra_needs_matched_event_and_valid_real_price(self):
        game={"id":"F","home":"ATL","away":"BOS","start_utc":(NOW+timedelta(days=1)).isoformat(),"status":"SCHEDULED"}
        picks=[{"market":"winner","probability":.65,"contract":{"team":"ATL"}}]
        q={"home":"ATL","away":"BOS","team":"ATL","market":"h2h",
           "start_utc":game["start_utc"],"price":1.90,
           "updated_utc":NOW.isoformat(),"bookmaker":"book123",
           "captured_utc":NOW.isoformat(),"provider":"The Odds API","event_id":"external"}
        opposite={**q,"team":"BOS","price":2.0}
        second={**q,"bookmaker":"book456","price":1.85}
        second_opposite={**second,"team":"BOS","price":2.05}
        self.assertIsNone(choose_extra(game,picks,[q],NOW))
        selected=choose_extra(game,picks,[q,opposite,second,second_opposite],NOW)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["real_price"],1.90)
        self.assertEqual(selected["bookmaker"],"book123")
        self.assertLess(selected["probability"],picks[0]["probability"])
        self.assertEqual(selected["model_version"],"NBA_CONTEXT_V3_MARKET_GUARD")
        self.assertIsNone(choose_extra(game,picks,[{**q,"away":"NYK"}],NOW))
        self.assertIsNone(choose_extra(game,picks,[q],NOW+timedelta(days=2)))
        self.assertIsNone(choose_extra(game,picks,[{**q,"price":1.49}],NOW))

    def test_same_frozen_winner_may_be_real_additional_before_tipoff(self):
        from basketball_ai_lab.selection_policy import active_top3
        game={"id":"G","home":"ATL","away":"BOS",
              "start_utc":(NOW+timedelta(days=1)).isoformat(),"status":"SCHEDULED"}
        picks=[
            {"id":"G|winner","event_id":"G","market":"winner","probability":.65,
             "contract":{"type":"winner","team":"ATL"}},
            {"id":"G|total","event_id":"G","market":"total","probability":.6,
             "contract":{"type":"total","direction":"under","line":244.5}},
            {"id":"G|handicap","event_id":"G","market":"handicap","probability":.6,
             "contract":{"type":"handicap","side":"home","home_margin_line":-4.5}},
        ]
        q={"home":"ATL","away":"BOS","team":"ATL","market":"h2h",
           "start_utc":game["start_utc"],"price":1.90,
           "updated_utc":NOW.isoformat(),"bookmaker":"book123",
           "captured_utc":NOW.isoformat(),"provider":"The Odds API","event_id":"external"}
        quotes=[q,{**q,"team":"BOS","price":2.0},
                {**q,"bookmaker":"book456","price":1.85},
                {**q,"bookmaker":"book456","team":"BOS","price":2.05}]
        chosen=choose_extra(game,picks,quotes,NOW)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen["contract"],picks[0]["contract"])
        active=active_top3({p["id"]:p for p in picks},{chosen["id"]:chosen})
        self.assertEqual(len(active),2)

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)/"data";self.site=Path(self.tmp.name)/"site"
        self.calendar=game_batch()
    def client(self):return Client(fetch=mock_source(self.calendar),max_calls=65)
    def test_initial_bootstrap_team_logos_and_frozen_archive(self):
        first=update(self.out,self.site,NOW,self.client(),env={})
        self.assertEqual(first["new_top3_picks"],3)
        self.assertEqual(first["logo_coverage"],30)
        self.assertEqual(first["odds_status"],"DESACTIVADO")
        self.assertEqual(first["extras_archived"],0)
        self.assertEqual(len(load(self.site/"teams.json",{})["teams"]),30)
        old=load(self.out/"picks.json",{})
        second=update(self.out,self.site,NOW+timedelta(hours=1),self.client(),env={})
        self.assertEqual(second["new_top3_picks"],0)
        self.assertEqual(old,load(self.out/"picks.json",{}))
    def test_postgame_settlement_cannot_modify_original_probability(self):
        update(self.out,self.site,NOW,self.client(),env={})
        first=load(self.out/"picks.json",{})
        future_dt=NOW+timedelta(days=2)
        self.calendar[future_dt.strftime("%Y%m%d")]=[event("FUTURE",future_dt,score=(120,110))]
        update(self.out,self.site,NOW+timedelta(days=3),self.client(),env={})
        settled=load(self.out/"picks.json",{})
        self.assertEqual(settled.keys(),first.keys())
        for key,old in first.items():
            self.assertEqual(settled[key]["probability"],old["probability"])
            self.assertEqual(settled[key]["created_utc"],old["created_utc"])
            self.assertIn(settled[key]["result"],(0,1))
            self.assertIn(settled[key]["status"],("ACIERTO","FALLO"))
    def test_outage_preserves_archive(self):
        update(self.out,self.site,NOW,self.client(),env={})
        archived=load(self.out/"picks.json",{})
        def fail(url):raise TimeoutError("test")
        with self.assertRaisesRegex(SourceError,"Sin calendarios comprobables"):
            update(self.out,self.site,NOW+timedelta(hours=2),Client(fetch=fail,max_calls=65),env={})
        self.assertEqual(archived,load(self.out/"picks.json",{}))
        self.assertEqual(load(self.out/"status.json",{})["updated_utc"],NOW.isoformat())
    def test_exports_csv_for_excel_without_invented_additional(self):
        import csv
        report=update(self.out,self.site,NOW,self.client(),env={})
        self.assertEqual(report["top3_archived"],3)
        for filename,expected in (("top3.csv",3),("adicional_150.csv",0),("sorpresas.csv",0)):
            path=self.site.parent/"reports"/filename
            self.assertTrue(path.exists())
            with path.open(encoding="utf-8-sig",newline="") as file:
                rows=list(csv.DictReader(file))
            self.assertEqual(len(rows),expected)
        with (self.out/"reports"/"top3.csv").open(encoding="utf-8-sig") as file:
            self.assertIn("cuota_justa_teorica",file.readline())

    def test_odds_error_never_retries_same_day(self):
        attempts=[]
        def broken(url):attempts.append(url);raise TimeoutError("provider unreachable")
        one=fetch_snapshot("dummy-private-value",NOW,{},broken)
        self.assertEqual(one["status"],"PROVEEDOR_NO_DISPONIBLE")
        again=fetch_snapshot("dummy-private-value",NOW,one["state"],broken)
        self.assertEqual(again["status"],"YA_CONSULTADO_HOY")
        self.assertEqual(len(attempts),1)
        self.assertNotIn("dummy-private-value",str(again["state"]))

    def test_initial_all_sources_down_does_not_publish(self):
        def fail(url):raise TimeoutError("offline")
        with self.assertRaises(SourceError):
            update(self.out,self.site,NOW,Client(fetch=fail,max_calls=65),env={})
        self.assertFalse((self.out/"games.json").exists())

if __name__=='__main__':unittest.main()
