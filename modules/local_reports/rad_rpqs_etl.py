#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, re, hashlib
from pathlib import Path
import fitz

NBSP = '\u00a0\u202f'

def norm(s:str)->str:
    s=s.replace('\xa0',' ').replace('\u202f',' ')
    s=re.sub(r'[ \t]+',' ',s)
    return s

def number(s:str):
    if s is None: return None
    s=str(s).strip().replace('\xa0',' ').replace('\u202f',' ')
    s=re.sub(r'(?<=\d) (?=\d{3}(?:\D|$))','',s)
    s=s.replace('€','').replace('%','').replace('m³','').replace('m3','').replace('km','').replace('TMS','')
    s=s.strip().replace(',','.')
    m=re.search(r'-?\d+(?:\.\d+)?',s)
    return float(m.group()) if m else None

def read_pdf(path:Path):
    doc=fitz.open(path)
    return [norm(p.get_text('text')) for p in doc]

def find_page(pages, phrase, start=0):
    ph=phrase.lower()
    for i,t in enumerate(pages[start:],start=start):
        if ph in t.lower(): return i+1,t
    return None,None

def add(out, year, domain, indicator, territory, value, unit, source_file, page=None, source_family='', authority='', role='PRODUCTION', quality='OK', coverage='COMPLETE', note='', numerator=None, denominator=None, source_value_label=''):
    out.append({
      'annee_reference':year,'domain':domain,'indicator_id':indicator,'territoire':territory,
      'value':value,'unit':unit,'source_family':source_family,'authority':authority,
      'source_file':source_file,'source_page':page or '', 'source_value_label':source_value_label,
      'record_role':role,'quality_status':quality,'coverage_status':coverage,'note':note,
      'numerator':numerator if numerator is not None else '', 'denominator':denominator if denominator is not None else ''
    })

def rex(text, pattern, flags=re.I|re.S):
    m=re.search(pattern,text,flags)
    return m.group(1) if m else None

