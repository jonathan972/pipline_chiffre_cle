#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json
from pathlib import Path


def clean_header(s: str) -> str:
    return str(s or '').replace('\ufeff','').strip().strip('"')


def as_float(v):
    if v is None:
        return None
    s=str(v).strip().replace(',','.')
    if s in {'','N/A','Inc','ND','-'}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_portal(path: Path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        rr=csv.reader(f,delimiter='|')
        headers=[clean_header(x) for x in next(rr)]
        rows=[]
        for vals in rr:
            if len(vals)<len(headers):
                vals += ['']*(len(headers)-len(vals))
            rows.append(dict(zip(headers,vals[:len(headers)])))
    return rows


def load_epci_map(root: Path):
    p=root/'modules'/'perimeters'/'epci_communes.csv'
    out={}
    with p.open('r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f,delimiter=';'):
            out[r['commune_insee'].strip()]=r['epci_code'].strip()
    return out


def write_scsv(path: Path, rows, fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or (list(rows[0].keys()) if rows else [])
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=';')
        w.writeheader(); w.writerows(rows)


def fact(year, iid, territory, value, unit, role, quality, definition, source_file, note='', numerator='', denominator=''):
    return {
        'annee_reference':year,
        'indicator_id':iid,
        'domain':'ANC' if iid.startswith('ANC_') else 'ASSAINISSEMENT_COLLECTIF',
        'territoire':territory,
        'perimeter_id':territory,
        'value':round(value,6) if isinstance(value,float) else value,
        'unit':unit,
        'numerator':numerator,
        'denominator':denominator,
        'source_primary':'PORTAIL_ASSAINISSEMENT_DEAL',
        'source_detail':'Export portail national assainissement - DEAL Martinique',
        'source_file':source_file,
        'coverage_status':'COMPLETE',
        'quality_status':quality,
        'record_role':role,
        'definition':definition,
        'note':note,
    }


def aggregate(rows, year, root: Path, source_file: str):
    epci=load_epci_map(root)
    by_code={}
    for r in rows:
        code=(r.get('Code du STEU') or '').strip()
        if code and code not in by_code:
            by_code[code]=r
    stations=list(by_code.values())

    for r in stations:
        code=(r.get('Code INSEE commune implantation') or '').strip()
        r['_territoire']=epci.get(code,'UNKNOWN')
        r['_capacity']=as_float(r.get('Capacité nominale en EH')) or 0.0

    facts=[]
    summary={}
    territories=['Martinique','CACEM','CAESM','CAP_NORD']
    for terr in territories:
        ss=stations if terr=='Martinique' else [r for r in stations if r['_territoire']==terr]
        priv=[r for r in ss if (r.get('Nature du STEU') or '').strip()=='Privé']
        urban=[r for r in ss if (r.get('Nature du STEU') or '').strip()=='Urbain']
        urban_gt200=[r for r in urban if r['_capacity']>200]

        npriv=len(priv)
        pcap=sum(r['_capacity'] for r in priv)
        nlt500=sum(r['_capacity']<500 for r in priv)
        pctlt500=(100*nlt500/npriv) if npriv else None
        if npriv:
            facts += [
                fact(year,'ANC_005',terr,npriv,'nb','PRODUCTION','OK',
                     "Nombre de STEU de nature 'Privé' en service dans l'export du portail.",source_file),
                fact(year,'ANC_006',terr,pcap,'EH','PRODUCTION','OK',
                     "Somme des capacités nominales des STEU de nature 'Privé'.",source_file),
                fact(year,'ANC_008',terr,pctlt500,'%','PRODUCTION','OK',
                     "Part des STEU privées dont la capacité nominale est strictement inférieure à 500 EH.",source_file,
                     numerator=nlt500,denominator=npriv),
            ]

        public_cap_gt200=sum(r['_capacity'] for r in urban_gt200)
        if terr=='Martinique' and public_cap_gt200:
            facts.append(fact(year,'ANC_007',terr,100*pcap/public_cap_gt200,'%','PRODUCTION','OK',
                "Capacité privée / capacité nominale cumulée des STEU urbaines > 200 EH.",source_file,
                note='Définition alignée sur le rapport 2022.',numerator=pcap,denominator=public_cap_gt200))

        known=[r for r in priv if (r.get('Conformité globale STEU réglementaire performances') or '').strip() in {'Oui','Non'}]
        if npriv:
            facts.append(fact(year,'ANC_009_CANDIDATE',terr,100*len(known)/npriv,'%','DIAGNOSTIC','DEFINITION_TO_CONFIRM',
                "Part des STEU privées disposant d'un statut de conformité globale réglementaire de performance Oui/Non.",source_file,
                note="Ne pas publier comme ANC_009 avant validation que ce statut équivaut à 'données de conformité transmises'.",
                numerator=len(known),denominator=npriv))

        n_urban=len(urban); n_gt=len(urban_gt200); cap_gt=sum(r['_capacity'] for r in urban_gt200)
        if n_urban:
            facts.append(fact(year,'AC_003',terr,n_urban,'nb','PRODUCTION','OK',
                "Nombre de STEU de nature 'Urbain' en service.",source_file))
        if n_gt:
            facts.append(fact(year,'AC_004',terr,n_gt,'nb','PRODUCTION','OK',
                "Nombre de STEU urbaines de capacité nominale strictement supérieure à 200 EH.",source_file))
            facts.append(fact(year,'AC_005',terr,cap_gt,'EH','PRODUCTION','OK',
                "Somme des capacités nominales des STEU urbaines > 200 EH.",source_file))
            caps=sorted((r['_capacity'] for r in urban_gt200),reverse=True)
            top4=sum(caps[:4]); small42=sum(sorted(caps)[:min(42,len(caps))])
            facts.append(fact(year,'AC_006',terr,100*top4/cap_gt,'%','PRODUCTION','OK',
                "Part de capacité nominale portée par les 4 plus grosses STEU urbaines >200 EH.",source_file,
                numerator=top4,denominator=cap_gt))
            facts.append(fact(year,'AC_007',terr,100*small42/cap_gt,'%','PRODUCTION','OK',
                "Part de capacité nominale portée par les 42 plus petites STEU urbaines >200 EH.",source_file,
                numerator=small42,denominator=cap_gt))
            conf=[r for r in urban_gt200 if (r.get('Conformité globale agglo réglementaire') or '').strip()=='Oui']
            conf_cap=sum(r['_capacity'] for r in conf)
            facts.append(fact(year,'AC_008',terr,100*conf_cap/cap_gt,'%','DIAGNOSTIC','DEFINITION_TO_VALIDATE',
                "Part de capacité des STEU urbaines >200 EH associées à une agglomération globalement conforme.",source_file,
                note='Valider la définition de conformité éditoriale du millésime avant publication.',
                numerator=conf_cap,denominator=cap_gt))
            facts.append(fact(year,'AC_009',terr,100*len(conf)/n_gt,'%','DIAGNOSTIC','DEFINITION_TO_VALIDATE',
                "Part des STEU urbaines >200 EH associées à une agglomération globalement conforme.",source_file,
                note='Valider la définition de conformité éditoriale du millésime avant publication.',
                numerator=len(conf),denominator=n_gt))

        sludge=sum(as_float(r.get('Prod boues sans réactif (tMS/an)')) or 0 for r in urban)
        if n_urban:
            facts.append(fact(year,'AC_012_PORTAL',terr,sludge,'tMS/an','VALIDATION','PORTAL_CONTROL',
                "Somme de 'Prod boues sans réactif (tMS/an)' des STEU urbaines.",source_file,
                note='Contrôle secondaire : le reporting privilégie les RAD/RPQS locaux pour AC_012.'))

        summary[terr]={
            'private_count':npriv,'private_capacity_eh':pcap,
            'private_lt500_count':nlt500,'private_lt500_pct':pctlt500,
            'urban_count':n_urban,'urban_gt200_count':n_gt,'urban_gt200_capacity_eh':cap_gt,
        }

    normalized=[]
    keep=['Code du STEU','Nom du STEU','Nature du STEU','Etat du STEU en '+str(year),
          'Commune implantation','Code INSEE commune implantation','Capacité nominale en EH',
          'Conformité globale STEU réglementaire performances','Conformité globale agglo réglementaire',
          'Existence manuel autosurveillance STEU','Validation manuel autosurveillance STEU',
          'Prod boues sans réactif (tMS/an)']
    for r in stations:
        row={k:r.get(k,'') for k in keep}
        row['EPCI']=r['_territoire']; normalized.append(row)
    return facts, normalized, summary


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--year',type=int,required=True)
    ap.add_argument('--input',required=True)
    ap.add_argument('--root',default='../..')
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    root=Path(a.root).resolve(); out=Path(a.out).resolve(); inp=Path(a.input).resolve()
    rows=read_portal(inp)
    facts,normalized,summary=aggregate(rows,a.year,root,inp.name)
    write_scsv(out/f'fact_assainissement_portal_{a.year}.csv',facts)
    write_scsv(out/f'steu_inventory_{a.year}.csv',normalized)
    (out/f'summary_assainissement_portal_{a.year}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'year':a.year,'input_rows':len(rows),'fact_rows':len(facts),'summary':summary.get('Martinique')},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
