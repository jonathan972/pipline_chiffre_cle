#!/usr/bin/env python3
"""ETL BNPE pour le Référentiel Eau & Assainissement ODE Martinique.

Le module travaille sur les exports standards du site BNPE :
- prelevements.csv
- synthese_usage.csv
- synthese_type_eau.csv
- synthese_evolution_temporelle.csv
- synthese_geographique.csv

Aucune valeur du rapport ODE n'est utilisée pour corriger les données source.
Le rapport 2022 sert uniquement de jeu de validation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=","))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def as_int_if_whole(v: float | None) -> int | float | None:
    if v is None:
        return None
    return int(v) if float(v).is_integer() else v


def map_headers(row: dict[str, str]) -> dict[str, str]:
    return {norm(k): v for k, v in row.items()}


def getv(row: dict[str, str], *aliases: str) -> str:
    nr = map_headers(row)
    for a in aliases:
        k = norm(a)
        if k in nr:
            return nr[k]
    return ""


def sum_volume(rows: Iterable[dict[str, str]]) -> float:
    return sum(to_float(getv(r, "Volume (m3)", "Volume total (m3)")) or 0 for r in rows)


def compare_status(report: float | None, pipeline: float | None, *, is_percentage: bool, cfg: dict[str, Any]) -> tuple[str, float | None, float | None]:
    if pipeline is None or report is None:
        return "NON_CALCULE", None, None
    diff = pipeline - report
    rel = None if report == 0 else diff / report * 100
    if is_percentage:
        tol = float(cfg["validation"]["published_percentage_tolerance_points"])
        if abs(diff) <= tol:
            return ("OK" if abs(diff) < 1e-12 else "ECART_FAIBLE"), diff, rel
    tol_rel = float(cfg["validation"]["relative_tolerance_pct"])
    if abs(diff) < 1e-12:
        return "OK", diff, rel
    if rel is not None and abs(rel) <= tol_rel:
        return "ECART_FAIBLE", diff, rel
    return "ECART_IMPORTANT", diff, rel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--reference", required=False, default=None)
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(args.config, encoding="utf-8"))
    ref = json.load(open(args.reference, encoding="utf-8")) if args.reference else {"year": None, "metrics": []}
    year = str(args.year)

    paths = {
        "prelevements": input_dir / "prelevements.csv",
        "usage": input_dir / "synthese_usage.csv",
        "type_eau": input_dir / "synthese_type_eau.csv",
        "evolution": input_dir / "synthese_evolution_temporelle.csv",
        "geo": input_dir / "synthese_geographique.csv",
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Fichiers BNPE absents : " + ", ".join(missing))

    pre = read_csv(paths["prelevements"])
    usage = read_csv(paths["usage"])
    typ = read_csv(paths["type_eau"])
    evo = read_csv(paths["evolution"])
    geo = read_csv(paths["geo"])

    pre_y = [r for r in pre if getv(r, "Année") == year]
    usage_y = [r for r in usage if getv(r, "Année") == year]
    type_y = [r for r in typ if getv(r, "Année") == year]
    evo_y = [r for r in evo if getv(r, "Année") == year]
    geo_y = [r for r in geo if getv(r, "Année") == year]

    quality: list[dict[str, Any]] = []
    if not pre_y:
        quality.append({"year_reference": year, "severity": "ERROR", "issue_type": "YEAR_MISSING", "message": "Aucune ligne de prélèvement pour l'année demandée."})

    # Disponibilité déclarée dans la synthèse temporelle.
    evo_volume = to_float(getv(evo_y[0], "Volume (m3)")) if evo_y else None
    evo_comment = getv(evo_y[0], "Commentaire") if evo_y else ""
    if evo_volume is None:
        quality.append({"year_reference": year, "severity": "WARNING", "issue_type": "YEAR_UNAVAILABLE", "message": evo_comment or "Donnée BNPE indisponible."})

    fact_rows: list[dict[str, Any]] = []
    for r in pre_y:
        fact_rows.append({
            "annee_reference": int(year),
            "code_ouvrage": getv(r, "Code Sandre de l'ouvrage"),
            "nom_ouvrage": getv(r, "Nom de l'ouvrage"),
            "departement": getv(r, "Département"),
            "code_insee": getv(r, "Code INSEE"),
            "commune": getv(r, "Commune"),
            "volume_m3": as_int_if_whole(to_float(getv(r, "Volume (m3)"))),
            "code_usage_bnpe": getv(r, "Code usage BNPE"),
            "libelle_usage_bnpe": getv(r, "Libellé usage BNPE"),
            "code_usage_declare": getv(r, "Code de l'usage déclaré"),
            "usage_declare": getv(r, "Usage déclaré"),
            "type_eau": getv(r, "Type d'eau"),
            "longitude": to_float(getv(r, "Longitude")),
            "latitude": to_float(getv(r, "Latitude")),
            "precision_localisation": getv(r, "Précision de la localisation"),
            "mode_obtention_volume": getv(r, "Mode d'obtention du volume"),
            "statut_volume": getv(r, "Libellé du statut du volume d'eau"),
            "qualification_volume": getv(r, "Libellé de qualification du volume d'eau"),
            "code_bss": getv(r, "Code BSS"),
            "code_zone_hydro": getv(r, "Code de la zone hydrographique"),
            "nom_zone_hydro": getv(r, "Nom de la zone hydrographique"),
            "code_entite_hydro_cours_eau": getv(r, "Code entité hydrographique cours d'eau"),
            "code_entite_hydro_plan_eau": getv(r, "Code entité hydrographique plan d'eau"),
            "code_bdlisa": getv(r, "Code BDLISA"),
            "libelle_bdlisa": getv(r, "Libellé entité hydrologique BDLISA"),
            "date_debut_exploitation": getv(r, "Date début exploitation ouvrage de prélèvement"),
            "date_fin_exploitation": getv(r, "Date de fin d'exploitation d'un ouvrage de prélèvement"),
            "source_file": paths["prelevements"].name,
        })

    # Dimension ouvrage : un enregistrement canonique par code, à partir de toutes les années disponibles.
    dim_by_code: dict[str, dict[str, Any]] = {}
    for r in pre:
        code = getv(r, "Code Sandre de l'ouvrage")
        if not code:
            continue
        candidate = {
            "code_ouvrage": code,
            "nom_ouvrage": getv(r, "Nom de l'ouvrage"),
            "code_alternatif": getv(r, "Code alternatif de l'ouvrage"),
            "origine_code_alternatif": getv(r, "Origine du code alternatif"),
            "departement": getv(r, "Département"),
            "code_insee": getv(r, "Code INSEE"),
            "commune": getv(r, "Commune"),
            "lieu_dit": getv(r, "Lieu dit", "Lieu-dit"),
            "type_eau": getv(r, "Type d'eau"),
            "longitude": to_float(getv(r, "Longitude")),
            "latitude": to_float(getv(r, "Latitude")),
            "precision_localisation": getv(r, "Précision de la localisation"),
            "code_bss": getv(r, "Code BSS"),
            "code_zone_hydro": getv(r, "Code de la zone hydrographique"),
            "nom_zone_hydro": getv(r, "Nom de la zone hydrographique"),
            "code_entite_hydro_cours_eau": getv(r, "Code entité hydrographique cours d'eau"),
            "code_bdlisa": getv(r, "Code BDLISA"),
            "libelle_bdlisa": getv(r, "Libellé entité hydrologique BDLISA"),
            "date_debut_exploitation": getv(r, "Date début exploitation ouvrage de prélèvement"),
            "date_fin_exploitation": getv(r, "Date de fin d'exploitation d'un ouvrage de prélèvement"),
        }
        # Préférer l'occurrence la plus récente si le code existe plusieurs années.
        dim_by_code[code] = candidate
    dim_rows = sorted(dim_by_code.values(), key=lambda r: (r["commune"], r["nom_ouvrage"], r["code_ouvrage"]))

    # Tests d'unicité à la granularité année × ouvrage × usage.
    key_counts = Counter((r["annee_reference"], r["code_ouvrage"], r["code_usage_bnpe"]) for r in fact_rows)
    for key, count in key_counts.items():
        if count > 1:
            quality.append({"year_reference": year, "severity": "ERROR", "issue_type": "DUPLICATE_FACT_KEY", "message": f"Clé dupliquée {key}: {count} lignes."})

    # Synthèses recalculées depuis le détail.
    total = sum(float(r["volume_m3"] or 0) for r in fact_rows)
    by_usage: dict[str, float] = defaultdict(float)
    by_type: dict[str, float] = defaultdict(float)
    by_usage_type: dict[tuple[str, str], float] = defaultdict(float)
    by_commune: dict[str, float] = defaultdict(float)
    for r in fact_rows:
        v = float(r["volume_m3"] or 0)
        by_usage[r["code_usage_bnpe"]] += v
        by_type[r["type_eau"]] += v
        by_usage_type[(r["code_usage_bnpe"], r["type_eau"])] += v
        by_commune[r["commune"]] += v

    usage_rows = []
    for code, v in sorted(by_usage.items()):
        usage_rows.append({"annee_reference": int(year), "code_usage_bnpe": code, "volume_m3": as_int_if_whole(v), "proportion_pct": (v / total * 100 if total else None)})
    type_rows = []
    for code, v in sorted(by_type.items()):
        type_rows.append({"annee_reference": int(year), "type_eau": code, "volume_m3": as_int_if_whole(v), "proportion_pct": (v / total * 100 if total else None)})

    # Contrôles croisés avec les fichiers de synthèse BNPE.
    checks = [
        ("TOTAL_PRELEVEMENTS_VS_EVOLUTION", total, evo_volume),
        ("TOTAL_PRELEVEMENTS_VS_USAGE", total, sum(to_float(getv(r, "Volume total (m3)", "Volume (m3)")) or 0 for r in usage_y)),
        ("TOTAL_PRELEVEMENTS_VS_TYPE_EAU", total, sum(to_float(getv(r, "Volume total (m3)", "Volume (m3)")) or 0 for r in type_y)),
        ("TOTAL_PRELEVEMENTS_VS_GEO", total, sum(to_float(getv(r, "Volume (m3)")) or 0 for r in geo_y)),
    ]
    for label, a, b in checks:
        if b is None:
            continue
        if abs(a - b) > 0.5:
            quality.append({"year_reference": year, "severity": "ERROR", "issue_type": "SUMMARY_MISMATCH", "message": f"{label}: détail={a}, synthèse={b}."})

    aep = by_usage.get(cfg["aep_usage_code"], 0.0)
    irr = by_usage.get(cfg["irrigation_usage_code"], 0.0)
    ind = by_usage.get(cfg["industry_usage_code"], 0.0)
    aep_surface = by_usage_type.get((cfg["aep_usage_code"], cfg["surface_water_code"]), 0.0)
    aep_ground = by_usage_type.get((cfg["aep_usage_code"], cfg["groundwater_code"]), 0.0)

    lezarde_codes = set(cfg["lezarde_system"]["ouvrage_codes"])
    lezarde_volume = sum(float(r["volume_m3"] or 0) for r in fact_rows if r["code_usage_bnpe"] == cfg["aep_usage_code"] and r["code_ouvrage"] in lezarde_codes)

    aep_rows = [r for r in fact_rows if r["code_usage_bnpe"] == cfg["aep_usage_code"]]
    aep_works = {r["code_ouvrage"] for r in aep_rows}
    aep_surface_works = {r["code_ouvrage"] for r in aep_rows if r["type_eau"] == cfg["surface_water_code"]}
    aep_ground_works = {r["code_ouvrage"] for r in aep_rows if r["type_eau"] == cfg["groundwater_code"]}

    metrics = {
        "RES_015": total,
        "RES_014": aep,
        "RES_016": irr,
        "RES_017": ind,
        "RES_001": (aep / total * 100 if total else None),
        "RES_002": (irr / total * 100 if total else None),
        "RES_003": (ind / total * 100 if total else None),
        "RES_004": (aep_surface / aep * 100 if aep else None),
        "RES_005": (aep_ground / aep * 100 if aep else None),
        "RES_006": (lezarde_volume / aep * 100 if aep else None),
        "RES_007": len(aep_works),
        "RES_008": len(aep_surface_works),
        "RES_009": len(aep_ground_works),
    }

    mart = []
    reference_active = int(ref.get("year")) == int(year) if ref.get("year") is not None else False
    refs = {m["id"]: m for m in ref.get("metrics", [])} if reference_active else {}
    for mid, value in metrics.items():
        rr = refs.get(mid, {})
        mart.append({
            "annee_reference": int(year),
            "indicator_id": mid,
            "label": rr.get("label", mid),
            "value": as_int_if_whole(value),
            "unit": rr.get("unit", ""),
            "source": "BNPE",
            "calculation": {
                "RES_015": "Somme détail prelevements.csv",
                "RES_014": "Somme Code usage BNPE=AEP",
                "RES_016": "Somme Code usage BNPE=IRR",
                "RES_017": "Somme Code usage BNPE=IND",
                "RES_001": "AEP / total ×100",
                "RES_002": "IRR / total ×100",
                "RES_003": "IND / total ×100",
                "RES_004": "AEP CONT / AEP ×100",
                "RES_005": "AEP SOUT / AEP ×100",
                "RES_006": "AEP ouvrages Lézarde + Blanche / AEP ×100",
                "RES_007": "Nombre d'ouvrages AEP présents dans BNPE",
                "RES_008": "Nombre d'ouvrages AEP CONT présents dans BNPE",
                "RES_009": "Nombre d'ouvrages AEP SOUT présents dans BNPE",
            }.get(mid, ""),
        })

    validation = []
    for rr in (ref.get("metrics", []) if reference_active else []):
        val = metrics.get(rr["id"])
        status, diff, rel = compare_status(float(rr["report_value"]), float(val) if val is not None else None, is_percentage=(rr["unit"] == "%"), cfg=cfg)
        source_policy = "BNPE_PRIMARY"
        recommended = "BNPE"
        comment = ""
        if rr["id"] in {"RES_007", "RES_008", "RES_009"}:
            source_policy = "INVENTORY_EXTERNAL_PRIMARY"
            recommended = "SISPEA / ODE / ARS"
            comment = "La BNPE n'est pas un inventaire exhaustif des ouvrages ; utiliser le référentiel patrimonial pour les comptages."
        elif rr["id"] in {"RES_015", "RES_016", "RES_017"} and status != "OK":
            comment = "Le snapshot BNPE actuel diffère du rapport historique ; conserver les deux versions avec date de snapshot."
        elif rr["id"] in {"RES_004", "RES_005"}:
            comment = "Part calculée uniquement sur les prélèvements AEP du détail BNPE, et non sur la synthèse tous usages."
        elif rr["id"] == "RES_006":
            comment = "Le système Lézarde + Rivière Blanche est défini par une liste versionnée de codes ouvrages dans config.json."
        validation.append({
            "reference_id": rr["id"],
            "label": rr["label"],
            "page_rapport": rr["page"],
            "unite": rr["unit"],
            "valeur_rapport": rr["report_value"],
            "valeur_pipeline": as_int_if_whole(val),
            "ecart_absolu": diff,
            "ecart_relatif_pct": rel,
            "statut": status,
            "politique_source": source_policy,
            "source_recommandee": recommended,
            "commentaire": comment,
        })

    # Notes qualité structurantes.
    if reference_active and "RES_007" in refs and len(aep_works) < int(refs["RES_007"]["report_value"]):
        quality.append({"year_reference": year, "severity": "WARNING", "issue_type": "AEP_INVENTORY_INCOMPLETE", "message": f"BNPE contient {len(aep_works)} ouvrages AEP, contre {refs['RES_007']['report_value']} captages dans le rapport ODE. Ne pas utiliser BNPE seule pour l'inventaire."})
    if any(str(r.get("precision_localisation")) in {"5", "6"} for r in aep_rows):
        quality.append({"year_reference": year, "severity": "INFO", "issue_type": "AEP_COORDINATES_APPROXIMATE", "message": "Les coordonnées des ouvrages AEP ont une précision 5/6 : elles ne doivent pas être traitées comme localisation exacte."})

    write_csv(out / f"fact_prelevement_{year}.csv", fact_rows)
    write_csv(out / "dim_ouvrage.csv", dim_rows)
    write_csv(out / f"fact_bnpe_usage_{year}.csv", usage_rows)
    write_csv(out / f"fact_bnpe_type_eau_{year}.csv", type_rows)
    write_csv(out / f"mart_bnpe_indicateurs_{year}.csv", mart)
    write_csv(out / f"validation_rapport_{year}.csv", validation)
    write_csv(out / f"data_quality_issues_{year}.csv", quality, ["year_reference","severity","issue_type","message"])

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "year_reference": int(year),
        "source_files": {k: {"file": p.name, "sha256": sha256(p)} for k, p in paths.items()},
        "availability": {"volume_m3": evo_volume, "comment": evo_comment},
        "metrics": {k: as_int_if_whole(v) for k, v in metrics.items()},
        "counts": {
            "rows_prelevements": len(fact_rows),
            "unique_ouvrages": len({r["code_ouvrage"] for r in fact_rows}),
            "aep_rows": len(aep_rows),
            "aep_unique_ouvrages": len(aep_works),
            "aep_surface_ouvrages": len(aep_surface_works),
            "aep_groundwater_ouvrages": len(aep_ground_works),
            "zero_volume_rows": sum(1 for r in fact_rows if float(r["volume_m3"] or 0) == 0),
        },
        "quality_issue_count": len(quality),
    }
    with (out / f"summary_{year}.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