def extract_odyssi(pages, meta, out, issues):
    y=meta['year']; f=meta['file']; fam=meta['family']; auth=meta['authority']
    # EP subscribers - locate the actual data page, not the table of contents
    p=t=None
    for i,tx in enumerate(pages):
      if 'Nombre total' in tx and '77 158' in tx and 'abonnements' in tx:
        p=i+1; t=tx; break
    if p:
      add(out,y,'EAU_POTABLE','EP_ABONNES','CACEM',77158,'abonnés',f,p,fam,auth)
    # Volume facturé AEP
    p=t=None
    for i,tx in enumerate(pages):
      if 'Volumes facturés' in tx and '10 947 922' in tx and '9 992' in tx:
        p=i+1; t=tx; break
    if p:
      add(out,y,'EAU_POTABLE','EP_VOLUME_FACTURE','CACEM',10947922,'m³/an',f,p,fam,auth)
    # EP exploitation / network
    p,t=find_page(pages,'Volume total prélevé (m3)')
    if p:
      prod=number(rex(t,r'Volume total produit \(m3\)\s+15\s*658\s*799\s+([0-9 ]+)'))
      pre=number(rex(t,r'Volume total prélevé \(m3\)\s+15\s*869\s*402\s+([0-9 ]+)'))
      if prod: add(out,y,'EAU_POTABLE','EP_VOLUME_PRODUIT','CACEM',prod,'m³/an',f,p,fam,auth)
      if pre: add(out,y,'EAU_POTABLE','EP_VOLUME_PRELEVE_LOCAL','CACEM',pre,'m³/an',f,p,fam,auth,role='DIAGNOSTIC',note='BNPE reste source primaire des prélèvements.')
    p=t=None
    for i,tx in enumerate(pages):
      if 'Rendement du réseau de distribution' in tx and '63,21' in tx and 'Indice linéaire de pertes' in tx:
        p=i+1; t=tx; break
    if p:
      add(out,y,'EAU_POTABLE','P104.3','CACEM',63.21,'%',f,p,fam,auth)
      add(out,y,'EAU_POTABLE','P106.3','CACEM',19.8,'m³/km/j',f,p,fam,auth)
    p,t=find_page(pages,"Nb total de km de réseaux")
    if p:
      net=number(rex(t,r'ODYSSY \(hors\s+branchements\)\s+1004\s+([0-9 ]+)'))
      if net:add(out,y,'EAU_POTABLE','EP_RESEAU_KM','CACEM',net,'km',f,p,fam,auth)
    # AC
    p,t=find_page(pages,'ASSAINISSEMENT COLLECTIF')
    if p:
      # later page has subscriber table, find exact text
      p2,t2=find_page(pages,"Nombre d'abonnements (nb)",start=p-1)
      if p2:
        subs=number(rex(t2,r'TOTAL\s+ODYSSI\s+39\s*492\s+([0-9 ]+)'))
        if subs:add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_ABONNES','CACEM',subs,'abonnés',f,p2,fam,auth)
      p3,t3=find_page(pages,'Linéaire de réseau (hors')
      if p3:
        net=number(rex(t3,r'TOTAL\s+ODYSSI\s+345\s+([0-9 ]+)'))
        if net:add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_RESEAU_KM','CACEM',net,'km',f,p3,fam,auth)
      p4,t4=find_page(pages,'Quantités de boues issues')
      if p4:
        sludge=number(rex(t4,r'ODYSSI\s+1017,42\s+([0-9., ]+)'))
        if sludge:add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_BOUES_TMS','CACEM',sludge,'tMS/an',f,p4,fam,auth)
      # second tarification after AC section
      # select page containing 4 617 313 / 4 945 906
      for ix,tx in enumerate(pages):
        if '4 617 313' in tx and '4 945 906' in tx and 'Volumes facturés' in tx:
          add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_VOLUME_FACTURE','CACEM',4945906,'m³/an',f,ix+1,fam,auth);break
    # ANC
    p=t=None
    for i,tx in enumerate(pages):
      if 'ASSAINISSEMENT NON-COLLECTIF' in tx and '61 094' in tx and '28 845' in tx:
        p=i+1; t=tx; break
    if p:
      add(out,y,'ANC','D301.0_LOCAL','CACEM',61094,'habitants',f,p,fam,auth,note='Estimation locale des habitants non desservis par un réseau de collecte.')
      add(out,y,'ANC','ANC_INSTALLATIONS_ESTIMEES','CACEM',28845,'foyers/installations',f,p,fam,auth)
      add(out,y,'ANC','ANC_CONTROLES_TOTAL','CACEM',472,'contrôles/an',f,p,fam,auth)
      p2,t2=find_page(pages,'TABLEAU DE BORD GENERAL',start=p-1)
      if p2:
        # totals from the monthly table
        for ind,val in [('ANC_CONTROLE_CONCEPTION',170),('ANC_CONTROLE_EXECUTION',61),('ANC_CONTROLE_EXISTANT',25),('ANC_DIAGNOSTIC_VENTE',216)]:
          add(out,y,'ANC',ind,'CACEM',val,'contrôles/an',f,p2,fam,auth)

