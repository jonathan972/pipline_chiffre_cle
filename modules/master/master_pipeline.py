#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from typing import Any


def read_scsv(path: Path) -> list[dict[str,str]]:
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f,delimiter=';'))

def read_csv(path: Path) -> list[dict[str,str]]:
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def write_scsv(path: Path, rows: list[dict[str,Any]], fields: list[str]):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=';'); w.writeheader(); w.writerows(rows)

def fnum(v):
    if v in ('',None): return None
    return float(v)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--year',type=int,default=2022)
    ap.add_argument('--project-root',default='../..')
    ap.add_argument('--out',default='outputs')
    args=ap.parse_args()
    here=Path(__file__).resolve().parent
    root=(here/args.project_root).resolve()
    out=(here/args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.load((here/'config.json').open(encoding='utf-8'))
    y=args.year
    rows=[]
    quality=[]

    def add(indicator_id,domain,territory,value,unit,source_primary,source_detail='',source_file='',snapshot_date='',coverage_status='COMPLETE',quality_status='OK',record_role='PRODUCTION',population_millesime='',note=''):
        rows.append({
            'annee_reference':y,'indicator_id':indicator_id,'domain':domain,'territoire':territory,
            'value': '' if value is None else value,'unit':unit,'source_primary':source_primary,'source_detail':source_detail,
            'source_file':source_file,'snapshot_date':snapshot_date,'coverage_status':coverage_status,
            'quality_status':quality_status,'record_role':record_role,'population_millesime':population_millesime,'note':note
        })

    # INSEE population resolved
    pop_file=root/'modules/insee_population/outputs'/f'fact_population_resolue_2019_2024.csv'
    pops=[r for r in read_scsv(pop_file) if int(r['annee_indicateur'])==y]
    pop_map={r['territoire']:r for r in pops}
    for t in ['Martinique','CACEM','CAESM','CAP_NORD']:
        r=pop_map.get(t)
        if r:
            add('POP_001','POPULATION',t,int(r['population_utilisee']),'hab','INSEE',r['statut_resolution'],pop_file.name,'',
                'COMPLETE' if r['statut_resolution']=='OFFICIEL_MILLESIME_N' else 'FALLBACK',
                'OK' if r['statut_resolution']=='OFFICIEL_MILLESIME_N' else 'INFO','PRODUCTION',r['millesime_population'])

    # BNPE mart indicators
    bnpe_file=root/'modules/bnpe/outputs'/f'mart_bnpe_indicateurs_{y}.csv'
    for r in read_scsv(bnpe_file):
        iid=r['indicator_id']; role='PRODUCTION'; q='OK'; coverage='COMPLETE'; note=r.get('calculation','')
        if iid in {'RES_007','RES_008','RES_009'}:
            role='DIAGNOSTIC'; q='INCOMPLETE_INVENTORY'; coverage='PARTIAL'; note += ' | BNPE non exhaustive pour compter les captages.'
        add(iid,'RESSOURCE','Martinique',fnum(r['value']),r['unit'],'BNPE',r.get('calculation',''),bnpe_file.name,'',coverage,q,role,'',note)

    # SISPEA consolidated
    sis_con_file=root/'modules/sispea/outputs'/f'fact_sispea_consolidee_{y}.csv'
    con=read_scsv(sis_con_file)
    conidx={(r['competence'],r['code']):r for r in con}
    def add_con(iid,domain,comp,code,unit,role='PRODUCTION',quality_status='OK',coverage_status='COMPLETE',note=''):
        r=conidx.get((comp,code))
        if not r: return
        n=float(r['nombre_donnees_utilisees'] or 0)
        add(iid,domain,'Martinique',fnum(r['valeur_consolidee']),unit,'SISPEA',code,r['source_file'],r['date_snapshot'],coverage_status,quality_status,role,'',note or f'{code}; {int(n)} donnée(s) utilisée(s).')
    add_con('EP_005','EAU_POTABLE','EP','VP.056','abonnés')
    add_con('EP_017','EAU_POTABLE','EP','VP.077','km')
    add_con('AC_014','ASSAINISSEMENT_COLLECTIF','AC','VP.056','abonnés',quality_status='REVISED_SNAPSHOT',note='Snapshot SISPEA actuel ; historique susceptible d’avoir été révisé.')
    add_con('AC_001','ASSAINISSEMENT_COLLECTIF','AC','VP.077','km')
    add_con('AC_012','ASSAINISSEMENT_COLLECTIF','AC','VP.208','tMS')
    add_con('ANC_002','ANC','ANC','D301.0','hab',role='DIAGNOSTIC',quality_status='REVISED_SNAPSHOT',note='Population ANC du snapshot courant ; à confronter aux SPANC/ODE.')
    # P301.3 partial coverage
    r=conidx.get(('ANC','P301.3'))
    if r:
        used=int(float(r['nombre_donnees_utilisees'] or 0)); exp=int(cfg['expected_anc_services'])
        cov='COMPLETE' if used>=exp else 'PARTIAL'
        q='OK' if cov=='COMPLETE' else 'COVERAGE_PARTIAL'
        role='PRODUCTION' if cov=='COMPLETE' else 'DIAGNOSTIC'
        add('ANC_013','ANC','Martinique',fnum(r['valeur_consolidee']),'%','SISPEA','P301.3',r['source_file'],r['date_snapshot'],cov,q,role,'',f'{used}/{exp} services utilisés.')

    # SISPEA service-level comparable performance EP
    sis_fact_file=root/'modules/sispea/outputs'/f'fact_sispea_service_{y}.csv'
    sf=read_scsv(sis_fact_file)
    sfidx={(r['service_id'],r['code']):r for r in sf}
    code_to_iid={'P104.3':'EP_019','P106.3':'EP_020','P107.2':'EP_021'}
    units={'P104.3':'%','P106.3':'m3/km/j','P107.2':'%'}
    for terr,sid in cfg['report_comparable_ep_services'].items():
        for code,iid in code_to_iid.items():
            r=sfidx.get((sid,code))
            if r:
                add(iid,'EAU_POTABLE',terr,fnum(r['valeur_num']),units[code],'SISPEA',code,r['source_file'],r['date_snapshot'],'COMPLETE','OK','PRODUCTION','',f'Service SISPEA comparable au périmètre du rapport : {sid}.')

    # ANC variables from service facts
    anc_rows=[r for r in sf if r['competence']=='ANC']
    def sum_code(code): return sum(float(r['valeur_num']) for r in anc_rows if r['code']==code and r['valeur_num'] not in ('',None))
    def count_code(code): return sum(1 for r in anc_rows if r['code']==code and r['valeur_num'] not in ('',None))
    dc306=sum_code('DC.306'); dc332=sum_code('DC.332'); dc333=sum_code('DC.333'); vp334=sum_code('VP.334')
    if dc306: add('ANC_003','ANC','Martinique',dc306,'installations','SISPEA','DC.306',sis_fact_file.name,'','PARTIAL','REVISED_SNAPSHOT','DIAGNOSTIC','','Somme des services renseignés ; contrôle SPANC requis.')
    if dc332 or dc333: add('ANC_010','ANC','Martinique',dc332+dc333,'contrôles/an','SISPEA','DC.332 + DC.333',sis_fact_file.name,'','COMPLETE','OK','PRODUCTION','','Contrôles du neuf = conception + exécution, règle à conserver versionnée.')
    if vp334 or count_code('VP.334'):
        used=count_code('VP.334'); exp=int(cfg['expected_anc_services']); cov='COMPLETE' if used>=exp else 'PARTIAL'
        add('ANC_011','ANC','Martinique',vp334,'contrôles/an','SISPEA','VP.334',sis_fact_file.name,'',cov,'OK' if cov=='COMPLETE' else 'COVERAGE_PARTIAL','PRODUCTION' if cov=='COMPLETE' else 'DIAGNOSTIC','',f'{used}/{exp} services renseignés.')

    # STEU current snapshot primary
    steu_summary_path=root/'modules/steu/outputs'/f'summary_{y}.json'
    if steu_summary_path.exists():
        sm=json.load(steu_summary_path.open(encoding='utf-8')); m=sm['metrics']
        add('AC_003','ASSAINISSEMENT_COLLECTIF','Martinique',m['public_stations_positive_capacity'],'nb','PORTAIL_ERU','Nature=Urbain et capacité>0',sm['source_file'],m.get('latest_source_modification_date',''),'COMPLETE','OK','PRODUCTION','','Inventaire public du snapshot courant.')
        add('AC_004','ASSAINISSEMENT_COLLECTIF','Martinique',m['public_stations_gt_200'],'nb','PORTAIL_ERU','Nature=Urbain et capacité>200 EH',sm['source_file'],m.get('latest_source_modification_date',''),'COMPLETE','REVISED_SNAPSHOT','PRODUCTION','','Le snapshot courant diffère du rapport 2022 historique.')
        add('AC_005','ASSAINISSEMENT_COLLECTIF','Martinique',m['public_capacity_gt_200_eh'],'EH','PORTAIL_ERU','Somme capacité nominale >200 EH',sm['source_file'],m.get('latest_source_modification_date',''),'COMPLETE','REVISED_SNAPSHOT','PRODUCTION','','Le snapshot courant diffère du rapport 2022 historique.')

    # Derived ratios using population
    pop_mq=fnum(pop_map.get('Martinique',{}).get('population_utilisee')) if pop_map.get('Martinique') else None
    ep_sub=next((float(r['value']) for r in rows if r['indicator_id']=='EP_005' and r['territoire']=='Martinique'),None)
    ac_sub=next((float(r['value']) for r in rows if r['indicator_id']=='AC_014' and r['territoire']=='Martinique'),None)
    anc_pop=next((float(r['value']) for r in rows if r['indicator_id']=='ANC_002' and r['territoire']=='Martinique'),None)
    if ep_sub and ac_sub:
        add('AC_016','ASSAINISSEMENT_COLLECTIF','Martinique',ac_sub/ep_sub*100,'%','CALCUL','AC_014 / EP_005 ×100','','','COMPLETE','REVISED_SNAPSHOT','DIAGNOSTIC','',"Part d'abonnés AC parmi les abonnés AEP ; ne pas l'intituler part de population raccordée.")
    if pop_mq and anc_pop:
        pop_mill=pop_map['Martinique']['millesime_population']
        add('ANC_001','ANC','Martinique',anc_pop/pop_mq*100,'%','CALCUL','ANC_002 / POP_001 ×100','','','COMPLETE','REVISED_SNAPSHOT','DIAGNOSTIC',pop_mill,'Part de population relevant de l’ANC d’après le snapshot SISPEA courant.')

    # Validation L/j/hab à partir d'une entrée externe explicite
    manual=read_csv(here/'manual_inputs'/f'manual_external_facts_{y}.csv')
    ep_fact=next((r for r in manual if r['indicator_id']=='EP_006' and r['territoire']=='Martinique'),None)
    if ep_fact and pop_mq:
        val=float(ep_fact['value'])*1000/(pop_mq*365)
        add('EP_001','EAU_POTABLE','Martinique',val,'L/j/hab','RAD_RPQS + INSEE','Volume facturé AEP / population municipale / 365',Path('manual_inputs')/f'manual_external_facts_{y}.csv','', 'COMPLETE','VALIDATION_OK','VALIDATION',pop_map['Martinique']['millesime_population'],'Validation de la formule ; automatisation RAD/RPQS encore à développer.')

    fields=['annee_reference','indicator_id','domain','territoire','value','unit','source_primary','source_detail','source_file','snapshot_date','coverage_status','quality_status','record_role','population_millesime','note']
    rows=sorted(rows,key=lambda r:(r['domain'],r['indicator_id'],r['territoire']))
    write_scsv(out/f'fact_indicateur_master_{y}.csv',rows,fields)
    # Quality report
    for r in rows:
        if r['coverage_status']!='COMPLETE' or r['quality_status'] not in ('OK','VALIDATION_OK'):
            quality.append({'annee_reference':y,'indicator_id':r['indicator_id'],'territoire':r['territoire'],'severity':'INFO' if r['quality_status'] in ('REVISED_SNAPSHOT','VALIDATION_OK') else 'WARNING','coverage_status':r['coverage_status'],'quality_status':r['quality_status'],'message':r['note']})
    qfields=['annee_reference','indicator_id','territoire','severity','coverage_status','quality_status','message']
    write_scsv(out/f'data_quality_master_{y}.csv',quality,qfields)
    summary={'year':y,'rows':len(rows),'production_rows':sum(r['record_role']=='PRODUCTION' for r in rows),'diagnostic_rows':sum(r['record_role']=='DIAGNOSTIC' for r in rows),'validation_rows':sum(r['record_role']=='VALIDATION' for r in rows),'quality_rows':len(quality)}
    json.dump(summary,(out/f'summary_master_{y}.json').open('w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
