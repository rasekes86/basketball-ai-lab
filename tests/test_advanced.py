"""Offline regression coverage for real team-stat parsing and diversified Top 3."""
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit,parse_qs

from basketball_ai_lab.advanced import parse_summary,matchup_form
from basketball_ai_lab.model import forecast,settle_one
from basketball_ai_lab.odds import fetch_snapshot,choose_extra
from basketball_ai_lab.pipeline import update
from basketball_ai_lab.provider import Client
from basketball_ai_lab.store import load

ASOF=datetime(2026,11,18,20,tzinfo=timezone.utc)

def fixture(id_,when,finished=True,home='ATL',away='BOS'):
    return {'id':str(id_),'home':home,'away':away,'start_utc':when.isoformat(),
        'status':'FINAL' if finished else 'SCHEDULED',
        'home_score':118 if finished else None,'away_score':107 if finished else None}

def summary(f,threes=(17,11),rebounds=(46,40),assists=(29,24)):
    box=[]
    for team,t,r,a in zip((f['home'],f['away']),threes,rebounds,assists):
        box.append({'team':{'abbreviation':team},'statistics':[
            {'name':'threePointFieldGoalsMade-threePointFieldGoalsAttempted','displayValue':f'{t}-38'},
            {'name':'totalRebounds','displayValue':str(r)},
            {'name':'assists','displayValue':str(a)}]})
    return {'header':{'id':str(f['id'])},'boxscore':{'teams':box}}

class TeamStatsTests(unittest.TestCase):
    def setUp(self):
        self.games={}
        self.boxes={}
        for i in range(10):
            f=fixture(i+100,ASOF-timedelta(days=22-i))
            self.games[f['id']]=f
            self.boxes[f['id']]=parse_summary(summary(f,threes=(17+i%3,8+i%3),
                         rebounds=(50+i%3,37+i%3),assists=(31+i%2,20+i%2)),
                         f,ASOF-timedelta(days=1))
        self.future=fixture(999,ASOF+timedelta(days=2),False)
    def test_summary_real_three_point_field_goals_and_absent_values(self):
        f=next(iter(self.games.values()))
        record=parse_summary(summary(f),f,ASOF)
        self.assertEqual(record['teams']['ATL']['threes'],17)
        self.assertEqual(record['teams']['BOS']['rebounds'],40)
        self.assertEqual(record['teams']['ATL']['assists'],29)
        self.assertIsNone(parse_summary({'header':{'id':'wrong'},'boxscore':summary(f)['boxscore']},f,ASOF))
        broken=summary(f)
        broken['boxscore']['teams'][1]['statistics']=[]
        self.assertIsNone(parse_summary(broken,f,ASOF))
    def test_no_future_or_later_retrieval_can_leak(self):
        rates=matchup_form(self.future,self.games,self.boxes,ASOF)
        self.assertEqual(rates['ATL']['threes']['n'],10)
        later=fixture(888,ASOF+timedelta(days=1))
        self.games['888']=later
        self.boxes['888']=parse_summary(summary(later,threes=(60,1)),later,ASOF-timedelta(hours=1))
        self.assertEqual(matchup_form(self.future,self.games,self.boxes,ASOF),rates)
        self.boxes['100']['retrieved_utc']=(ASOF+timedelta(minutes=1)).isoformat()
        self.assertEqual(matchup_form(self.future,self.games,self.boxes,ASOF)['ATL']['threes']['n'],9)
    def test_new_markets_diverse_and_can_be_settled_only_with_stats(self):
        picks,why=forecast(self.future,self.games,ASOF,self.boxes)
        self.assertEqual(why,'ARCHIVABLE')
        self.assertEqual(len(picks),3)
        self.assertEqual(len(set(p['market'] for p in picks)),3)
        self.assertTrue(all(.55<=p['probability']<=1/1.15 for p in picks))
        self.assertTrue(all(p.get('real_price') is None for p in picks))
        self.assertTrue(all(p['created_utc']<p['start_utc'] for p in picks))
        final={**self.future,'status':'FINAL','home_score':118,'away_score':107}
        result=parse_summary(summary(final),final,ASOF+timedelta(days=3))
        self.assertIsNotNone(result)
        for pick in picks:
            if pick['market'].startswith('team_'):
                self.assertIsNone(settle_one(pick,final))
                self.assertIn(settle_one(pick,final,result),(True,False))
    def test_fallback_preserves_original_three_without_boxscores(self):
        old,_=forecast(self.future,self.games,ASOF)
        missing,_=forecast(self.future,self.games,ASOF,{})
        self.assertEqual(old,missing)
        self.assertTrue(len(old)<=3)
        self.assertTrue(all(p['probability']>=.55 for p in old))