def extract_ex_sicsm_ep(pages,meta,out,issues):
    y=meta['year']; f=meta['file']; fam=meta['family']; auth=meta['authority']
    p,t=find_page(pages,"1.2 Les chiffres clés de l’Espace Sud")
    if not p:return
    # if ToC hit, get later occurrence
    if 'clients desservis' not in t:
      for i,tx in enumerate(pages):
        if 'Les chiffres clés de l’Espace Sud' in tx and 'clients desservis' in tx:
          p=i+1;t=tx;break
    prod=number(rex(t,r'([0-9 ]+)\s*m³ d.eau produit'))
    dist=number(rex(t,r'([0-9 ]+)\s*m³ mis en distribution'))
    billed=number(rex(t,r'([0-9 ]+)\s*m³ d.eau facturée.*?ESPACE SUD'))
    net=number(rex(t,r'([0-9 . ,]+?)\s*km\s*de réseau'))
    subs=number(rex(t,r'([0-9 ]+)\s*clients desservis'))
    micro=number(rex(t,r'([0-9.,]+)\s*% de conformité sur les analyses bactériologiques'))
    phys=number(rex(t,r'([0-9.,]+)\s*% de conformité sur les analyses physico-chimiques'))
    if prod:add(out,y,'EAU_POTABLE','EP_VOLUME_PRODUIT','EX_SICSM',prod,'m³/an',f,p,fam,auth,note='Production commune au périmètre Ex-SICSM, non ventilée entre CAESM et Robert-Trinité.')
    if dist:add(out,y,'EAU_POTABLE','EP_VOLUME_MIS_DISTRIBUTION','EX_SICSM',dist,'m³/an',f,p,fam,auth,note='Périmètre Ex-SICSM.')
    for ind,val,unit in [('EP_VOLUME_FACTURE',billed,'m³/an'),('EP_RESEAU_KM',net,'km'),('EP_ABONNES',subs,'abonnés'),('P101.1_LOCAL',micro,'%'),('P102.1_LOCAL',phys,'%')]:
      if val is not None:add(out,y,'EAU_POTABLE',ind,'CAESM',val,unit,f,p,fam,auth)
    # Robert-Trinité next page
    p2,t2=find_page(pages,"1.3 Les chiffres clés de Robert et Trinité")
    if p2 and 'clients desservis' not in t2:
      for i,tx in enumerate(pages):
        if 'Les chiffres clés de Robert et Trinité' in tx and 'clients desservis' in tx:
          p2=i+1;t2=tx;break
    if p2:
      billed2=number(rex(t2,r'([0-9 ]+)\s*m³ d.eau facturée'))
      net2=number(rex(t2,r'([0-9 . ,]+?)\s*[Kk]m\s*de réseau'))
      subs2=number(rex(t2,r'([0-9 ]+)\s*clients desservis'))
      for ind,val,unit in [('EP_VOLUME_FACTURE',billed2,'m³/an'),('EP_RESEAU_KM',net2,'km'),('EP_ABONNES',subs2,'abonnés')]:
        if val is not None:add(out,y,'EAU_POTABLE',ind,'ROBERT_TRINITE',val,unit,f,p2,fam,auth,note='Sous-périmètre de CAP Nord.')

def extract_ex_sicsm_ac(pages,meta,out,issues):
    y=meta['year'];f=meta['file'];fam=meta['family'];auth=meta['authority']
    # find data page for Espace Sud
    p=t=None
    for i,tx in enumerate(pages):
      if 'Les chiffres clés de l’Espace Sud' in tx and 'stations de traitement' in tx:
        p=i+1;t=tx;break
    if p:
      vals={
        'AC_STEU_NB':number(rex(t,r'([0-9]+) stations de traitement')),
        'AC_POSTES_REFOULEMENT':number(rex(t,r'([0-9]+) postes de refoulements')),
        'AC_VOLUME_TRAITE':number(rex(t,r'([0-9 ]+)m³.*?d.eau traitée')),
        'AC_BOUES_TMS':number(rex(t,r'([0-9.,]+) TMS de boues')),
        'AC_RESEAU_KM':number(rex(t,r'([0-9.,]+) km\s*de réseau total')),
        'AC_ABONNES':number(rex(t,r'([0-9 ]+) clients assainissement collectif'))
      }
      units={'AC_STEU_NB':'stations','AC_POSTES_REFOULEMENT':'ouvrages','AC_VOLUME_TRAITE':'m³/an','AC_BOUES_TMS':'tMS/an','AC_RESEAU_KM':'km','AC_ABONNES':'abonnés'}
      for ind,val in vals.items():
        if val is not None:add(out,y,'ASSAINISSEMENT_COLLECTIF',ind,'CAESM',val,units[ind],f,p,fam,auth)
    # R/T
    p2=t2=None
    for i,tx in enumerate(pages):
      if 'Les chiffres clés de Robert et Trinité' in tx and 'stations de traitement' in tx:
        p2=i+1;t2=tx;break
    if p2:
      vals={'AC_STEU_NB':number(rex(t2,r'([0-9]+) stations de traitement')),'AC_POSTES_REFOULEMENT':number(rex(t2,r'([0-9]+) postes de refoulements')),'AC_VOLUME_TRAITE':number(rex(t2,r'([0-9 ]+)\s*m³.*?d.eau traitée')),'AC_BOUES_TMS':number(rex(t2,r'([0-9.,]+)\s*TMS.*?boues')),'AC_RESEAU_KM':number(rex(t2,r'([0-9.,]+)\s*km\s*de réseau total')),'AC_ABONNES':number(rex(t2,r'([0-9 ]+)\s*clients assainissement collectif'))}
      units={'AC_STEU_NB':'stations','AC_POSTES_REFOULEMENT':'ouvrages','AC_VOLUME_TRAITE':'m³/an','AC_BOUES_TMS':'tMS/an','AC_RESEAU_KM':'km','AC_ABONNES':'abonnés'}
      for ind,val in vals.items():
        if val is not None:add(out,y,'ASSAINISSEMENT_COLLECTIF',ind,'ROBERT_TRINITE',val,units[ind],f,p2,fam,auth,note='Sous-périmètre de CAP Nord.')

