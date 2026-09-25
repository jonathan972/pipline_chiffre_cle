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
  fields=['annee_reference','indicator_id','domain','territoire','value','unit','source_primary','source_detail','source_file','source_page','coverage_status','quality_status','record_role','population_millesime','note']
  # Population
  pops=read_csv(root/'modules/insee_population/outputs/fact_population_resolue_2019_2024.csv')
  for r in pops:
    if int(r['annee_indicateur'])!=y:continue
    rows.append({'annee_reference':y,'indicator_id':'POP_MUNICIPALE','domain':'DEMOGRAPHIE','territoire':r['territoire'],'value':r['population_utilisee'],'unit':'habitants','source_primary':'INSEE','source_detail':r['statut_resolution'],'source_file':'fact_population_resolue_2019_2024.csv','source_page':'','coverage_status':'COMPLETE','quality_status':'OK' if r['statut_resolution']=='OFFICIEL_MILLESIME_N' else 'POPULATION_LAG','record_role':'PRODUCTION' if r['statut_resolution']=='OFFICIEL_MILLESIME_N' else 'DIAGNOSTIC','population_millesime':r['millesime_population'],'note':'Population municipale.'})
  # Local reports
  lp=root/f'modules/local_reports/outputs/fact_local_reports_{y}.csv'
  if lp.exists():
    for r in read_csv(lp):
      rows.append({'annee_reference':y,'indicator_id':r['indicator_id'],'domain':r['domain'],'territoire':r['territoire'],'value':r['value'],'unit':r['unit'],'source_primary':'RAD_RPQS','source_detail':r['source_family'],'source_file':r['source_file'],'source_page':r['source_page'],'coverage_status':r['coverage_status'],'quality_status':r['quality_status'],'record_role':r['record_role'],'population_millesime':'','note':r['note']})
  # BNPE if available
  bp=root/f'modules/bnpe/outputs_{y}/mart_bnpe_indicateurs_{y}.csv'
  if not bp.exists() and y==2022: bp=root/'modules/bnpe/outputs/mart_bnpe_indicateurs_2022.csv'
  if bp.exists():
    for r in read_csv(bp):
      role='DIAGNOSTIC' if r['indicator_id'] in {'RES_007','RES_008','RES_009'} else 'PRODUCTION'
      quality='INCOMPLETE_INVENTORY' if role=='DIAGNOSTIC' else 'OK'
      rows.append({'annee_reference':y,'indicator_id':r['indicator_id'],'domain':'RESSOURCE','territoire':'Martinique','value':r['value'],'unit':r['unit'] or ('m³/an' if r['indicator_id'] in {'RES_014','RES_015','RES_016','RES_017'} else '%' if r['indicator_id'] in {'RES_001','RES_002','RES_003','RES_004','RES_005','RES_006'} else 'nb'),'source_primary':'BNPE','source_detail':r['calculation'],'source_file':f'mart_bnpe_indicateurs_{y}.csv','source_page':'','coverage_status':'COMPLETE','quality_status':quality,'record_role':role,'population_millesime':'','note':'BNPE non exhaustive pour le comptage des captages.' if role=='DIAGNOSTIC' else ''})
  # Derived 2023 diagnostic AEP total from local contracts (pending Cap Nord mapping confirmation)
  if y==2023:
    def localval(ind,terr):
      rr=[r for r in rows if r['indicator_id']==ind and r['territoire']==terr and r['source_primary']=='RAD_RPQS']
      return fnum(rr[-1]['value']) if rr else None
    comps=['CACEM','CAESM','CAP_NORD_CONTRAT_SME','ROBERT_TRINITE']
    billed=[localval('EP_VOLUME_FACTURE',t) for t in comps]
    subs=[localval('EP_ABONNES',t) for t in comps]
    pop=[r for r in rows if r['indicator_id']=='POP_MUNICIPALE' and r['territoire']=='Martinique']
    if all(v is not None for v in billed):
      total=sum(billed)
      rows.append({'annee_reference':y,'indicator_id':'EP_VOLUME_FACTURE_LOCAL_DIAG','domain':'EAU_POTABLE','territoire':'Martinique','value':total,'unit':'m³/an','source_primary':'CALCUL_LOCAL','source_detail':'CACEM + CAESM + contrat CAP Nord + Robert-Trinité','source_file':'','source_page':'','coverage_status':'PARTIAL_METHOD','quality_status':'TERRITORY_MAPPING_TO_CONFIRM','record_role':'DIAGNOSTIC','population_millesime':'','note':'Ne pas publier avant validation formelle du périmètre du contrat SME CAP Nord.'})
      if pop:
        p=fnum(pop[0]['value']); cons=total*1000/(p*365)
        rows.append({'annee_reference':y,'indicator_id':'EP_CONSO_L_J_HAB_LOCAL_DIAG','domain':'EAU_POTABLE','territoire':'Martinique','value':cons,'unit':'L/j/hab','source_primary':'CALCUL_LOCAL','source_detail':'Volume facturé local / population municipale INSEE','source_file':'','source_page':'','coverage_status':'PARTIAL_METHOD','quality_status':'TERRITORY_MAPPING_TO_CONFIRM','record_role':'DIAGNOSTIC','population_millesime':pop[0]['population_millesime'],'note':'Diagnostic uniquement.'})
    if all(v is not None for v in subs):
      rows.append({'annee_reference':y,'indicator_id':'EP_ABONNES_LOCAL_DIAG','domain':'EAU_POTABLE','territoire':'Martinique','value':sum(subs),'unit':'abonnés','source_primary':'CALCUL_LOCAL','source_detail':'CACEM + CAESM + contrat CAP Nord + Robert-Trinité','source_file':'','source_page':'','coverage_status':'PARTIAL_METHOD','quality_status':'TERRITORY_MAPPING_TO_CONFIRM','record_role':'DIAGNOSTIC','population_millesime':'','note':'Diagnostic uniquement.'})
  write_csv(Path(args.out)/f'fact_indicateur_master_{y}.csv',rows,fields)
  quality=[r for r in rows if r['quality_status']!='OK' or r['coverage_status'] not in ('COMPLETE','')]
  write_csv(Path(args.out)/f'data_quality_master_{y}.csv',quality,fields)
  json.dump({'year':y,'rows':len(rows),'production':sum(r['record_role']=='PRODUCTION' for r in rows),'diagnostic':sum(r['record_role']=='DIAGNOSTIC' for r in rows),'audit':sum(r['record_role']=='AUDIT' for r in rows)},open(Path(args.out)/f'summary_master_{y}.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
  print(json.dumps({'year':y,'rows':len(rows),'production':sum(r['record_role']=='PRODUCTION' for r in rows),'diagnostic':sum(r['record_role']=='DIAGNOSTIC' for r in rows),'audit':sum(r['record_role']=='AUDIT' for r in rows)},ensure_ascii=False))
if __name__=='__main__':main()
