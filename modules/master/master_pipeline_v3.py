#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter=';'))
def write_csv(path,rows,fields):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=';');w.writeheader();w.writerows(rows)
def fnum(v):
    try:return float(v)
    except:return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--year',type=int,required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    root=Path(args.root);y=args.year;rows=[]
    fields=['annee_reference','indicator_id','domain','territoire','perimeter_id','value','unit','source_primary','source_detail','source_file','source_page','coverage_status','quality_status','record_role','population_millesime','definition','note']
    # Population
    pops=read_csv(root/'modules/insee_population/outputs/fact_population_resolue_2019_2024.csv')
    for r in pops:
        if int(r['annee_indicateur'])!=y:continue
        rows.append({'annee_reference':y,'indicator_id':'POP_MUNICIPALE','domain':'DEMOGRAPHIE','territoire':r['territoire'],'perimeter_id':r['territoire'],'value':r['population_utilisee'],'unit':'habitants','source_primary':'INSEE','source_detail':r['statut_resolution'],'source_file':'fact_population_resolue_2019_2024.csv','source_page':'','coverage_status':'COMPLETE','quality_status':'OK' if r['statut_resolution']=='OFFICIEL_MILLESIME_N' else 'POPULATION_LAG','record_role':'PRODUCTION' if r['statut_resolution']=='OFFICIEL_MILLESIME_N' else 'DIAGNOSTIC','population_millesime':r['millesime_population'],'definition':'Population municipale INSEE.','note':''})
    # RAD/RPQS reconciled by contract/sector
    lp=root/f'modules/perimeters/outputs/fact_local_reports_reconciled_{y}.csv'
    if lp.exists():
        for r in read_csv(lp):
            rows.append({'annee_reference':y,'indicator_id':r['indicator_id'],'domain':r['domain'],'territoire':r['territoire'],'perimeter_id':r['perimeter_id'],'value':r['value'],'unit':r['unit'],'source_primary':'RAD_RPQS','source_detail':r['source_family'],'source_file':r['source_file'],'source_page':r['source_page'],'coverage_status':r['coverage_status'],'quality_status':r['quality_status'],'record_role':r['record_role'],'population_millesime':'','definition':r['definition'],'note':r['note']})
    # BNPE if available
    bp=root/f'modules/bnpe/outputs_{y}/mart_bnpe_indicateurs_{y}.csv'
    if not bp.exists() and y==2022: bp=root/'modules/bnpe/outputs/mart_bnpe_indicateurs_2022.csv'
    if bp.exists():
        for r in read_csv(bp):
            role='DIAGNOSTIC' if r['indicator_id'] in {'RES_007','RES_008','RES_009'} else 'PRODUCTION'
            quality='INCOMPLETE_INVENTORY' if role=='DIAGNOSTIC' else 'OK'
            rows.append({'annee_reference':y,'indicator_id':r['indicator_id'],'domain':'RESSOURCE','territoire':'Martinique','perimeter_id':'MARTINIQUE','value':r['value'],'unit':r['unit'] or ('m³/an' if r['indicator_id'] in {'RES_014','RES_015','RES_016','RES_017'} else '%' if r['indicator_id'] in {'RES_001','RES_002','RES_003','RES_004','RES_005','RES_006'} else 'nb'),'source_primary':'BNPE','source_detail':r['calculation'],'source_file':f'mart_bnpe_indicateurs_{y}.csv','source_page':'','coverage_status':'COMPLETE','quality_status':quality,'record_role':role,'population_millesime':'','definition':'','note':'BNPE non exhaustive pour le comptage des captages.' if role=='DIAGNOSTIC' else ''})
    # Derived AEP subscribers Martinique only when the 3 EPCI values are available as production.
    def prod_value(ind,terr):
        rr=[r for r in rows if r['indicator_id']==ind and r['territoire']==terr and r['record_role']=='PRODUCTION']
        vals=[fnum(r['value']) for r in rr if fnum(r['value']) is not None]
        # Prefer verified CAP_NORD_EPCI when there are multiple rows.
        if terr=='CAP_NORD':
            vv=[r for r in rr if r.get('perimeter_id')=='CAP_NORD_EPCI' and fnum(r['value']) is not None]
            if vv:return fnum(vv[-1]['value'])
        return vals[-1] if vals else None
    ep_sub=[prod_value('EP_ABONNES',t) for t in ('CACEM','CAESM','CAP_NORD')]
    if all(v is not None for v in ep_sub):
        rows.append({'annee_reference':y,'indicator_id':'EP_ABONNES','domain':'EAU_POTABLE','territoire':'Martinique','perimeter_id':'MARTINIQUE','value':sum(ep_sub),'unit':'abonnés','source_primary':'CALCUL_LOCAL','source_detail':'Somme EPCI réconciliés','source_file':'','source_page':'','coverage_status':'COMPLETE','quality_status':'OK','record_role':'PRODUCTION','population_millesime':'','definition':'Somme des abonnés AEP des trois EPCI après réconciliation des contrats CAP Nord.','note':''})
    # Known absence coverage is carried as explicit status rows, not zeros.
    ca=root/'modules/perimeters/outputs/coverage_matrix_v2.csv'
    if ca.exists():
        for r in read_csv(ca):
            if int(r['year'])!=y or r['status']=='COUVERT':continue
            rows.append({'annee_reference':y,'indicator_id':'SOURCE_COVERAGE','domain':r['domain'],'territoire':r['territory'],'perimeter_id':r['territory'],'value':'','unit':'','source_primary':'META','source_detail':'Couverture documentaire','source_file':'coverage_matrix_v2.csv','source_page':'','coverage_status':r['status'],'quality_status':'SOURCE_NOT_PRODUCED' if r['status']=='NON_PRODUIT_DECLARE' else 'SOURCE_MISSING','record_role':'AUDIT','population_millesime':'','definition':'État de disponibilité de la source locale.','note':r['note']})
    write_csv(Path(args.out)/f'fact_indicateur_master_{y}.csv',rows,fields)
    quality=[r for r in rows if r['quality_status']!='OK' or r['coverage_status'] not in ('COMPLETE','') or r['record_role'] in ('AUDIT','DIAGNOSTIC')]
    write_csv(Path(args.out)/f'data_quality_master_{y}.csv',quality,fields)
    summary={'year':y,'rows':len(rows),'production':sum(r['record_role']=='PRODUCTION' for r in rows),'diagnostic':sum(r['record_role']=='DIAGNOSTIC' for r in rows),'audit':sum(r['record_role']=='AUDIT' for r in rows)}
    json.dump(summary,open(Path(args.out)/f'summary_master_{y}.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
