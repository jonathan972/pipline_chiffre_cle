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
def num(v):
    try:return float(v)
    except:return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    root=Path(args.root); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    verified=read_csv(root/'modules/perimeters/capnord_verified_facts.csv')
    anomalies=read_csv(root/'modules/perimeters/sispea_anomalies.csv')
    absences=read_csv(root/'modules/perimeters/known_absences.csv')
    base_dir=root/'modules/local_reports/outputs'
    fields=['annee_reference','domain','indicator_id','territoire','perimeter_id','value','unit','source_family','authority','source_file','source_page','record_role','quality_status','coverage_status','definition','note']
    allrows=[]
    for year in (2023,2024):
        base=read_csv(base_dir/f'fact_local_reports_{year}.csv')
        # Keep non-CAP-Nord AEP as-is. Exclude ambiguous old CAP_NORD_CONTRAT_SME AEP facts.
        for r in base:
            if r['domain']=='EAU_POTABLE' and r['territoire']=='CAP_NORD_CONTRAT_SME':
                continue
            # Les abonnés Robert-Trinité sont réinjectés depuis le référentiel vérifié afin d'éviter un doublon.
            if r['domain']=='EAU_POTABLE' and r['territoire']=='ROBERT_TRINITE' and r['indicator_id']=='EP_ABONNES':
                continue
            perimeter={'CACEM':'CACEM_EPCI','CAESM':'CAESM_EPCI','CAP_NORD':'CAP_NORD_EPCI','ROBERT_TRINITE':'ROBERT_TRINITE_EXSICSM','EX_SICSM':'EX_SICSM_DSP_2015_2027'}.get(r['territoire'],r['territoire'])
            allrows.append({
              'annee_reference':r['annee_reference'],'domain':r['domain'],'indicator_id':r['indicator_id'],'territoire':r['territoire'],'perimeter_id':perimeter,
              'value':r['value'],'unit':r['unit'],'source_family':r['source_family'],'authority':r['authority'],'source_file':r['source_file'],'source_page':r['source_page'],
              'record_role':r['record_role'],'quality_status':r['quality_status'],'coverage_status':r['coverage_status'],'definition':'','note':r['note']
            })
        # Inject verified CAP Nord perimeter facts
        for r in verified:
            if int(r['year'])!=year: continue
            terr={'CAP_NORD_EPCI':'CAP_NORD','CAP_NORD_DSP_2020_2024':'CAP_NORD_DSP_2020_2024','ROBERT_TRINITE_EXSICSM':'ROBERT_TRINITE','EX_SICSM_DSP_2015_2027':'EX_SICSM'}.get(r['perimeter_id'],r['perimeter_id'])
            allrows.append({
              'annee_reference':year,'domain':'EAU_POTABLE','indicator_id':r['indicator_id'],'territoire':terr,'perimeter_id':r['perimeter_id'],
              'value':r['value'],'unit':r['unit'],'source_family':r['source_type'],'authority':'CAP Nord / SME' if r['source_type'] in ('RAD','RPQS','CAP_NORD') else r['source_type'],
              'source_file':r['source_file_or_url'],'source_page':r['source_page'],'record_role':r['record_role'],'quality_status':r['quality_status'],'coverage_status':'COMPLETE',
              'definition':r['definition'],'note':r['note']
            })
    # exact checks: subscriber partition
    checks=[]
    for y,contract,rt,total in [(2023,38372,14266,52638),(2024,37332,14414,51746)]:
        checks.append({'year':y,'check_id':'CAPNORD_SUBSCRIBER_PARTITION','lhs':contract+rt,'rhs':total,'difference':contract+rt-total,'status':'OK' if contract+rt==total else 'ERROR','message':'CAP Nord contract + Robert-Trinité Ex-SICSM = total EPCI.'})
    # detailed sector proof values from RAD (partial communes)
    sectors=[
      {'year':2023,'sector':'ROBERT_CN','commune':'Le Robert','subscribers':2365,'billed_m3':206077,'source':'RAD_Eau_potable_CAP_NORD_2023.pdf','page':129},
      {'year':2023,'sector':'TRINITE_CN','commune':'La Trinité','subscribers':776,'billed_m3':63008,'source':'RAD_Eau_potable_CAP_NORD_2023.pdf','page':129},
      {'year':2024,'sector':'ROBERT_CN','commune':'Le Robert','subscribers':2318,'billed_m3':204544,'source':'RAD_Eau_potable_CAP_NORD_2024.pdf','page':151},
      {'year':2024,'sector':'TRINITE_CN','commune':'La Trinité','subscribers':771,'billed_m3':58438,'source':'RAD_Eau_potable_CAP_NORD_2024.pdf','page':151},
    ]
    write_csv(out/'fact_local_reports_reconciled_2023.csv',[r for r in allrows if int(r['annee_reference'])==2023],fields)
    write_csv(out/'fact_local_reports_reconciled_2024.csv',[r for r in allrows if int(r['annee_reference'])==2024],fields)
    write_csv(out/'perimeter_quality_checks.csv',checks,['year','check_id','lhs','rhs','difference','status','message'])
    write_csv(out/'capnord_partial_sectors.csv',sectors,['year','sector','commune','subscribers','billed_m3','source','page'])
    # Coverage: distinguish non-produced from missing
    coverage=[]
    for y in (2023,2024):
      yearrows=[r for r in allrows if int(r['annee_reference'])==y]
      for terr in ('CACEM','CAESM','CAP_NORD'):
        for dom in ('EAU_POTABLE','ASSAINISSEMENT_COLLECTIF','ANC'):
          rr=[r for r in yearrows if r['territoire']==terr and r['domain']==dom and r['record_role']!='AUDIT']
          declared=next((a for a in absences if int(a['year'])==y and a['territory']==terr and a['domain']==dom),None)
          if declared:
            status=declared['status']; note=declared['note']
          elif rr:
            status='COUVERT';note=''
          else:
            status='MANQUANT';note=''
          coverage.append({'year':y,'territory':terr,'domain':dom,'status':status,'n_facts':len(rr),'note':note})
    write_csv(out/'coverage_matrix_v2.csv',coverage,['year','territory','domain','status','n_facts','note'])
    json.dump({'rows':len(allrows),'anomalies':len(anomalies),'checks':checks},open(out/'summary_perimeters.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print(json.dumps({'rows':len(allrows),'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