class RealPricesTests(unittest.TestCase):
    def test_free_main_game_market_request_parser(self):
        kickoff=ASOF+timedelta(days=1)
        payload=[{'id':'odds123','home_team':'Atlanta Hawks','away_team':'Boston Celtics',
          'commence_time':kickoff.isoformat(),
          'bookmakers':[{'key':'book1','last_update':ASOF.isoformat(),'markets':[
             {'key':'h2h','outcomes':[{'name':'Atlanta Hawks','price':1.80}]},
             {'key':'spreads','outcomes':[{'name':'Atlanta Hawks','price':1.87,'point':-4.5}]},
             {'key':'totals','outcomes':[{'name':'Over','price':1.88,'point':221.5}]}
          ]}]}]
        seen=[]
        def fetch(url):seen.append(url);return payload,{'x-requests-last':'3','x-requests-remaining':'497'}
        sample=fetch_snapshot('test-secret',ASOF,{},fetch)
        self.assertEqual([q['market'] for q in sample['quotes']],['h2h','spreads','totals'])
        self.assertEqual(sample['state']['odds_budget']['used'],3)
        self.assertIn('markets=h2h%2Cspreads%2Ctotals',seen[0])
        self.assertEqual(fetch_snapshot('test-secret',ASOF,sample['state'],fetch)['status'],'YA_CONSULTADO_HOY')
        self.assertEqual(len(seen),1)
        game=fixture(999,kickoff,False)
        primary=[{'market':'winner','contract':{'team':'ATL'},'probability':.65,'estimated':7.0}]
        baseline=[*primary,{'market':'total','estimated':235.0}]
        extra=choose_extra(game,primary,sample['quotes'],ASOF,baseline=baseline)
        # V3: single-sided offers from one book cannot substantiate an edge.
        self.assertIsNone(extra)
    def test_explicit_user_requested_second_snapshot_only_once_per_utc_day(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            return [],{'x-requests-last':'3','x-requests-remaining':'491'}
        first=fetch_snapshot('key',ASOF,{},fetch)
        self.assertEqual(first["status"],"OK")
        self.assertEqual(first["state"]["odds_budget"]["used"],3)
        self.assertEqual(fetch_snapshot('key',ASOF,first["state"],fetch)["status"],"YA_CONSULTADO_HOY")
        again=fetch_snapshot('key',ASOF,first["state"],fetch,allow_extra_daily=True)
        self.assertEqual(again["status"],"OK")
        self.assertEqual(again["state"]["odds_budget"]["used"],6)
        self.assertEqual(again["state"]["odds_recheck_day"],"2026-11-18")
        self.assertEqual(fetch_snapshot('key',ASOF,again["state"],fetch,allow_extra_daily=True)["status"],"YA_CONSULTADO_HOY")
        self.assertEqual(len(calls),2)
        blocked=fetch_snapshot('key',ASOF,{"odds_day":"2026-11-18","odds_budget":{"month":"2026-11","used":99}},fetch,allow_extra_daily=True)
        self.assertEqual(blocked["status"],"CUPO_INTERNO_AGOTADO")

    def test_no_key_no_calls_and_strict_budget(self):
        def nope(url):raise AssertionError('network without key')
        self.assertEqual(fetch_snapshot('',ASOF,{},nope)['status'],'SIN_CLAVE')
        self.assertEqual(fetch_snapshot('fake',ASOF,{'odds_budget':{'month':'2026-11','used':99}},nope)['status'],'CUPO_INTERNO_AGOTADO')

class PipelineIntegrationTests(unittest.TestCase):
    def test_live_stat_collection_frozen_and_audited(self):
        events={}
        games=[]
        for i in range(8):
            t=ASOF-timedelta(days=15-i)
            f=fixture(1000+i,t)
            games.append(f)
            events[t.strftime('%Y%m%d')]=[{'id':f['id'],'date':t.isoformat(),
               'season':{'type':2},'status':{'type':{'completed':True,'name':'STATUS_FINAL'}},
               'competitions':[{'competitors':[
                 {'homeAway':'home','team':{'abbreviation':'ATL'},'score':'118'},
                 {'homeAway':'away','team':{'abbreviation':'BOS'},'score':'107'}]}]}]
        t=ASOF+timedelta(days=2)
        events[t.strftime('%Y%m%d')]=[{'id':'9999','date':t.isoformat(),'season':{'type':2},
                'status':{'type':{'completed':False}},'competitions':[{'competitors':[
                 {'homeAway':'home','team':{'abbreviation':'ATL'},'score':''},
                 {'homeAway':'away','team':{'abbreviation':'BOS'},'score':''}]}]}]
        def fetch(url):
            loc=urlsplit(url);params=parse_qs(loc.query)
            if loc.path.endswith('/teams'):return {'teams':[]}
            if loc.path.endswith('/scoreboard'):
                return {'events':events.get(params['dates'][0],[])}
            if loc.path.endswith('/summary'):
                f=next(x for x in games if x['id']==params['event'][0]);return summary(f,threes=(16,12))
            raise ValueError('unexpected endpoint')
        with TemporaryDirectory() as folder:
            data=Path(folder)/'data';site=Path(folder)/'site/data'
            client=Client(fetch=fetch,max_calls=95)
            report=update(data,site,ASOF,client,env={'ENABLE_ADVANCED_STATS':'true'})
            self.assertEqual(report['boxscores_archived'],8)
            self.assertEqual(report['top3_archived'],3)
            self.assertTrue(all(p['probability']>=.55 for p in load(data/'picks.json',{}).values()))
            before=load(data/'picks.json',{})
            again=update(data,site,ASOF+timedelta(minutes=1),Client(fetch=fetch,max_calls=95),env={'ENABLE_ADVANCED_STATS':'true'})
            self.assertEqual(before,load(data/'picks.json',{}))
            self.assertEqual(again['boxscores_new'],0)
            self.assertEqual(load(site/'boxscores.json',{}),load(data/'boxscores.json',{}))

if __name__=='__main__':unittest.main()
