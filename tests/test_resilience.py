"""Safety regression tests for immutable NBA archives and ESPN response changes."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit, parse_qs

from basketball_ai_lab.provider import Client, SourceError
from basketball_ai_lab.model import forecast, settle_one
from basketball_ai_lab.pipeline import update
from basketball_ai_lab.store import load,save
from basketball_ai_lab.transform import game_score, logo_url, normalize_games

AT=datetime(2026,11,18,13,tzinfo=timezone.utc)

def event(id, at, home="ATL", away="BOS", score=None, phase=2):
    return {"id":id, "date":at.isoformat(), "season":{"type":phase},
      "status":{"type":{"completed":score is not None,
                         "name":"STATUS_FINAL" if score else "STATUS_SCHEDULED"}},
      "competitions":[{"competitors":[
          {"homeAway":"home","team":{"abbreviation":home},
           "score":str(score[0]) if score else ""},
          {"homeAway":"away","team":{"abbreviation":away},
           "score":str(score[1]) if score else ""}]}]}

class FakeNBA:
    def __init__(self):
        self.items={}
        for i in range(13):
            when=AT-timedelta(days=16-i)
            self.add(event('H'+str(i),when,score=(104+i%7,99+i%4)))
        self.future=AT+timedelta(days=2)
        self.add(event('NEXT',self.future))
        self.fail_days=set()
        self.all_fail=False
    def add(self,fixture,bucket=None):
        date=bucket or fixture['date'][:10].replace('-','')
        self.items.setdefault(date,[]).append(fixture)
    def __call__(self,url):
        if '/teams?' in url:
            return {'sports':[{'leagues':[{'teams':[]}]}]}
        date=parse_qs(urlsplit(url).query)['dates'][0]
        if self.all_fail or date in self.fail_days:
            raise TimeoutError('simulated blocked provider')
        return {'events':self.items.get(date,[])}

class SourceResilienceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.data=self.root/'data';self.site=self.root/'site'
        self.feed=FakeNBA()
    def client(self):return Client(fetch=self.feed,max_calls=65)

    def test_scores_accept_object_without_allowing_fractions_or_extremes(self):
        self.assertEqual(game_score({'value':122}),122)
        self.assertEqual(game_score({'displayValue':'121'}),121)
        for x in [True,123.2,-1,999,'',None,{'value':'oops'}]:
            self.assertIsNone(game_score(x))
        source=event('OBJ',AT,score=(122,115))
        source['competitions'][0]['competitors'][0]['score']={'value':122}
        source['competitions'][0]['competitors'][1]['score']={'displayValue':'115'}
        self.assertEqual(normalize_games({'events':[source]})['OBJ']['home_score'],122)

    def test_preseason_excluded_from_history_and_predictions(self):
        preseason=event('PRE',AT-timedelta(days=2),score=(120,90),phase=1)
        self.assertEqual(normalize_games({'events':[preseason]}),{})
        reg=event('REG',AT-timedelta(days=2),score=(120,90),phase=2)
        self.assertEqual(len(normalize_games({'events':[reg]})),1)

    def test_cancelled_with_scores_cannot_be_liquidated(self):
        cancelled=event('POSTPONED',AT,score=(100,90))
        cancelled['status']['type']['name']='STATUS_CANCELED'
        self.assertEqual(normalize_games({'events':[cancelled]})['POSTPONED']['status'],
                         'SCHEDULED')

    def test_untrusted_images_rejected_with_port_and_credentials(self):
        good='https://a.espncdn.com/i/teamlogos/nba/500/atl.png'
        self.assertEqual(logo_url(good),good)
        for x in ['https://a.espncdn.com:8080/a.png',
                  'https://u@a.espncdn.com/a.png',
                  'https://evil.com/a.png',
                  'https://a.espncdn.com/a.png#fragment',
                  'https://a.espncdn.com:invalid/a.png']:
            self.assertIsNone(logo_url(x))

    def test_initial_malformed_payload_fails_without_publishing(self):
        def malformed(url):return {'unexpected':[]}
        with self.assertRaises(SourceError):
            update(self.data,self.site,AT,Client(fetch=malformed,max_calls=65),{})
        self.assertFalse((self.data/'status.json').exists())

    def test_existing_archive_is_not_recomputed_when_all_sources_fail(self):
        first=update(self.data,self.site,AT,self.client(),{})
        old=load(self.data/'picks.json',{})
        self.feed.all_fail=True
        with self.assertRaises(SourceError):
            update(self.data,self.site,AT+timedelta(hours=1),self.client(),{})
        self.assertEqual(load(self.data/'picks.json',{}),old)
        self.assertEqual(load(self.data/'status.json',{})['updated_utc'],first['updated_utc'])

    def test_missing_upcoming_from_current_source_cannot_generate_new_pick(self):
        update(self.data,self.site,AT,self.client(),{})
        # Remove previous picks for this fixture as if it had not been seen yet.
        save(self.data/'picks.json',{})
        self.feed.items[self.feed.future.strftime('%Y%m%d')]=[]
        result=update(self.data,self.site,AT+timedelta(hours=1),self.client(),{})
        self.assertEqual(result['top3_archived'],0)
        self.assertEqual(result['no_top3_reasons']['NEXT'],
                         'PARTIDO_NO_VERIFICADO_EN_LA_RONDA')

    def test_us_date_bucket_before_utc_midnight_is_supported(self):
        self.feed=FakeNBA()
        dt=datetime(2026,11,21,1,tzinfo=timezone.utc)
        self.feed.items.pop(self.feed.future.strftime('%Y%m%d'))
        self.feed.add(event('NEXT',dt),bucket='20261120')
        outcome=update(self.data,self.site,AT,self.client(),{})
        self.assertEqual(outcome['top3_archived'],3)

    def test_rescheduling_archived_game_requires_review_and_blocks_settlement(self):
        update(self.data,self.site,AT,self.client(),{})
        saved=load(self.data/'picks.json',{})
        date=self.feed.future.strftime('%Y%m%d')
        moved=self.feed.future+timedelta(hours=5)
        self.feed.items[date]=[event('NEXT',moved)]
        flag=update(self.data,self.site,AT+timedelta(hours=1),self.client(),{})
        self.assertEqual(flag['review_required_count'],1)
        self.assertEqual(flag['review_required']['NEXT']['code'],'FECHA_REPROGRAMADA')
        self.assertEqual(load(self.data/'picks.json',{}),saved)
        self.feed.items[date]=[event('NEXT',moved,score=(125,100))]
        update(self.data,self.site,AT+timedelta(days=3),self.client(),{})
        self.assertTrue(all(p['status']=='PENDIENTE' for p in load(self.data/'picks.json',{}).values()))

    def test_changed_result_after_settlement_flags_without_rewriting(self):
        update(self.data,self.site,AT,self.client(),{})
        date=self.feed.future.strftime('%Y%m%d')
        self.feed.items[date]=[event('NEXT',self.feed.future,score=(120,101))]
        update(self.data,self.site,AT+timedelta(days=3),self.client(),{})
        old=load(self.data/'picks.json',{})
        self.assertTrue(all(p['status'] in ('ACIERTO','FALLO') for p in old.values()))
        self.feed.items[date]=[event('NEXT',self.feed.future,score=(121,101))]
        report=update(self.data,self.site,AT+timedelta(days=3,hours=1),self.client(),{})
        self.assertEqual(report['review_required']['NEXT']['code'],'MARCADOR_FINAL_CORREGIDO')
        self.assertEqual(old,load(self.data/'picks.json',{}))

if __name__=='__main__':unittest.main()

from basketball_ai_lab.doctor import audit

class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=Path(self.temp.name)/'data';self.site=Path(self.temp.name)/'site/data'

    def test_before_activation_audit_is_honest(self):
        result=audit(self.data,self.site,now=AT)
        self.assertEqual(result['state'],'PENDING_LIVE')
        self.assertFalse(result['errors'])
        strict=audit(self.data,self.site,now=AT,require_live=True)
        self.assertEqual(strict['state'],'ERROR')
        self.assertIn('SIN_CAPTURA_REAL',[x['code'] for x in strict['errors']])

    def test_real_capture_audit_checks_immutable_top3_and_web_mirror(self):
        source=FakeNBA()
        update(self.data,self.site,AT,Client(fetch=source.fetch if hasattr(source,'fetch') else source),{})
        result=audit(self.data,self.site,now=AT+timedelta(minutes=1),require_live=True)
        self.assertEqual(result['state'],'OK',result)
        self.assertEqual(result['summary']['top3'],3)
        picks=load(self.data/'picks.json',{})
        item=next(iter(picks.values()))
        item['created_utc']=item['start_utc']
        save(self.data/'picks.json',picks)
        broken=audit(self.data,self.site,now=AT+timedelta(minutes=1),require_live=True)
        self.assertIn('TOP3_NO_PREPARTIDO',[x['code'] for x in broken['errors']])
        self.assertIn('WEB_DESINCRONIZADA',[x['code'] for x in broken['errors']])

    def test_bad_logo_is_caught_and_no_external_calls_needed(self):
        source=FakeNBA()
        update(self.data,self.site,AT,Client(fetch=source),{})
        teams=load(self.data/'teams.json',{})
        teams['teams']['ATL']={'abbr':'ATL','name':'Atlanta Hawks','logo':'https://evil.example/logo.png'}
        save(self.data/'teams.json',teams)
        result=audit(self.data,self.site,now=AT+timedelta(minutes=1))
        self.assertIn('ESCUDO_URL',[x['code'] for x in result['errors']])

class RateLimitSafetyTests(unittest.TestCase):
    def test_http_429_breaks_immediately_without_more_requests(self):
        from urllib.error import HTTPError
        attempts=[]
        def provider(url):
            attempts.append(url)
            raise HTTPError(url,429,'Too many requests',{},None)
        client=Client(fetch=provider,max_calls=65)
        with self.assertRaisesRegex(SourceError,'HTTP_429'):
            client.scoreboard(AT.date())
        with self.assertRaisesRegex(SourceError,'detenido por seguridad'):
            client.scoreboard((AT+timedelta(days=1)).date())
        self.assertEqual(client.calls,1)
        self.assertEqual(len(attempts),1)
        self.assertEqual(client.blocked_reason,'HTTP_429')

    def test_three_consecutive_network_errors_stop_at_three_requests(self):
        attempts=[]
        def provider(url):
            attempts.append(url)
            raise TimeoutError('network failure')
        client=Client(fetch=provider,max_calls=65)
        for day in range(3):
            with self.assertRaises(SourceError):
                client.scoreboard((AT+timedelta(days=day)).date())
        with self.assertRaises(SourceError):
            client.scoreboard((AT+timedelta(days=3)).date())
        self.assertEqual(client.calls,3)
        self.assertEqual(len(attempts),3)
        self.assertEqual(client.blocked_reason,'TRES_FALLOS_CONSECUTIVOS')
