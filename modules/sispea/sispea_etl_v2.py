#!/usr/bin/env python3
"""ETL SISPEA ODE Martinique v2.

- Lit nativement les exports SISPEA ODS et les anciens XLS BIFF8 sans LibreOffice.
- Conserve les entités de gestion au niveau service.
- Importe la feuille officielle « Données consolidées » lorsqu'elle existe.
- Compare le snapshot courant aux chiffres publiés dans le rapport ODE 2022.

Le lecteur XLS est volontairement limité aux structures BIFF8 utilisées par les exports
SISPEA (NUMBER/RK/MULRK/LABELSST/FORMULA). L'ODS reste le format conseillé pour les
nouvelles extractions.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, math, os, re, struct, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

CODE_RE = re.compile(r"^(?:[DP]\d{3}(?:\.\d+[A-Z]?)?|VP\.\d{3}|DC\.\d{3})$", re.I)

# ---------- utilitaires ----------
def as_float(v: Any) -> float | None:
    if v in (None, ""): return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v): return None
        return float(v)
    s=str(v).strip().replace("\xa0", " ").replace(" ", "").replace(",", ".")
    if not s or s.upper() in {"NC","ND","N/A","NA","-"}: return None
    try: return float(s)
    except ValueError: return None

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def write_csv(path: Path, rows: list[dict[str,Any]], fieldnames: list[str] | None=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames=[]
        for r in rows:
            for k in r:
                if k not in fieldnames: fieldnames.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fieldnames})

def excel_serial_date(v: Any) -> str:
    x=as_float(v)
    if x is None: return str(v or "")
    dt=datetime(1899,12,30)+timedelta(days=x)
    return dt.isoformat(timespec="seconds")

def norm_collectivity(s: Any) -> str:
    x=str(s or "").upper().replace("\x92", "'")
    if "ESPACE SUD" in x: return "CAESM"
    if "PAYS NORD" in x or "CAP NORD" in x: return "CAP_NORD"
    if "CENTRE DE LA MARTINIQUE" in x or "CACEM" in x: return "CACEM"
    return ""

# ---------- ODS ----------
NS={
 'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
 'table':'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
 'text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
}
def read_ods(path: Path) -> dict[str,list[list[Any]]]:
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read('content.xml'))
    out={}
    for tbl in root.findall('.//table:table',NS):
        name=tbl.attrib.get('{%s}name'%NS['table'], 'Sheet')
        rows=[]
        for row in tbl.findall('table:table-row',NS):
            rrep=int(row.attrib.get('{%s}number-rows-repeated'%NS['table'],'1'))
            vals=[]
            for cell in row:
                if cell.tag not in ('{%s}table-cell'%NS['table'],'{%s}covered-table-cell'%NS['table']): continue
                crep=int(cell.attrib.get('{%s}number-columns-repeated'%NS['table'],'1'))
                vt=cell.attrib.get('{%s}value-type'%NS['office'])
                if vt in ('float','currency','percentage'):
                    raw=cell.attrib.get('{%s}value'%NS['office'])
                    try: val=float(raw)
                    except: val=raw
                elif vt=='date': val=cell.attrib.get('{%s}date-value'%NS['office'])
                elif vt=='boolean': val=cell.attrib.get('{%s}boolean-value'%NS['office'])
                else:
                    val='\n'.join(''.join(p.itertext()) for p in cell.findall('.//text:p',NS))
                # huge empty repeats encode unused tail columns
                if val in ('',None) and crep>200: crep=1
                vals.extend([val]*crep)
            while vals and vals[-1] in ('',None): vals.pop()
            if any(v not in ('',None) for v in vals):
                for _ in range(min(rrep,100)): rows.append(vals.copy())
            elif rrep<=5:
                rows.extend([[] for _ in range(rrep)])
        out[name]=rows
    return out

# ---------- CFB / BIFF8 XLS ----------
FREE=0xFFFFFFFF; END=0xFFFFFFFE

def cfb_workbook_stream(path: Path) -> bytes:
    data=path.read_bytes()
    if data[:8] != bytes.fromhex('D0CF11E0A1B11AE1'): raise ValueError(f"{path}: format XLS/CFB non reconnu")
    ss=1<<struct.unpack_from('<H',data,0x1E)[0]; ms=1<<struct.unpack_from('<H',data,0x20)[0]
    numfat=struct.unpack_from('<I',data,0x2C)[0]; firstdir=struct.unpack_from('<I',data,0x30)[0]
    cutoff=struct.unpack_from('<I',data,0x38)[0]; firstmf=struct.unpack_from('<I',data,0x3C)[0]; nummf=struct.unpack_from('<I',data,0x40)[0]
    firstdif=struct.unpack_from('<I',data,0x44)[0]; numdif=struct.unpack_from('<I',data,0x48)[0]
    def sec(s): return data[(s+1)*ss:(s+2)*ss]
    dif=[x for x in struct.unpack_from('<109I',data,0x4C) if x not in (FREE,END)]
    sid=firstdif
    for _ in range(numdif):
        if sid in (FREE,END): break
        a=list(struct.unpack('<%dI'%(ss//4),sec(sid))); dif += [x for x in a[:-1] if x not in (FREE,END)]; sid=a[-1]
    fat=[]
    for s in dif[:numfat]: fat += list(struct.unpack('<%dI'%(ss//4),sec(s)))
    def chain(start, table=fat):
        out=[]; seen=set(); s=start
        while s not in (FREE,END) and s<len(table) and s not in seen:
            seen.add(s); out.append(s); s=table[s]
        return out
    d=b''.join(sec(s) for s in chain(firstdir)); entries=[]; root=None
    for off in range(0,len(d),128):
        e=d[off:off+128]
        if len(e)<128: break
        nlen=struct.unpack_from('<H',e,64)[0]; name=e[:max(0,nlen-2)].decode('utf-16le',errors='replace') if nlen>=2 else ''
        typ=e[66]; start=struct.unpack_from('<I',e,116)[0]; size=struct.unpack_from('<Q',e,120)[0]
        ent=(name,typ,start,size); entries.append(ent)
        if typ==5: root=ent
    # mini streams are not needed for Workbook in SISPEA but supported for completeness
    minifat=[]
    if nummf and firstmf not in (FREE,END):
        mf=b''.join(sec(s) for s in chain(firstmf)); minifat=list(struct.unpack('<%dI'%(len(mf)//4),mf[:len(mf)//4*4]))
    rootstream=b''
    if root: rootstream=b''.join(sec(s) for s in chain(root[2]))[:root[3]]
    def extract(ent):
        name,typ,start,size=ent
        if typ==2 and size<cutoff:
            out=[]; s=start; seen=set()
            while s not in (FREE,END) and s<len(minifat) and s not in seen:
                seen.add(s); out.append(rootstream[s*ms:(s+1)*ms]); s=minifat[s]
            return b''.join(out)[:size]
        return b''.join(sec(s) for s in chain(start))[:size]
    for ent in entries:
        if ent[0].lower() in ('workbook','book') and ent[1]==2: return extract(ent)
    raise ValueError("Flux Workbook introuvable")

def biff_records(stream: bytes):
    p=0
    while p+4<=len(stream):
        rt,ln=struct.unpack_from('<HH',stream,p); yield p,rt,stream[p+4:p+4+ln]; p+=4+ln

def boundsheets(stream: bytes):
    out=[]
    for p,rt,b in biff_records(stream):
        if rt==0x0085:
            off=struct.unpack_from('<I',b,0)[0]; cch=b[6]; uni=b[7]&1; raw=b[8:8+cch*(2 if uni else 1)]
            out.append((raw.decode('utf-16le' if uni else 'latin1',errors='replace'),off))
    return out

class SegReader:
    def __init__(self,segs,off=0): self.segs=segs; self.i=0; self.o=off
    def advance(self): self.i+=1; self.o=0
    def raw(self,n):
        out=bytearray()
        while n:
            if self.i>=len(self.segs): raise EOFError
            rem=len(self.segs[self.i])-self.o
            if rem<=0: self.advance(); continue
            k=min(n,rem); out.extend(self.segs[self.i][self.o:self.o+k]); self.o+=k; n-=k
        return bytes(out)
    def u8(self): return self.raw(1)[0]
    def u16(self): return struct.unpack('<H',self.raw(2))[0]
    def u32(self): return struct.unpack('<I',self.raw(4))[0]
    def endseg(self): return self.o>=len(self.segs[self.i])

def parse_sst(stream: bytes):
    rec=list(biff_records(stream)); idx=next((i for i,x in enumerate(rec) if x[1]==0x00FC),None)
    if idx is None: return []
    segs=[rec[idx][2]]; j=idx+1
    while j<len(rec) and rec[j][1]==0x003C: segs.append(rec[j][2]); j+=1
    unique=struct.unpack_from('<I',segs[0],4)[0]; rd=SegReader(segs,8); out=[]
    for _ in range(unique):
        cch=rd.u16(); flags=rd.u8(); high=bool(flags&1); rich=bool(flags&8); ext=bool(flags&4)
        cr=rd.u16() if rich else 0; cb=rd.u32() if ext else 0; chars=[]
        for _c in range(cch):
            if rd.endseg(): rd.advance(); high=bool(rd.u8()&1)
            width=2 if high else 1
            if len(rd.segs[rd.i])-rd.o < width: rd.advance(); high=bool(rd.u8()&1); width=2 if high else 1
            chars.append(rd.raw(width).decode('utf-16le' if high else 'latin1',errors='replace'))
        if cr: rd.raw(cr*4)
        if cb: rd.raw(cb)
        out.append(''.join(chars))
    return out

def decode_rk(b: bytes):
    rk=struct.unpack('<I',b)[0]; mult=bool(rk&1); isint=bool(rk&2)
    if isint: val=struct.unpack('<i',struct.pack('<I',rk&0xFFFFFFFC))[0]>>2
    else: val=struct.unpack('<d',struct.pack('<Q',(rk&0xFFFFFFFC)<<32))[0]
    return val/100 if mult else val

def parse_sheet(stream: bytes, offset: int, sst: list[str]) -> list[list[Any]]:
    cells={}; p=offset; formula_cell=None
    while p+4<=len(stream):
        rt,ln=struct.unpack_from('<HH',stream,p); b=stream[p+4:p+4+ln]; p+=4+ln
        if rt==0x000A: break
        if rt==0x0203 and len(b)>=14:
            r,c,_=struct.unpack_from('<HHH',b,0); cells[(r,c)]=struct.unpack_from('<d',b,6)[0]
        elif rt==0x027E and len(b)>=10:
            r,c,_=struct.unpack_from('<HHH',b,0); cells[(r,c)]=decode_rk(b[6:10])
        elif rt==0x00BD and len(b)>=6:
            r,c0=struct.unpack_from('<HH',b,0); c1=struct.unpack_from('<H',b,len(b)-2)[0]; o=4
            for c in range(c0,c1+1): cells[(r,c)]=decode_rk(b[o+2:o+6]); o+=6
        elif rt==0x00FD and len(b)>=10:
            r,c,_=struct.unpack_from('<HHH',b,0); si=struct.unpack_from('<I',b,6)[0]; cells[(r,c)]=sst[si] if si<len(sst) else ''
        elif rt==0x0205 and len(b)>=8:
            r,c,_=struct.unpack_from('<HHH',b,0); cells[(r,c)]=bool(b[6]) if not b[7] else f"#ERR{b[6]}"
        elif rt==0x0006 and len(b)>=20:
            r,c,_=struct.unpack_from('<HHH',b,0); res=b[6:14]
            if res[6:8]==b'\xff\xff': cells[(r,c)]=''; formula_cell=(r,c)
            else: cells[(r,c)]=struct.unpack('<d',res)[0]; formula_cell=None
        elif rt==0x0207 and formula_cell:
            cch=struct.unpack_from('<H',b,0)[0]; high=b[2]&1; cells[formula_cell]=b[3:3+cch*(2 if high else 1)].decode('utf-16le' if high else 'latin1',errors='replace'); formula_cell=None
    if not cells: return []
    mr=max(r for r,c in cells); mc=max(c for r,c in cells)
    return [[cells.get((r,c),'') for c in range(mc+1)] for r in range(mr+1)]

def read_xls(path: Path) -> dict[str,list[list[Any]]]:
    st=cfb_workbook_stream(path); sst=parse_sst(st); return {n:parse_sheet(st,o,sst) for n,o in boundsheets(st)}

def read_workbook(path: Path):
    if path.suffix.lower()=='.ods': return read_ods(path)
    if path.suffix.lower()=='.xls': return read_xls(path)
    raise ValueError(f"Format non pris en charge: {path.suffix}. Préférer ODS ou XLS BIFF8.")

# ---------- extraction SISPEA ----------
def rows_as_dicts(sheets, name):
    mat=sheets.get(name,[])
    if not mat: return []
    hdr=[str(x).strip() for x in mat[0]]
    return [dict(zip(hdr,row+['']*(len(hdr)-len(row)))) for row in mat[1:] if any(v not in ('',None) for v in row)]

def metadata(sheets, path: Path):
    mat=sheets.get('Metadonnees',[]); out={'source_file':path.name,'source_sha256':sha256(path)}
    for row in mat:
        vals=[x for x in row if x not in ('',None)]
        if len(vals)>=2:
            k=str(vals[0]).strip(); v=vals[1]
            if k=='Date du jeu de données' and isinstance(v,(int,float)): v=excel_serial_date(v)
            out[k]=v
    return out

def code_columns(rows):
    if not rows: return []
    return [h for h in rows[0].keys() if CODE_RE.match(str(h).strip())]

def build_dimension(comp, rows, meta):
    out=[]
    for r in rows:
        coll=r.get('Nom collectivité',''); sid=r.get("Id SISPEA de l'entité de gestion",'')
        out.append({
          'annee_reference':int(float(meta.get("Année de l'exercice",2022))), 'competence':comp,
          'service_id':str(sid), 'nom_service':r.get("Nom de l'entité de gestion",''), 'collectivite':coll,
          'epci_normalise':norm_collectivity(coll), 'statut':r.get('Statut',''), 'mode_gestion':r.get('Mode de gestion',''),
          'operateur':r.get("Nom de l'opérateur",''), 'source_file':meta['source_file'], 'date_snapshot':meta.get('Date du jeu de données',''),
          'source_sha256':meta['source_sha256']})
    return out

def long_facts(comp, rows, meta):
    out=[]; codes=code_columns(rows)
    for r in rows:
        sid=str(r.get("Id SISPEA de l'entité de gestion",'')); coll=r.get('Nom collectivité','')
        for code in codes:
            v=r.get(code,'')
            if v in ('',None): continue
            n=as_float(v)
            out.append({'annee_reference':int(float(meta.get("Année de l'exercice",2022))), 'competence':comp, 'service_id':sid,
             'epci_normalise':norm_collectivity(coll),'code':code,'valeur_num':n if n is not None else '',
             'valeur_texte':'' if n is not None else str(v),'source_file':meta['source_file'],'date_snapshot':meta.get('Date du jeu de données','')})
    return out

def consolidated(comp, sheets, meta):
    rows=rows_as_dicts(sheets,'Données consolidées'); out=[]
    for r in rows:
        code=str(r.get('Code indicateur ou variable','')).strip()
        if not code: continue
        out.append({'annee_reference':int(float(r.get('Année') or meta.get("Année de l'exercice",2022))), 'competence':comp,
         'code':code,'libelle':r.get('Libellé indicateur ou variable',''),'unite':r.get('Unité',''),
         'min':r.get('Min',''),'max':r.get('Max',''),'valeur_consolidee':r.get('Valeur consolidée',''),
         'nombre_donnees_utilisees':r.get('Nombre de données utilisées',''),'source_file':meta['source_file'],'date_snapshot':meta.get('Date du jeu de données','')})
    return out

def cindex(rows): return {r['code']:r for r in rows}

def entity_sum(rows, code):
    vals=[as_float(r.get(code)) for r in rows]; vals=[v for v in vals if v is not None]
    return (sum(vals),len(vals),len(rows)) if vals else (None,0,len(rows))

def service_value(rows, epci, code, name_contains=None):
    for r in rows:
        if norm_collectivity(r.get('Nom collectivité'))!=epci: continue
        if name_contains and name_contains.upper() not in str(r.get("Nom de l'entité de gestion",'')).upper(): continue
        v=as_float(r.get(code));
        if v is not None: return v
    return None

def collection_value(rows, epci, code):
    for r in rows:
        if norm_collectivity(r.get('Nom collectivité'))==epci:
            v=as_float(r.get(code));
            if v is not None: return v
    return None

def compare(ref, cur):
    if cur is None: return None,None,'NON_CALCULE'
    d=cur-ref; rel=(d/ref*100) if ref else None
    if abs(d)<1e-9: s='OK'
    elif rel is not None and abs(rel)<=1: s='ECART_FAIBLE'
    else: s='ECART_IMPORTANT'
    return d,rel,s

def validation(parsed):
    E=parsed['EP']; A=parsed['AC']; N=parsed['ANC']
    ec=cindex(E['consolidated']); ac=cindex(A['consolidated']); nc=cindex(N['consolidated'])
    epr=E['entities']; epcoll=E['collectivities']; acr=A['entities']; ancr=N['entities']
    tests=[]
    def add(id,comp,label,scope,page,unit,ref,cur,code,policy,source_reco,note=''):
        d,rel,status=compare(ref,cur); tests.append({'ode_id':id,'competence':comp,'indicateur':label,'territoire':scope,'page_rapport':page,'unite':unit,
          'valeur_rapport':ref,'valeur_sispea_snapshot':cur if cur is not None else '', 'ecart_absolu':d if d is not None else '',
          'ecart_relatif_pct':rel if rel is not None else '', 'statut':status,'code_sispea':code,'politique_source':policy,'source_recommandee':source_reco,'commentaire':note})
    # EP agrégats
    add('EP_005','EP','Nombre d’abonnés AEP','Martinique','11','abonnés',190066, as_float(ec.get('VP.056',{}).get('valeur_consolidee')),'VP.056','SISPEA_PRIMARY','SISPEA','Correspondance exacte du snapshot actuel.')
    add('EP_006','EP','Volume facturé AEP','Martinique','11','m³/an',21041846,None,'—','EXTERNAL_PRIMARY','RAD/RPQS','Aucun VP.068 dans l’extraction AEP 2022. VP.063 est un volume comptabilisé domestique et n’est pas équivalent.')
    add('EP_007','EP','Volume produit','Martinique','12','m³/an',41539655,as_float(ec.get('VP.059',{}).get('valeur_consolidee')),'VP.059','SISPEA_DIAGNOSTIC','RAD/RPQS / ODE','La définition SISPEA est disponible mais le snapshot actuel ne reproduit pas le rapport.')
    add('RES_014','EP','Volume prélevé AEP','Martinique','8,12','m³/an',44771108,as_float(ec.get('VP.062',{}).get('valeur_consolidee')),'VP.062','EXTERNAL_PRIMARY','BNPE','Le rapport s’appuie sur la synthèse des prélèvements ; BNPE doit rester la source de référence.')
    add('EP_017','EP','Linéaire réseau AEP','Martinique','13','km',3867,as_float(ec.get('VP.077',{}).get('valeur_consolidee')),'VP.077','SISPEA_PRIMARY','SISPEA','Écart de 1 km compatible avec une révision/arrondi.')
    add('TAR_001','EP','Prix moyen EP base 120 m³','Martinique','31','€/m³',2.83,as_float(ec.get('D102.0',{}).get('valeur_consolidee')),'D102.0','SISPEA_DIAGNOSTIC','SISPEA tarifs + méthode ODE','La valeur consolidée SISPEA est utile mais la méthode éditoriale du rapport doit être versionnée.')
    # EP qualité - collection pour CAP Nord, entité pour autres (mêmes périmètres)
    for id,code,label,vals in [
      ('EP_003','P101.1','Conformité microbiologique',{'CAESM':100.0,'CACEM':99.4,'CAP_NORD':98.6}),
      ('EP_004','P102.1','Conformité physico-chimique',{'CAESM':100.0,'CACEM':99.4,'CAP_NORD':100.0})]:
        for epci,ref in vals.items(): add(id, 'EP',label,epci,'11','%',ref,collection_value(epcoll,epci,code),code,'EXTERNAL_PRIMARY','ARS Martinique','Le rapport cite explicitement l’ARS ; SISPEA est un contrôle secondaire.')
    # EP performance - périmètres du rapport
    for id,code,label,refs in [
      ('EP_019','P104.3','Rendement hydraulique',{'CAESM':81.8,'CACEM':64.5,'CAP_NORD':52.4}),
      ('EP_020','P106.3','Indice linéaire de pertes',{'CAESM':6.54,'CACEM':21.0,'CAP_NORD':10.2}),
      ('EP_021','P107.2','Taux moyen de renouvellement',{'CAESM':0.18,'CACEM':0.19,'CAP_NORD':0.28})]:
        for epci,ref in refs.items():
            name_contains='EAU POTABLE CAP NORD' if epci=='CAP_NORD' else None
            add(id,'EP',label,epci,'14' if code!='P107.2' else '15','%' if code!='P106.3' else 'm³/km/j',ref,service_value(epr,epci,code,name_contains),code,'SISPEA_PRIMARY','SISPEA','Pour CAP Nord le rapport utilise le service principal hors Robert/Trinité.')
    # AC
    for id,label,page,unit,ref,code,policy,reco,note in [
      ('AC_001','Linéaire réseau AC','18','km',901,'VP.077','SISPEA_PRIMARY','SISPEA',''),
      ('AC_012','Boues évacuées','23','tMS/an',1622,'VP.208','SISPEA_PRIMARY','SISPEA','Très faible écart ; conserver la valeur non arrondie.'),
      ('AC_014','Nombre d’abonnés AC','24','abonnés',80832,'VP.056','SISPEA_PRIMARY','SISPEA','Le snapshot 2026 contient une légère révision du millésime 2022.'),
      ('AC_015','Volume facturé AC','24','m³/an',9940643,'VP.068','SISPEA_DIAGNOSTIC','RAD/RPQS','Écart significatif avec le snapshot SISPEA actuel.')]:
        add(id,'AC',label,'Martinique',page,unit,ref,as_float(ac.get(code,{}).get('valeur_consolidee')),code,policy,reco,note)
    # AC réseau et boues par EPCI
    for epci,ref in {'CAESM':304,'CACEM':345,'CAP_NORD':252}.items(): add('AC_001','AC','Linéaire réseau AC',epci,'18','km',ref,collection_value(A['collectivities'],epci,'VP.077'),'VP.077','SISPEA_PRIMARY','SISPEA')
    for epci,ref in {'CAESM':322,'CACEM':1017,'CAP_NORD':282}.items(): add('AC_012','AC','Boues évacuées',epci,'23','tMS/an',ref,collection_value(A['collectivities'],epci,'VP.208'),'VP.208','SISPEA_PRIMARY','SISPEA')
    # ANC
    add('ANC_002','ANC','Population ANC','Martinique','26','habitants',205898,as_float(nc.get('D301.0',{}).get('valeur_consolidee')),'D301.0','SISPEA_DIAGNOSTIC','SISPEA + contrôle ODE/SPANC','Le snapshot courant est inférieur au rapport 2022.')
    v,n,total=entity_sum(ancr,'DC.306'); add('ANC_003','ANC','Dispositifs ANC estimés','Martinique','26,28','installations',73000,v,'DC.306','SISPEA_INCOMPLETE','ODE/SPANC','Le champ est renseigné dans 3 services mais CACEM vaut seulement 601 : contrôle local indispensable.')
    c1,n1,_=entity_sum(ancr,'DC.332'); c2,n2,_=entity_sum(ancr,'DC.333'); cur=(c1 or 0)+(c2 or 0) if c1 is not None or c2 is not None else None
    add('ANC_010','ANC','Contrôles sur le neuf','Martinique','29','contrôles',1007,cur,'DC.332 + DC.333','SISPEA_PRIMARY','SISPEA','Somme conception + vérification d’exécution : à confirmer comme convention éditoriale, mais le résultat est très proche du rapport.')
    v,n,total=entity_sum(ancr,'VP.334'); add('ANC_011','ANC','Contrôles sur l’existant','Martinique','29','contrôles',591,v,'VP.334','SISPEA_INCOMPLETE','SPANC / SISPEA après complétude','CACEM est non renseignée dans le snapshot actuel, d’où une sous-estimation.')
    # P301.3 n'est pas dans le rapport 2022 mais suivi pour la base future
    p=nc.get('P301.3',{}); tests.append({'ode_id':'ANC_013','competence':'ANC','indicateur':'Taux de conformité ANC','territoire':'Martinique','page_rapport':'—','unite':'%',
      'valeur_rapport':'','valeur_sispea_snapshot':p.get('valeur_consolidee',''),'ecart_absolu':'','ecart_relatif_pct':'','statut':'COUVERTURE_PARTIELLE' if as_float(p.get('nombre_donnees_utilisees')) and as_float(p.get('nombre_donnees_utilisees'))<3 else 'OK',
      'code_sispea':'P301.3','politique_source':'SISPEA_WITH_COMPLETENESS','source_recommandee':'SISPEA + contrôle SPANC',
      'commentaire':f"Valeur consolidée calculée sur {p.get('nombre_donnees_utilisees','')} service(s) sur 3 ; ne pas présenter comme taux Martinique complet sans signalement."})
    return tests

def quality(parsed, validation_rows):
    q=[]
    for comp,p in parsed.items():
        q.append({'competence':comp,'type':'SNAPSHOT','severity':'INFO','message':f"Snapshot {p['meta'].get('Date du jeu de données','')} ; année de référence {p['meta'].get("Année de l'exercice",'')}", 'source_file':p['meta']['source_file']})
    # ANC missing fields
    anc=parsed['ANC']['entities']
    for code in ['VP.166','VP.267','VP.334']:
        missing=[norm_collectivity(r.get('Nom collectivité')) for r in anc if r.get(code) in ('',None)]
        if missing: q.append({'competence':'ANC','type':'MISSING_SERVICE_VALUE','severity':'WARNING','message':f"{code} non renseigné pour: {', '.join(missing)}",'source_file':parsed['ANC']['meta']['source_file']})
    for r in validation_rows:
        if r['statut']=='ECART_IMPORTANT': q.append({'competence':r['competence'],'type':'REPORT_DIFFERENCE','severity':'WARNING','message':f"{r['indicateur']} ({r['territoire']}): rapport={r['valeur_rapport']} ; snapshot={r['valeur_sispea_snapshot']}", 'source_file':''})
    return q

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--year',type=int,required=True); ap.add_argument('--ep',required=True); ap.add_argument('--ac',required=True); ap.add_argument('--anc',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    paths={'EP':Path(a.ep),'AC':Path(a.ac),'ANC':Path(a.anc)}; parsed={}
    for comp,path in paths.items():
        sheets=read_workbook(path); meta=metadata(sheets,path); ents=rows_as_dicts(sheets,'Entités de gestion'); colls=rows_as_dicts(sheets,'Collectivités'); cons=consolidated(comp,sheets,meta)
        parsed[comp]={'sheets':sheets,'meta':meta,'entities':ents,'collectivities':colls,'consolidated':cons}
    dims=[]; facts=[]; consall=[]
    for comp,p in parsed.items(): dims+=build_dimension(comp,p['entities'],p['meta']); facts+=long_facts(comp,p['entities'],p['meta']); consall+=p['consolidated']
    val=validation(parsed); q=quality(parsed,val)
    write_csv(out/f'dim_service_{a.year}.csv',dims); write_csv(out/f'fact_sispea_service_{a.year}.csv',facts); write_csv(out/f'fact_sispea_consolidee_{a.year}.csv',consall); write_csv(out/f'validation_rapport_{a.year}.csv',val); write_csv(out/f'data_quality_issues_{a.year}.csv',q)
    # wide service tables for human review
    for comp,p in parsed.items(): write_csv(out/f'services_{comp}_{a.year}.csv',p['entities'])
    summary={'generated_at':datetime.now(timezone.utc).isoformat(),'year_reference':a.year,
      'sources':{c:p['meta'] for c,p in parsed.items()},
      'counts':{c:{'entities':len(p['entities']),'collectivities':len(p['collectivities']),'consolidated_rows':len(p['consolidated'])} for c,p in parsed.items()},
      'validation_status_counts':{s:sum(1 for r in val if r['statut']==s) for s in sorted({r['statut'] for r in val})}}
    (out/f'summary_{a.year}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
