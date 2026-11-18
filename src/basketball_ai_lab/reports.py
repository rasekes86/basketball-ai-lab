"""Excel-compatible CSV exports; never use exploratory picks in ROI."""
import csv
from pathlib import Path

FIELDS=("partido","fecha_utc","local","visitante","mercado","seleccion",
        "probabilidad","cuota_justa_teorica","cuota_real_ofrecida","bookmaker",
        "captura_cuota_utc","estado","acierto","nivel","fuente")

def _one(row):
    return {"partido":row.get("event_id"),"fecha_utc":row.get("start_utc"),
        "local":row.get("home"),"visitante":row.get("away"),
        "mercado":row.get("market"),"seleccion":row.get("selection"),
        "probabilidad":row.get("probability"),
        "cuota_justa_teorica":row.get("fair_odds",""),
        "cuota_real_ofrecida":row.get("real_price") if row.get("real_price") is not None else "",
        "bookmaker":row.get("bookmaker", ""),
        "captura_cuota_utc":row.get("captured_utc",""),
        "estado":row.get("status","PENDIENTE"),
        "acierto":row.get("result") if row.get("result") is not None else "",
        "nivel":row.get("quality",""),
        "fuente":row.get("provider",row.get("model",""))}

def _save(path,rows,fields):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)

def surprises(games,picks):
    """Model-defined upsets only: >=60% archived favourite later lost.
    This is NOT evidence of bookmaker betting value.
    """
    result=[]
    for p in picks.values():
        if p.get('market')!='winner' or p.get('status')!='FALLO':continue
        if float(p.get('probability') or 0)<.60:continue
        g=games.get(p.get('event_id'))
        if not g or g.get('status')!='FINAL':continue
        winner=g['home'] if g['home_score']>g['away_score'] else g['away']
        result.append({"partido":g['id'],"fecha_utc":g['start_utc'],
            "favorito_modelo":p['contract']['team'],"probabilidad":p['probability'],
            "ganador_real":winner,"marcador":f"{g['home_score']}-{g['away_score']}",
            "tipo":"SORPRESA_SEGUN_MODELO_SIN_CUOTAS"})
    return result

def publish(base,site,games,picks,extras):
    """Export original Top3 and exactly one frozen extra per fixture."""
    ordered=lambda x:sorted(x.values(),key=lambda p:(p.get('start_utc',''),p.get('id','')))
    for name,records in (("top3.csv",ordered(picks)),("adicional_150.csv",ordered(extras))):
        lines=[_one(p) for p in records]
        for root in (base,site):_save(Path(root)/'reports'/name,lines,FIELDS)
    upset=surprises(games,picks)
    fields=('partido','fecha_utc','favorito_modelo','probabilidad','ganador_real','marcador','tipo')
    for root in (base,site):_save(Path(root)/'reports'/'sorpresas.csv',upset,fields)
    return {"sorpresas_detectadas":len(upset)}
