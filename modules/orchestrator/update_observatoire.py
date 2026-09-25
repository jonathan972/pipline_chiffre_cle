#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,hashlib,uuid,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

FIELDS=["annee_reference","indicator_id","domain","territoire","perimeter_id","value","unit","source_primary",
"source_detail","source_file","source_page","coverage_status","quality_status","record_role",
"population_millesime","definition","note"]

def read_scsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f,delimiter=";"))
def write_scsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=";");w.writeheader();w.writerows(rows)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1048576),b""):h.update(c)
    return h.hexdigest()
def normal(r,year):
    x={k:r.get(k,"") for k in FIELDS};x["annee_reference"]=str(year);return x
def pri(r):return {"PRODUCTION":3,"VALIDATION":2,"DIAGNOSTIC":1,"AUDIT":0}.get(r.get("record_role",""),0)
def dedupe(rows):
    best={}
    for r in rows:
        key=(r["annee_reference"],r["indicator_id"],r["territoire"],r["perimeter_id"])
        if key not in best or pri(r)>pri(best[key]):best[key]=r
        elif pri(r)==pri(best[key]) and (r.get("value")!=best[key].get("value") or r.get("source_primary")!=best[key].get("source_primary")):
            best[key]["note"]=(best[key].get("note","")+" | DUPLICATE_SOURCE_CANDIDATE="+r.get("source_primary","")).strip(" |")
    return list(best.values())

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--year",type=int,required=True);ap.add_argument("--root",default="../..")
    ap.add_argument("--out",required=True);ap.add_argument("--refresh-ars",action="store_true");ap.add_argument("--ars-fixture")
    ap.add_argument("--strict",action="store_true");a=ap.parse_args()
    root=Path(a.root).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    start=datetime.now(timezone.utc);events=[];rows=[]
    candidates=[root/"modules/master/outputs_v3"/f"fact_indicateur_master_{a.year}.csv",
                root/"modules/master/outputs_v2"/f"fact_indicateur_master_{a.year}.csv",
                root/"modules/master/outputs"/f"fact_indicateur_master_{a.year}.csv"]
    base=next((p for p in candidates if p.exists()),None)
    if base:
        rr=read_scsv(base);rows += [normal(r,a.year) for r in rr];events.append({"module":"master_base","status":"OK","file":str(base),"rows":len(rr)})
    elif a.strict:raise SystemExit("Master de base absent")
    else:events.append({"module":"master_base","status":"MISSING"})
    arsout=root/"modules/ars_quality/outputs"/str(a.year);arsfile=arsout/f"fact_ars_quality_{a.year}.csv"
    if a.refresh_ars or a.ars_fixture:
        cmd=[sys.executable,str(root/"modules/ars_quality/ars_quality_etl.py"),"--year",str(a.year),"--out",str(arsout)]
        if a.ars_fixture:cmd += ["--fixture",a.ars_fixture]
        subprocess.run(cmd,check=True)
    if arsfile.exists():
        rr=read_scsv(arsfile)
        for r in rr:
            x=normal(r,a.year);x["source_file"]=arsfile.name;rows.append(x)
        events.append({"module":"ars_quality","status":"OK","file":str(arsfile),"rows":len(rr)})
    else:events.append({"module":"ars_quality","status":"NOT_RUN"})
    final=dedupe(rows);final.sort(key=lambda r:(r["domain"],r["indicator_id"],r["territoire"],r["perimeter_id"]))
    write_scsv(out/f"fact_indicateur_master_{a.year}.csv",final,FIELDS)
    q=[]
    for r in final:
        c=r["coverage_status"];s=r["quality_status"];role=r["record_role"];sev="INFO"
        if c in {"MISSING","NO_DATA"} or any(t in s for t in ("ERROR","INVALID","INCOMPLETE")):sev="ERROR"
        elif role=="PRODUCTION" and (c not in {"COMPLETE","FULL",""} or s not in {"OK","SOURCE_REVISION_MINOR",""}):sev="WARNING"
        if sev!="INFO":q.append({"severity":sev,"indicator_id":r["indicator_id"],"territoire":r["territoire"],"perimeter_id":r["perimeter_id"],"coverage_status":c,"quality_status":s,"record_role":role,"message":r["note"]})
    qfields=["severity","indicator_id","territoire","perimeter_id","coverage_status","quality_status","record_role","message"]
    write_scsv(out/f"quality_report_{a.year}.csv",q,qfields)
    sources=[]
    for module,p in [("master_base",base),("ars_quality",arsfile if arsfile.exists() else None)]:
        if p:sources.append({"module":module,"path":str(p),"sha256":sha(p)})
    man={"run_id":str(uuid.uuid4()),"year":a.year,"started_at":start.isoformat(),"finished_at":datetime.now(timezone.utc).isoformat(),
         "status":"OK","events":events,"sources":sources,"rows_final":len(final),
         "production_rows":sum(r["record_role"]=="PRODUCTION" for r in final),
         "diagnostic_rows":sum(r["record_role"]=="DIAGNOSTIC" for r in final),
         "audit_rows":sum(r["record_role"]=="AUDIT" for r in final),"quality_alerts":len(q)}
    (out/"run_manifest.json").write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(man,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
