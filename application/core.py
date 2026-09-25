from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


def project_root() -> Path:
    """Return the portable project root.

    The packaged Windows EXE is distributed next to the project folders.  Keeping
    data outside the executable makes annual source drops auditable and editable.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ROOT = project_root()
RESOURCES = ROOT / 'resources'
SOURCE_DOCUMENTS = RESOURCES / 'source_documents'


def _log(cb: Callable[[str], None] | None, msg: str) -> None:
    if cb:
        cb(msg)


def _load_script(rel_path: str, module_name: str):
    """Load a project script directly, including when the UI is frozen."""
    import importlib.util
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_scsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_scsv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0].keys()) if rows else [])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows)


@dataclass
class SourceCheck:
    key: str
    label: str
    status: str
    detail: str
    required: bool = True


@dataclass
class BuildResult:
    year: int
    output_dir: str
    docx: str | None
    pdf: str | None
    preflight: str | None
    summary: dict


KNOWN_ABSENCES = {
    2024: {
        "CACEM_AEP": "CACEM : aucun bilan/RAD AEP 2024 produit.",
        "CACEM_AC": "CACEM : aucun bilan/RAD AC 2024 produit.",
        "CACEM_ANC": "CACEM : aucun bilan/RAD ANC 2024 produit.",
        "CAESM_ANC": "CAESM : aucun RPQS ANC 2024 produit.",
    }
}

EXPECTED_MAPS = {
    "MAP_CAPTAGES_AEP": "Carte captages AEP",
    "MAP_STEU_PUBLIQUES": "Carte STEU publiques",
    "MAP_OU_CHART_AC_COMMUNE": "Part AC par commune",
    "MAP_AC_ANC_COMMUNES": "Carte AC/ANC par commune",
}

ASSET_FILENAME = {
    "MAP_CAPTAGES_AEP": "map_captages_aep_{year}.png",
    "MAP_STEU_PUBLIQUES": "map_steu_publiques_{year}.png",
    "MAP_OU_CHART_AC_COMMUNE": "map_part_ac_communes_{year}.png",
    "MAP_AC_ANC_COMMUNES": "map_ac_anc_communes_{year}.png",
}


def year_out(year: int) -> Path:
    return ROOT / "publication" / str(year)


def source_status(year: int) -> list[SourceCheck]:
    checks: list[SourceCheck] = []
    master_path = ROOT / "outputs" / str(year) / f"fact_indicateur_master_{year}.csv"
    master = master_path if master_path.exists() else None
    checks.append(SourceCheck("master", "Référentiel maître", "OK" if master else "MANQUANT",
                              str(master) if master else
                              f"Exécuter update_observatoire.py --year {year} pour construire le master canonique."))

    ars_dir = ROOT / "modules/ars_quality/outputs" / str(year)
    ars = ars_dir / f"fact_ars_quality_{year}.csv"
    ars_samples = ars_dir / f"fact_ars_samples_{year}.csv"
    if ars.exists():
        ars_status, ars_detail = "OK", str(ars)
    elif ars_samples.exists():
        ars_status, ars_detail = "PRÊT À REAGRÉGER", f"Échantillons ARS présents : {ars_samples.name}"
    else:
        ars_status, ars_detail = "À ACTUALISER", "Cliquer sur « Actualiser ARS » pour interroger Hub'Eau."
    checks.append(SourceCheck("ars", "Qualité ARS / Hub'Eau", ars_status, ars_detail, required=False))

    portal = ROOT / "modules/assainissement_portal/outputs" / str(year) / f"fact_assainissement_portal_{year}.csv"
    inbox = ROOT / "data/source_inbox" / str(year)
    portal_raw = next(iter(sorted(inbox.glob("*assainissement*.csv"))), None) if inbox.exists() else None
    checks.append(SourceCheck("portal", "Portail assainissement (STEU publiques/privées)",
                              "OK" if portal.exists() else ("PRÊT À IMPORTER" if portal_raw else "MANQUANT"),
                              str(portal if portal.exists() else (portal_raw or "Déposer l'export CSV."))))

    local = ROOT / "modules/local_reports/outputs" / f"fact_local_reports_{year}.csv"
    raw_year = SOURCE_DOCUMENTS / str(year)
    raw_count = len(list(raw_year.glob('*.pdf'))) if raw_year.exists() else 0
    detail = str(local) if local.exists() else f"{raw_count} document(s) source disponibles ; reconstruire le module local."
    checks.append(SourceCheck("local_reports", "RAD / RPQS locaux normalisés", "OK" if local.exists() else ("PRÊT À EXTRAIRE" if raw_count else "MANQUANT"), detail))

    pop = ROOT / "modules/insee_population/outputs/fact_population_resolue_2019_2024.csv"
    checks.append(SourceCheck("population", "Population INSEE", "OK" if pop.exists() else "MANQUANT", str(pop)))

    bnpe = ROOT / "modules/bnpe" / ("outputs_2023" if year == 2023 else "outputs") / f"mart_bnpe_indicateurs_{year}.csv"
    checks.append(SourceCheck("bnpe", "Prélèvements BNPE", "OK" if bnpe.exists() else "À FOURNIR/ACTUALISER",
                              str(bnpe) if bnpe.exists() else "Export BNPE du millésime requis.", required=False))

    maps_dir = year_out(year) / "assets_manual"
    present = sum((maps_dir / fn.format(year=year)).exists() for fn in ASSET_FILENAME.values())
    checks.append(SourceCheck("maps", "Cartes SIG", "OK" if present == len(ASSET_FILENAME) else "EN ATTENTE SIG",
                              f"{present}/{len(ASSET_FILENAME)} cartes présentes.", required=False))
    return checks


def import_assainissement_portal(year: int, source: Path, log=None) -> Path:
    _log(log, f"Import portail assainissement {year}: {source.name}")
    inbox = ROOT / "data/source_inbox" / str(year)
    inbox.mkdir(parents=True, exist_ok=True)
    saved = inbox / f"export-portail_assainissement_{year}.csv"
    if source.resolve() != saved.resolve():
        shutil.copy2(source, saved)
    mod = _load_script("modules/assainissement_portal/assainissement_portal_etl.py", f"portal_{year}")
    rows = mod.read_portal(saved)
    facts, normalized, summary = mod.aggregate(rows, year, ROOT, saved.name)
    out = ROOT / "modules/assainissement_portal/outputs" / str(year)
    out.mkdir(parents=True, exist_ok=True)
    mod.write_scsv(out / f"fact_assainissement_portal_{year}.csv", facts)
    mod.write_scsv(out / f"steu_inventory_{year}.csv", normalized)
    (out / f"summary_assainissement_portal_{year}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(log, f"Portail assainissement: {len(facts)} faits normalisés.")
    return out / f"fact_assainissement_portal_{year}.csv"


def refresh_ars(year: int, log=None) -> Path:
    _log(log, f"Téléchargement du contrôle sanitaire ARS / Hub'Eau pour {year}…")
    mod = _load_script("modules/ars_quality/ars_quality_etl.py", f"ars_{year}")
    params = {"code_departement": "972", "date_min_prelevement": f"{year}-01-01", "date_max_prelevement": f"{year}-12-31"}
    rows = mod.fetch_all("resultats_dis", params)
    samples = mod.dedupe_samples(rows)
    facts = mod.aggregate(samples, year)
    out = ROOT / "modules/ars_quality/outputs" / str(year)
    out.mkdir(parents=True, exist_ok=True)
    mod.write_scsv(out / f"fact_ars_quality_{year}.csv", facts)
    mod.write_scsv(out / f"fact_ars_samples_{year}.csv", samples)
    (out / f"raw_hubeau_ars_{year}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    summary = {"year": year, "source": mod.BASE + "/resultats_dis", "raw_rows": len(rows), "unique_samples": len(samples), "facts": len(facts)}
    (out / f"summary_ars_{year}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(log, f"ARS: {len(rows)} résultats → {len(samples)} prélèvements uniques → {len(facts)} indicateurs.")
    return out / f"fact_ars_quality_{year}.csv"


def rebuild_local_reports(log=None) -> Path:
    config = ROOT / 'modules/local_reports/config.json'
    if not config.exists():
        raise FileNotFoundError(config)
    work = ROOT / 'data' / '_local_reports_work'
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    cfg=json.loads(config.read_text(encoding='utf-8'))
    missing=[]
    for src in cfg.get('sources',[]):
        name=src['file']; year=int(src['year'])
        candidates=[ROOT/'data/source_inbox'/str(year)/'documents'/name, SOURCE_DOCUMENTS/str(year)/name]
        found=next((x for x in candidates if x.exists()),None)
        if found: shutil.copy2(found,work/name)
        else: missing.append(name)
    if missing: _log(log, f"RAD/RPQS : {len(missing)} source(s) absente(s) du corpus ; extraction partielle possible.")
    out = ROOT / 'modules/local_reports/outputs'
    cmd=[sys.executable,str(ROOT/'modules/local_reports/rad_rpqs_etl.py'),'--input-dir',str(work),'--config',str(config),'--out',str(out)]
    proc=subprocess.run(cmd,capture_output=True,text=True)
    if proc.returncode!=0: raise RuntimeError(proc.stderr or proc.stdout or 'Échec extraction RAD/RPQS')
    _log(log,'RAD/RPQS : extraction locale reconstruite.')
    return out


def rebuild_ars_from_samples(year: int, log=None) -> Path | None:
    """Recompute ARS aggregates with the current commune→EPCI mapping."""
    out = ROOT / "modules/ars_quality/outputs" / str(year)
    samples_file = out / f"fact_ars_samples_{year}.csv"
    if not samples_file.exists(): return None
    mod = _load_script("modules/ars_quality/ars_quality_etl.py", f"ars_reaggregate_{year}")
    samples = read_scsv(samples_file)
    facts = mod.aggregate(samples, year)
    mod.write_scsv(out / f"fact_ars_quality_{year}.csv", facts)
    summary = {"year": year, "source": "existing fact_ars_samples", "unique_samples": len(samples), "facts": len(facts), "reaggregated_with_current_epci_mapping": True}
    (out / f"summary_ars_{year}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(log, f"ARS {year}: {len(samples)} prélèvements réagrégés avec le référentiel EPCI courant.")
    return out / f"fact_ars_quality_{year}.csv"


def prepare_existing_sources(year: int, log=None) -> None:
    ars_dir = ROOT / "modules/ars_quality/outputs" / str(year)
    ars_fact = ars_dir / f"fact_ars_quality_{year}.csv"
    ars_samples = ars_dir / f"fact_ars_samples_{year}.csv"
    if ars_samples.exists() and not ars_fact.exists(): rebuild_ars_from_samples(year, log=log)
    inbox = ROOT / "data/source_inbox" / str(year)
    if inbox.exists():
        portal = next(iter(sorted(inbox.glob("*assainissement*.csv"))), None)
        out = ROOT / "modules/assainissement_portal/outputs" / str(year) / f"fact_assainissement_portal_{year}.csv"
        if portal and not out.exists(): import_assainissement_portal(year, portal, log=log)
    local = ROOT / 'modules/local_reports/outputs' / f'fact_local_reports_{year}.csv'
    if not local.exists() and (SOURCE_DOCUMENTS/str(year)).exists(): rebuild_local_reports(log=log)


def prepare_all_sources(year: int, refresh_ars_online: bool = False, log=None) -> list[SourceCheck]:
    prepare_existing_sources(year, log=log)
    if refresh_ars_online:
        try: refresh_ars(year, log=log)
        except Exception as exc: _log(log, f"ARS indisponible temporairement : {exc}")
    return source_status(year)


def copy_manual_documents(year: int, files: Iterable[Path], log=None) -> list[Path]:
    dest = ROOT / "data/source_inbox" / str(year) / "documents"
    dest.mkdir(parents=True, exist_ok=True)
    copied=[]
    for src in files:
        dst=dest/src.name; shutil.copy2(src,dst); copied.append(dst); _log(log,f"Document ajouté: {src.name}")
    return copied


def import_manual_overrides(year: int, source: Path, log=None) -> Path:
    rows=read_scsv(source)
    required={'indicator_id','territoire','value'}
    fields=set(rows[0].keys()) if rows else set()
    if not required <= fields: raise ValueError(f"CSV valeurs complémentaires : colonnes requises {sorted(required)}")
    dest=ROOT/'data/manual_overrides'/f'{year}.csv'; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
    _log(log,f"Valeurs complémentaires importées : {len(rows)} ligne(s).")
    return dest


def export_missing_values_template(year: int) -> Path:
    pf=year_out(year)/f'preflight_report_{year}.csv'
    if not pf.exists(): build_report(year,final=False)
    rows=[r for r in read_scsv(pf) if r.get('status') in ('MISSING_VALUE','OPTIONAL_MISSING')]
    out=year_out(year)/f'gabarit_valeurs_complementaires_{year}.csv'
    fields=['indicator_id','territoire','perimeter_id','value','unit','source','definition','note','validated']
    seen=set(); result=[]
    for r in rows:
        key=(r.get('indicator_id',''),r.get('territory',''))
        if not key[0] or key in seen: continue
        seen.add(key)
        result.append({'indicator_id':key[0],'territoire':key[1],'perimeter_id':'','value':'','unit':'','source':'','definition':'','note':f"Placeholder {r.get('token','')} page {r.get('page','')}",'validated':'non'})
    write_scsv(out,result,fields)
    return out


def add_map(year: int, token: str, source: Path, log=None) -> Path:
    if token not in ASSET_FILENAME: raise KeyError(token)
    dest_dir=year_out(year)/"assets_manual"; dest_dir.mkdir(parents=True,exist_ok=True)
    dst=dest_dir/ASSET_FILENAME[token].format(year=year); shutil.copy2(source,dst)
    _log(log,f"Carte ajoutée: {EXPECTED_MAPS[token]} → {dst.name}")
    return dst


def _try_pdf(docx_path: Path, outdir: Path, log=None) -> Path | None:
    for exe in ["soffice","libreoffice"]:
        try: proc=subprocess.run([exe,"--headless","--convert-to","pdf","--outdir",str(outdir),str(docx_path)],capture_output=True,text=True,timeout=120)
        except (FileNotFoundError,subprocess.TimeoutExpired): continue
        pdf=outdir/(docx_path.stem+".pdf")
        if proc.returncode==0 and pdf.exists(): _log(log,f"PDF généré: {pdf.name}"); return pdf
    _log(log,"PDF non généré automatiquement (LibreOffice non détecté). Le DOCX reste disponible.")
    return None


def build_report(year: int, final: bool = False, log=None) -> BuildResult:
    prepare_existing_sources(year, log=log)
    out=year_out(year); out.mkdir(parents=True,exist_ok=True)
    reporting=_load_script("modules/reporting/report_builder.py",f"reporting_{year}")
    mode="final" if final else "draft"; _log(log,f"Génération du rapport {year} ({mode})…")
    docx,summary=reporting.build_docx(ROOT,year,out,mode=mode)
    if final and summary.get("blocking_count"): raise RuntimeError(f"Rapport final bloqué: {summary['blocking_count']} élément(s) requis non résolu(s). Consultez le préflight.")
    pdf=_try_pdf(Path(docx),out,log=log)
    run={"generated_at":datetime.now(timezone.utc).isoformat(),"year":year,"mode":mode,"summary":summary,"sources":[asdict(x) for x in source_status(year)],"docx":str(docx),"pdf":str(pdf) if pdf else None}
    (out/f"application_run_{year}.json").write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding="utf-8")
    _log(log,f"Rapport terminé: {Path(docx).name}")
    return BuildResult(year,str(out),str(docx),str(pdf) if pdf else None,str(out/f"preflight_report_{year}.csv"),summary)


def open_path(path: Path) -> None:
    path=Path(path)
    if sys.platform.startswith("win"): os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform=="darwin": subprocess.Popen(["open",str(path)])
    else: subprocess.Popen(["xdg-open",str(path)])
