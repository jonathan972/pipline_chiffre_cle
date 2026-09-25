#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

def load_epci_map():
    """Load the authoritative commune -> EPCI bridge maintained by the perimeter module."""
    p=Path(__file__).resolve().parents[1]/"perimeters"/"epci_communes.csv"
    out={}
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f,delimiter=";"):
            out[str(r.get("commune_insee") or "").strip()]=str(r.get("epci_code") or "").strip()
    return out

EPCI_BY_COMMUNE = load_epci_map()

def http_json(endpoint, params, timeout=180, retries=3):
    url=f"{BASE}/{endpoint}?{urlencode(params,doseq=True)}"
    req=Request(url,headers={"User-Agent":"ODE-Martinique-Referentiel/1.0"})
    last_error=None
    for attempt in range(1,retries+1):
        try:
            with urlopen(req,timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            last_error=exc
            if attempt>=retries: raise
            time.sleep(min(30,2**attempt))
    raise last_error

def fetch_all(endpoint, params, size=1000):
    page=1; rows=[]
    while True:
        p=dict(params); p.update({"page":page,"size":size})
        payload=http_json(endpoint,p)
        rows.extend(payload.get("data",[]))
        if not payload.get("next"): break
        page += 1; time.sleep(0.05)
    return rows

def norm_conf(v):
    if v is None:return None
    s=str(v).strip().upper()
    if s in {"C","O","OUI","TRUE","1"}:return "C"
    if s in {"N","NON","FALSE","0"}:return "N"
    return None

def dedupe_samples(rows):
    samples={}
    for r in rows:
        pid=str(r.get("code_prelevement") or r.get("referenceprel") or "").strip()
        if not pid: continue
        s=samples.setdefault(pid,{"code_prelevement":pid,"code_commune":str(r.get("code_commune") or "").strip(),
            "code_reseau":str(r.get("code_reseau") or r.get("cdreseau") or "").strip(),
            "date_prelevement":r.get("date_prelevement") or r.get("dateprel"),"bact":None,"pc":None})
        if not s["code_commune"] and r.get("code_commune"): s["code_commune"]=str(r.get("code_commune"))
        b=norm_conf(r.get("conformite_limites_bact_prelevement"))
        p=norm_conf(r.get("conformite_limites_pc_prelevement"))
        if b is not None:s["bact"]=b
        if p is not None:s["pc"]=p
    return list(samples.values())

def rate(samples, field):
    vals=[s[field] for s in samples if s.get(field) in {"C","N"}]
    if not vals:return None,0,0
    ok=sum(v=="C" for v in vals)
    return 100.0*ok/len(vals),ok,len(vals)

def aggregate(samples, year):
    groups={"Martinique":samples}
    for e in ("CACEM","CAESM","CAP_NORD"):
        groups[e]=[s for s in samples if EPCI_BY_COMMUNE.get(s.get("code_commune"))==e]
    out=[]
    for territory,ss in groups.items():
        for iid,field,label in [
            ("QUAL_MICROBIO_CONFORMITE","bact","Conformité aux limites microbiologiques"),
            ("QUAL_PC_CONFORMITE","pc","Conformité aux limites physico-chimiques")]:
            pct,ok,total=rate(ss,field)
            out.append({"annee_reference":year,"indicator_id":iid,"domain":"QUALITE_EAU_POTABLE",
                "territoire":territory,"perimeter_id":territory,"value":"" if pct is None else round(pct,4),
                "unit":"%","numerator":ok,"denominator":total,"source_primary":"ARS_SISE_EAUX",
                "source_detail":"Hub'Eau qualite_eau_potable/resultats_dis",
                "coverage_status":"COMPLETE" if total else "NO_DATA","quality_status":"TO_VALIDATE_AGAINST_RPQS",
                "record_role":"DIAGNOSTIC","definition":label+" ; prélèvements uniques avec statut disponible.",
                "note":"Comparer aux P101.1/P102.1 et aux chiffres ARS/RPQS avant passage en PRODUCTION."})
    return out

def write_scsv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0].keys()) if rows else []
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=";");w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--year",type=int,required=True);ap.add_argument("--out",required=True);ap.add_argument("--fixture")
    ap.add_argument("--from-samples",help="Réagrège un fichier fact_ars_samples_YYYY.csv existant (hors ligne).")
    a=ap.parse_args();out=Path(a.out)
    if a.from_samples:
        with open(a.from_samples,encoding="utf-8-sig",newline="") as f:
            samples=list(csv.DictReader(f,delimiter=";"))
        facts=aggregate(samples,a.year);out.mkdir(parents=True,exist_ok=True)
        write_scsv(out/f"fact_ars_quality_{a.year}.csv",facts)
        summary={"year":a.year,"source":f"réagrégation de {Path(a.from_samples).name}","unique_samples":len(samples),"facts":len(facts),
                 "epci_mapping":"modules/perimeters/epci_communes.csv"}
        (out/f"summary_ars_{a.year}.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(summary,ensure_ascii=False));return
    if a.fixture:
        payload=json.loads(Path(a.fixture).read_text(encoding="utf-8"))
        rows=payload["data"] if isinstance(payload,dict) and "data" in payload else payload; source="fixture"
    else:
        rows=fetch_all("resultats_dis",{"code_departement":"972","date_min_prelevement":f"{a.year}-01-01","date_max_prelevement":f"{a.year}-12-31"})
        source=f"{BASE}/resultats_dis";out.mkdir(parents=True,exist_ok=True)
        (out/f"raw_hubeau_ars_{a.year}.json").write_text(json.dumps(rows,ensure_ascii=False),encoding="utf-8")
    samples=dedupe_samples(rows);facts=aggregate(samples,a.year)
    write_scsv(out/f"fact_ars_quality_{a.year}.csv",facts);write_scsv(out/f"fact_ars_samples_{a.year}.csv",samples)
    summary={"year":a.year,"source":source,"raw_rows":len(rows),"unique_samples":len(samples),"facts":len(facts)}
    (out/f"summary_ars_{a.year}.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