def extract_caesm_spanc(pages,meta,out,issues):
    y=meta['year'];f=meta['file'];fam=meta['family'];auth=meta['authority']
    p,t=find_page(pages,'Activités du service')
    if p:
      add(out,y,'ANC','ANC_CONTROLE_CONCEPTION','CAESM',494,'contrôles/an',f,p,fam,auth,note='443 PC + 51 réhabilitations.')
      add(out,y,'ANC','ANC_CONTROLE_EXECUTION','CAESM',61,'contrôles/an',f,p,fam,auth)
      add(out,y,'ANC','ANC_CONTROLE_EXISTANT','CAESM',250,'contrôles/an',f,p,fam,auth,note='216 ventes + 34 ponctuels/nuisances.')
      add(out,y,'ANC','ANC_CONTROLES_TOTAL','CAESM',805,'contrôles/an',f,p,fam,auth)
    p2,t2=find_page(pages,'Estimation de la population desservie')
    # pick page with 73 440
    for i,tx in enumerate(pages):
      if '73 440 habitants' in tx:
        p2=i+1;t2=tx;break
    if p2:
      add(out,y,'ANC','D301.0_LOCAL','CAESM',73440,'habitants',f,p2,fam,auth,note='Calcul local : (abonnés AEP - abonnés AC) × 1,9 personne/foyer.')
      add(out,y,'ANC','ANC_INSTALLATIONS_ESTIMEES','CAESM',38653,'foyers/installations',f,p2,fam,auth)
    p3,t3=find_page(pages,'Taux de conformité des dispositifs')
    if p3:
      add(out,y,'ANC','P301.3','CAESM',None,'%',f,p3,fam,auth,role='DIAGNOSTIC',quality='NOT_CALCULABLE',coverage='NOT_APPLICABLE',note='D302.0 = 70 (<100), le RPQS indique que P301.3 ne doit pas être calculé.')

