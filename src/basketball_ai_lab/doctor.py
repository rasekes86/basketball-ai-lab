"""Non-network audit of a Basketball AI Lab installation.

Never prints credentials, makes HTTP requests or modifies an archive.
Allows an empty pre-activation package (state PENDING_LIVE); `--require-live`
can enforce source ingestion once a real GitHub runner is available.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path

from .model import settle_one,MIN_TOP_PROBABILITY,MIN_TOP_FAIR_ODDS
from .store import load
from .teams import NBA_TEAMS
from .transform import logo_url,time_utc

EXPECTED_MARKETS={'winner','total','handicap','team_threes','team_rebounds','team_assists'}
DATA_NAMES={'games','picks','extras','theoretical_extras','teams','status','boxscores'}
TOP3_POLICY_EFFECTIVE=datetime(2026,11,18,23,58,10,tzinfo=timezone.utc)


def audit(output=Path('data'),site=Path('site/data'),now=None,require_live=False):
    output=Path(output);site=Path(site)
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issues=[];warnings=[];observations=[]
    def fail(code,message):issues.append({'code':code,'message':message})
    def warn(code,message):warnings.append({'code':code,'message':message})

    docs={name:load(output/(name+'.json'),{}) for name in DATA_NAMES}
    games,picks,extras,teams,status=(docs[x] for x in ('games','picks','extras','teams','status'))
    boxscores=docs['boxscores']
    theoretical_extras=docs['theoretical_extras']
    flags=load(output/'review_flags.json',{})
    has_live_data=bool(status.get('source_successful_days')) and bool(games)
    if not has_live_data:
        if require_live:
            fail('SIN_CAPTURA_REAL','Aún no consta un calendario NBA obtenido en una ejecución real.')
        else:
            observations.append('Sin captura real todavía: entrega preparada para primera ejecución de GitHub.')
    saved_time=time_utc(status.get('updated_utc'))
    if saved_time and (now-saved_time)>timedelta(hours=48):
        warn('ACTUALIZACION_ANTIGUA','Última captura de más de 48 horas; revisar NBA daily.')
    if saved_time and saved_time>now+timedelta(minutes=5):
        fail('RELOJ_INCONSISTENTE','La fecha publicada está en el futuro respecto al reloj actual.')

    for fixture_id,fixture in games.items():
        if not isinstance(fixture,dict) or fixture.get('id')!=fixture_id:
            fail('ID_PARTIDO','Identificador de partido inconsistente.');break
        if fixture.get('home') not in NBA_TEAMS or fixture.get('away') not in NBA_TEAMS:
            fail('EQUIPO_DESCONOCIDO','Hay un partido con franquicias no reconocidas.');break
        if fixture.get('home')==fixture.get('away'):
            fail('EQUIPOS_IGUALES','Un partido enfrenta el mismo equipo consigo mismo.');break
        if not time_utc(fixture.get('start_utc')):
            fail('HORA_INVALIDA','Falta una hora UTC comprobable en un partido.');break

    legacy_low=[]
    for key,p in picks.items():
        market=p.get('market') if isinstance(p,dict) else None
        if market not in EXPECTED_MARKETS or key!=f'{p.get("event_id")}|{market}' or key!=p.get('id'):
            fail('TOP3_ESTRUCTURA','Un Top 3 tiene identificador o mercado no válido.');break
        created=time_utc(p.get('created_utc'));start=time_utc(p.get('start_utc'))
        if not created or not start or created>=start or created>now+timedelta(minutes=5):
            fail('TOP3_NO_PREPARTIDO','Existe un Top 3 sin sello prepartido válido.');break
        if not .0<float(p.get('probability') or 0)<=1.0:
            fail('PROBABILIDAD','Hay una probabilidad fuera de [0, 1].');break
        probability=float(p.get('probability') or 0)
        if probability<MIN_TOP_PROBABILITY or (probability>0 and 1/probability<MIN_TOP_FAIR_ODDS-0.000001):
            if created<TOP3_POLICY_EFFECTIVE:
                legacy_low.append(p)
            else:
                fail('TOP3_BAJO_MINIMO_NUEVO',
                     f'La selección {key} viola los filtros vigentes de probabilidad y cuota justa.');break
        if p.get('real_price') is not None or p.get('retrospective') is not False:
            fail('TOP3_MEZCLADO','El Top 3 contiene una cuota real o un retrospectivo.');break
        if p.get('status') in ('ACIERTO','FALLO'):
            if p.get('result') not in (0,1):
                fail('LIQUIDACION_INCONSISTENTE','Estado y resultado discordantes.');break
            event=games.get(p.get('event_id'))
            if event and p.get('event_id') not in flags:
                expected=settle_one(p,event,boxscores.get(p.get('event_id')))
                if expected is not None and int(expected)!=int(p['result']):
                    fail('LIQUIDACION_ERRONEA','Un Top 3 no corresponde al resultado final archivado.');break
    if legacy_low:
        warn('TOP3_LEGACY_FUERA_DE_FILTRO',
             f'{len(legacy_low)} selecciones previas al 18/11/2026 23:58 UTC no superan el filtro actual; conservar su archivo original.')
    for event_id in {p.get('event_id') for p in picks.values() if isinstance(p,dict)}:
        present=[x.get('market') for x in picks.values() if isinstance(x,dict) and x.get('event_id')==event_id]
        if len(present)!=3 or len(set(present))!=3:
            warn('TOP3_INCOMPLETO',f'El archivo debe tener exactamente tres mercados distintos ({event_id}).')

    for key,p in extras.items():
        if not isinstance(p,dict) or key!=f'{p.get("event_id")}|extra' or p.get('id')!=key:
            fail('ADICIONAL_DUPLICADA','La adicional no cumple un único registro por encuentro.');break
        created=time_utc(p.get('created_utc'));start=time_utc(p.get('start_utc'))
        captured=time_utc(p.get('captured_utc'));updated=time_utc(p.get('quote_updated_utc'))
        if not all([created,start,captured,updated]) or not (updated<=captured<=created<start):
            fail('ADICIONAL_SIN_TRAZABILIDAD','La cuota no tiene cuatro sellos temporales prepartido coherentes.');break
        try: real_price=float(p.get('real_price') or 0)
        except (TypeError,ValueError):real_price=0
        if not 1.50<real_price<=30 or p.get('real_price_status')!='OFRECIDA_API_REGISTRADA':
            fail('ADICIONAL_NO_VALIDA','Precio u origen de la adicional no cumplen los filtros.');break
        if not (p.get('bookmaker') and p.get('provider') and p.get('quote_event_id')):
            fail('ADICIONAL_SIN_PROVEEDOR','Falta identificación de bookmaker o evento de la cuota.');break
    # Model-only additional references are never bookmaker quotes.
    for key,p in theoretical_extras.items():
        if not isinstance(p,dict) or key!=f'{p.get("event_id")}|extra_teorica' or p.get("id")!=key:
            fail('ADICIONAL_TEORICA_ID','Referencia adicional sin identificador válido.');break
        created=time_utc(p.get('created_utc'));start=time_utc(p.get('start_utc'))
        probability=float(p.get('probability') or 0)
        if not created or not start or not created<start or not .0<probability<1/1.5:
            fail('ADICIONAL_TEORICA_INVALIDA','Referencia adicional sin probabilidad/prepartido válido.');break
        if p.get('real_price') is not None or p.get('real_price_status')!='CUOTA_JUSTA_TEORICA_NO_OFRECIDA':
            fail('ADICIONAL_TEORICA_COTIZADA','Una cuota justa fue confundida con cuota real.');break
        if any(other.get('event_id')==p.get('event_id') and other.get('contract')==p.get('contract') for other in picks.values()):
            fail('ADICIONAL_TEORICA_DUPLICADA','La referencia adicional duplica un Top 3.');break
    # A new statistic must trace to a genuine finalized ESPN game.
    for id_,record in boxscores.items():
        fixture=games.get(id_)
        if not fixture or fixture.get('status')!='FINAL' or record.get('id')!=id_:
            fail('BOXSCORE_SIN_PARTIDO','Estadística avanzada sin partido final reconocido.');break
        if record.get('start_utc')!=fixture.get('start_utc') or not time_utc(record.get('retrieved_utc')):
            fail('BOXSCORE_FECHA','Estadística avanzada con fechas no verificables.');break
        if set(record.get('teams') or {})!={fixture['home'],fixture['away']}:
            fail('BOXSCORE_RIVALES','Los equipos de las estadísticas no coinciden con el calendario.');break
    source_teams=teams.get('teams') or {}
    for key,value in source_teams.items():
        if key not in NBA_TEAMS or not isinstance(value,dict) or key!=value.get('abbr'):
            fail('CATALOGO_EQUIPOS','Hay una franquicia desconocida o inconsistente.');break
        if value.get('logo') and logo_url(value['logo']) is None:
            fail('ESCUDO_URL','Escudo con enlace externo no autorizado.');break
    if has_live_data and len(source_teams)<30:
        warn('CATALOGO_INCOMPLETO',f'Solo hay {len(source_teams)}/30 equipos identificados en ESPN.')
    verified=sum(bool(v.get('logo') and logo_url(v['logo'])) for v in source_teams.values())
    if has_live_data and verified<30:
        warn('ESCUDOS_PARCIALES',f'Solo {verified}/30 escudos tienen URL publicada; comprobar imágenes.')

    for name in DATA_NAMES:
        web_file=site/(name+'.json')
        if not web_file.exists():
            if has_live_data:fail('FALTA_WEB','La web carece de '+name+'.json')
            continue
        if has_live_data:
            # Site intentionally mirrors data except its own independent report assets.
            source_file=output/(name+'.json')
            if source_file.exists() and load(source_file,{})!=load(web_file,{}):
                fail('WEB_DESINCRONIZADA','El archivo web '+name+'.json difiere del motor.')
    for file in ('top3.csv','adicional_150.csv','sorpresas.csv'):
        for parent in (output,site.parent):
            path=parent/'reports'/file
            if not path.exists():
                if has_live_data:fail('FALTA_CSV','No existe '+str(path))
                continue
            try:
                with path.open(encoding='utf-8-sig',newline='') as stream:
                    header=next(csv.reader(stream),[])
                if not header:fail('CSV_VACIO','El reporte '+file+' no tiene encabezados.')
            except (UnicodeError,OSError,csv.Error):
                fail('CSV_DANADO','No se puede leer '+file)

    return {'state':'ERROR' if issues else 'OK' if has_live_data else 'PENDING_LIVE',
        'checked_utc':now.isoformat(),'errors':issues,'warnings':warnings,'notes':observations,
        'summary':{'games':len(games),'top3':len(picks),'additional':len(extras),'theoretical_additional':len(theoretical_extras),
                   'registered_teams':len(source_teams),'logo_urls':verified,
                   'manual_review':len(flags),'data_files':len(DATA_NAMES)}}


def format_report(report):
    lines=['Basketball AI Lab · Doctor: '+report['state']]
    x=report['summary']
    lines.append(f"Partidos: {x['games']} · Top3: {x['top3']} · Adicionales: {x['additional']} · Escudos: {x['logo_urls']}/30")
    for kind in ('errors','warnings','notes'):
        for row in report[kind]:
            lines.append(('ERROR' if kind=='errors' else 'AVISO' if kind=='warnings' else 'NOTA')+
                         ': '+(row['code']+' · '+row['message'] if isinstance(row,dict) else row))
    return '\n'.join(lines)