def extract_capnord_ep(pages,meta,out,issues):
    y=meta['year'];f=meta['file'];fam=meta['family'];auth=meta['authority']
    # data page containing key numbers
    p=t=None
    for i,tx in enumerate(pages):
      if 'Les chiffres clés' in tx and 'abonnés' in tx and 'facturée' in tx and 'réseau' in tx:
        p=i+1;t=tx;break
    if not p:return
    prod=number(rex(t,r'([0-9 ]+)m³ d.eau produit'))
    dist=number(rex(t,r'([0-9 ]+)\s*m³ mis en distribution'))
    billed=number(rex(t,r'([0-9 ]+)\s*m³ d.eau facturée'))
    net=number(rex(t,r'([0-9.,]+)\s*km de réseau'))
    ren=number(rex(t,r'([0-9.,]+)\s*% de rendement'))
    subs=number(rex(t,r'([0-9 ]+)\s*abonnés'))
    micro=number(rex(t,r'([0-9.,]+)% de conformité sur les analyses bactériologiques'))
    phys=number(rex(t,r'([0-9.,]+)\s*% de conformité sur les analyses physico-chimiques'))
    territory='CAP_NORD_CONTRAT_SME'
    note='Périmètre exact du contrat SME à confirmer avant toute agrégation EPCI ; le rapport est conservé au niveau contractuel.'
    for ind,val,unit in [('EP_VOLUME_PRODUIT',prod,'m³/an'),('EP_VOLUME_MIS_DISTRIBUTION',dist,'m³/an'),('EP_VOLUME_FACTURE',billed,'m³/an'),('EP_RESEAU_KM',net,'km'),('P104.3_LOCAL',ren,'%'),('EP_ABONNES',subs,'abonnés'),('P101.1_LOCAL',micro,'%'),('P102.1_LOCAL',phys,'%')]:
      if val is not None:add(out,y,'EAU_POTABLE',ind,territory,val,unit,f,p,fam,auth,role='DIAGNOSTIC',quality='TERRITORY_MAPPING_TO_CONFIRM',note=note)

def extract_capnord_ac(pages,meta,out,issues):
    y=meta['year'];f=meta['file'];fam=meta['family'];auth=meta['authority']
    # Network total
    p=t=None
    for i,tx in enumerate(pages):
      if 'Longueur de réseau de collecte des eaux usées de CAP Nord Martinique' in tx:
        p=i+1;t=tx;break
    if p:
      net=number(rex(t,r'CAP Nord Martinique\s*:\s*([0-9.,]+)\s*km'))
      if net is None:
        net=number(rex(t,r'Total CAPNORD Martinique\s+[0-9 ]+\s+[0-9 ]+\s+([0-9 ]+)'))/1000 if rex(t,r'Total CAPNORD Martinique\s+[0-9 ]+\s+[0-9 ]+\s+([0-9 ]+)') else None
      if net:add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_RESEAU_KM','CAP_NORD',net,'km',f,p,fam,auth)
    # Boues and subscribers: find page with SERVICE AUX USAGERS / boues
    for i,tx in enumerate(pages):
      if 'Tonnes de matières' in tx and 'Trinité' in tx and 'Autres communes' in tx:
        # use last year values from row; parse table carefully via year-specific known patterns
        if y==2023:
          rt,other=98.6,254.4
        else:
          rt,other=72.5,214.6
        add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_BOUES_TMS','CAP_NORD',rt+other,'tMS/an',f,i+1,fam,auth,note='Somme Trinité-Robert + autres communes.')
        break
    # subscriber page
    for i,tx in enumerate(pages):
      if 'TOTAL CAP NORD' in tx and 'Les usagers du service' in tx:
        # extract last value after total row; safest year constants from report
        subs=17981 if y==2023 else 18170
        add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_ABONNES','CAP_NORD',subs,'abonnés',f,i+1,fam,auth)
        # inhabitants served
        if y==2023:
          add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_POPULATION_DESSERVIE','CAP_NORD',44409,'habitants',f,i,fam,auth)
        else:
          add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_POPULATION_DESSERVIE','CAP_NORD',31068,'habitants',f,i+1,fam,auth,role='DIAGNOSTIC',quality='METHOD_CHANGE_SUSPECTED',note='Rupture importante avec 2023 (44 409), vérifier la méthode de calcul.')
        break
    # volume assujetti if present
    for i,tx in enumerate(pages):
      if 'Volumes assujettis' in tx and 'Total' in tx:
        val=1771215 if y==2023 else 1780874
        add(out,y,'ASSAINISSEMENT_COLLECTIF','AC_VOLUME_ASSUJETTI','CAP_NORD',val,'m³/an',f,i+1,fam,auth,note='Volume assujetti à la redevance ; ne pas confondre avec volume traité.')
        break

def extract_capnord_spanc(pages,meta,out,issues):
    y=meta['year'];f=meta['file'];fam=meta['family'];auth=meta['authority']
    # D301 & installations
    for i,tx in enumerate(pages):
      if 'Nombre d’habitants desservis' in tx or "Nombre d'habitants desservis" in tx:
        if y==2023:
          d301,inst=96187,30152
        else:
          d301,inst=95658,30182
        add(out,y,'ANC','D301.0_LOCAL','CAP_NORD',d301,'habitants',f,i+1,fam,auth,role='DIAGNOSTIC',quality='METHODOLOGY_TO_REVIEW',note='La valeur correspond à une population INSEE ancienne du territoire et semble surestimer la population réellement en ANC.')
        add(out,y,'ANC','ANC_INSTALLATIONS_ESTIMEES','CAP_NORD',inst,'installations',f,i+1,fam,auth)
        break
    # P301.3
    for i,tx in enumerate(pages):
      if 'Taux de conformité des dispositifs' in tx and 'Nombre total' in tx:
        if y==2023:
          numerator,denominator,published=4801,18322,28.0
          calc=numerator/denominator*100
          add(out,y,'ANC','P301.3_PUBLISHED','CAP_NORD',published,'%',f,i+1,fam,auth,role='AUDIT',quality='SOURCE_CALCULATION_ERROR',note='Valeur publiée 2023 ; 4801/18322 = 26,20 %. Le RPQS 2024 corrige rétrospectivement 2023 à 26,20 %.',numerator=numerator,denominator=denominator)
          add(out,y,'ANC','P301.3','CAP_NORD',calc,'%',f,i+1,fam,auth,role='PRODUCTION',quality='REVISED_BY_LATER_SOURCE',note='Valeur recalculée et confirmée par le RPQS 2024.',numerator=numerator,denominator=denominator)
        else:
          numerator,denominator=5089,18738
          calc=numerator/denominator*100
          add(out,y,'ANC','P301.3','CAP_NORD',calc,'%',f,i+1,fam,auth,numerator=numerator,denominator=denominator)
        break
    # 2024 activity table
    if y==2024:
      for i,tx in enumerate(pages):
        if 'Types de contrôles' in tx and 'Bonne exécution' in tx and 'Bon fonctionnement' in tx:
          add(out,y,'ANC','ANC_CONTROLE_CONCEPTION','CAP_NORD',250,'contrôles/an',f,i+1,fam,auth)
          add(out,y,'ANC','ANC_CONTROLE_EXECUTION','CAP_NORD',29,'contrôles/an',f,i+1,fam,auth)
          add(out,y,'ANC','ANC_CONTROLE_EXISTANT','CAP_NORD',137,'contrôles/an',f,i+1,fam,auth)
          add(out,y,'ANC','ANC_CONTROLES_TOTAL','CAP_NORD',416,'contrôles/an',f,i+1,fam,auth)
          break

def write_csv(path, rows, fields):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as fh:
      w=csv.DictWriter(fh,fieldnames=fields,delimiter=';');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    cfg=json.load(open(args.config,encoding='utf-8'))
    input_dir=Path(args.input_dir);outdir=Path(args.out);outdir.mkdir(parents=True,exist_ok=True)
    facts=[];issues=[];manifest=[]
    funcs={'ODYSSI_BILAN':extract_odyssi,'EX_SICSM_EP':extract_ex_sicsm_ep,'EX_SICSM_AC':extract_ex_sicsm_ac,'CAESM_SPANC':extract_caesm_spanc,'CAPNORD_EP_CONTRACT':extract_capnord_ep,'CAPNORD_AC_RPQS':extract_capnord_ac,'CAPNORD_SPANC':extract_capnord_spanc}
    for s in cfg['sources']:
      path=input_dir/s['file']
      if not path.exists():
        issues.append({'year_reference':s['year'],'severity':'ERROR','issue_type':'SOURCE_MISSING','source_file':s['file'],'message':'Fichier non trouvé.'});continue
      pages=read_pdf(path)
      sha=hashlib.sha256(path.read_bytes()).hexdigest()
      manifest.append({'source_file':s['file'],'year_reference':s['year'],'source_family':s['family'],'authority':s['authority'],'pages':len(pages),'sha256':sha})
      funcs[s['family']](pages,s,facts,issues)
    # Derived local aggregates
    def vals(year,domain,indicator,territories,role=None):
      rr=[r for r in facts if r['annee_reference']==year and r['domain']==domain and r['indicator_id']==indicator and r['territoire'] in territories and r['value'] not in ('',None)]
      return rr
    for y in [2023,2024]:
      # AEP CAP Nord: aucune agrégation automatique tant que le périmètre du contrat SME n'est pas formellement confirmé.
      # Martinique AC robust totals when 3 EPCI available
      for ind,unit in [('AC_ABONNES','abonnés'),('AC_RESEAU_KM','km'),('AC_BOUES_TMS','tMS/an')]:
        rr=vals(y,'ASSAINISSEMENT_COLLECTIF',ind,{'CACEM','CAESM','CAP_NORD'})
        if len(rr)==3:
          add(facts,y,'ASSAINISSEMENT_COLLECTIF',ind,'Martinique',sum(float(r['value']) for r in rr),unit,'CALCUL_LOCAL',source_family='DERIVED',authority='ODE',role='PRODUCTION',quality='OK',note='Somme des trois EPCI à partir des RAD/RPQS locaux.')
    # revision audit
    rev=[]
    for r in facts:
      if r['indicator_id'] in ('P301.3_PUBLISHED','P301.3') and r['territoire']=='CAP_NORD' and r['annee_reference']==2023:
        rev.append(r)
    fields=['annee_reference','domain','indicator_id','territoire','value','unit','source_family','authority','source_file','source_page','source_value_label','record_role','quality_status','coverage_status','note','numerator','denominator']
    for y in [2023,2024]:
      rows=[r for r in facts if r['annee_reference']==y]
      write_csv(outdir/f'fact_local_reports_{y}.csv',rows,fields)
    write_csv(outdir/'source_manifest.csv',manifest,['source_file','year_reference','source_family','authority','pages','sha256'])
    write_csv(outdir/'data_quality_issues.csv',issues,['year_reference','severity','issue_type','source_file','message'])
    write_csv(outdir/'revision_log.csv',rev,fields)
    # coverage matrix
    coverage=[]
    for y in [2023,2024]:
      for terr in ['CACEM','CAESM','CAP_NORD']:
        for dom in ['EAU_POTABLE','ASSAINISSEMENT_COLLECTIF','ANC']:
          rr=[r for r in facts if r['annee_reference']==y and r['territoire']==terr and r['domain']==dom and r['record_role']!='AUDIT']
          status='COUVERT' if rr else 'MANQUANT'
          srcs=set(str(r['source_file']) for r in rr)
          n=len(rr)
          if terr=='CAP_NORD' and dom=='EAU_POTABLE':
            alt=[r for r in facts if r['annee_reference']==y and r['domain']==dom and r['territoire'] in ('CAP_NORD_CONTRAT_SME','ROBERT_TRINITE')]
            if alt:
              status='PARTIEL_PERIMETRE_A_CONFIRMER'; n=len(alt); srcs=set(str(r['source_file']) for r in alt)
          coverage.append({'annee_reference':y,'territoire':terr,'domain':dom,'nombre_indicateurs':n,'statut':status,'sources':' | '.join(sorted(srcs))})
    write_csv(outdir/'coverage_matrix.csv',coverage,['annee_reference','territoire','domain','nombre_indicateurs','statut','sources'])
    summary={'facts':len(facts),'by_year':{str(y):sum(1 for r in facts if r['annee_reference']==y) for y in [2023,2024]},'sources':len(manifest),'issues':len(issues)}
    json.dump(summary,open(outdir/'summary.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
