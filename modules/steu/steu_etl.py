#!/usr/bin/env python3
"""ETL STEU — Observatoire de l'Eau Martinique (prototype v1).

Entrée : export CSV du portail national de l'assainissement collectif.
Sorties :
  - raw_normalized_steu_<year>.csv (111 champs normalisés + année)
  - dim_steu.csv
  - fact_steu_<year>.csv
  - fact_agglo_<year>.csv
  - data_quality_issues_<year>.csv
  - validation_rapport_<year>.csv (si fichier de référence fourni)
  - summary_<year>.json

Principes :
  * aucune correction silencieuse ;
  * année de référence déduite des en-têtes dynamiques ou passée via --year ;
  * conservation séparée de la conformité agglomération et de la conformité STEU ;
  * reconstitution d'une conformité station = collecte agglo + équipement STEU + performance STEU ;
  * seuil > 200 EH paramétrable ;
  * valeurs du rapport ODE externalisées dans un JSON de référence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_CONFIG = {
    "public_nature_values": ["Urbain"],
    "private_nature_values": ["Privé"],
    "positive_capacity_required_for_public_inventory": True,
    "large_station_threshold_eh": 200,
    "epci_rules": [
        {"contains": "ESPACE SUD", "epci": "CAESM"},
        {"contains": "PAYS NORD", "epci": "CAP Nord"},
        {"contains": "CENTRE DE LA MARTINIQUE", "epci": "CACEM"},
        {"contains": "ODYSSI", "epci": "CACEM"},
    ],
    "status_yes": ["oui", "yes", "true", "1"],
    "status_no": ["non", "no", "false", "0"],
    "missing_tokens": ["", "n/a", "na", "null", "none"],
}


def clean_header(value: str) -> str:
    return value.replace("\ufeff", "").replace("\t", "").strip().strip('"').strip()


def slugify(value: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", value)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("œ", "oe")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def parse_float(value: Any, missing_tokens: Iterable[str]) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip().replace("\u00a0", " ").replace(",", ".")
    if s.lower() in set(missing_tokens):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(value: Any, missing_tokens: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    """Retourne (ISO date ou None, anomalie ou None)."""
    if value is None:
        return None, None
    s = str(value).strip()
    if s.lower() in set(missing_tokens):
        return None, None
    if s.startswith("0000-00-00"):
        return None, "ZERO_DATE"
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat(), None
        except ValueError:
            pass
    return None, "INVALID_DATE"


def norm_bool(value: Any, config: Dict[str, Any]) -> Optional[bool]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in config["missing_tokens"]:
        return None
    if s in config["status_yes"]:
        return True
    if s in config["status_no"]:
        return False
    return None


def infer_year(headers: List[str]) -> Optional[int]:
    years: List[int] = []
    for h in headers:
        for match in re.findall(r"\b(20\d{2})\b", h):
            if "Etat" in h or "état" in h.lower() or "etat" in h.lower():
                years.append(int(match))
    if not years:
        return None
    return Counter(years).most_common(1)[0][0]


def read_pipe_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="|", quotechar='"')
        rows = list(reader)
    if not rows:
        raise ValueError("Fichier CSV vide")
    headers = [clean_header(h) for h in rows[0]]
    expected = len(headers)
    records: List[Dict[str, str]] = []
    for i, row in enumerate(rows[1:], start=2):
        if len(row) != expected:
            raise ValueError(f"Ligne {i}: {len(row)} colonnes au lieu de {expected}")
        records.append(dict(zip(headers, row)))
    return headers, records


def map_epci(record: Dict[str, str], config: Dict[str, Any]) -> str:
    haystack = " | ".join([
        record.get("Maître ouvrage", ""),
        record.get("Service gestionnaire de l'agglo", ""),
        record.get("Nom de l'agglomération", ""),
    ]).upper()
    for rule in config.get("epci_rules", []):
        if rule["contains"].upper() in haystack:
            return rule["epci"]
    return "Non déterminé"


def status_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def station_global_reconstructed(record: Dict[str, str], config: Dict[str, Any]) -> Optional[bool]:
    fields = [
        "Conformité collecte agglo temps sec",
        "Conformité ERU équipement STEU",
        "Conformité globale ERU performances",
    ]
    vals = [norm_bool(record.get(f), config) for f in fields]
    if any(v is None for v in vals):
        return None
    return all(vals)


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in fieldnames})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_issue(year: int, code: str, severity: str, issue_type: str, field: str, observed: Any, message: str, source: str) -> Dict[str, Any]:
    return {
        "year_reference": year,
        "code_steu": code,
        "severity": severity,
        "issue_type": issue_type,
        "field_name": field,
        "observed_value": observed,
        "message": message,
        "source_file": source,
    }


def build_outputs(headers: List[str], records: List[Dict[str, str]], year: int, config: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    missing = config["missing_tokens"]
    threshold = float(config["large_station_threshold_eh"])
    issues: List[Dict[str, Any]] = []

    # Contrôles structurels
    codes = [r.get("Code du STEU", "").strip() for r in records]
    for code, count in Counter(codes).items():
        if code and count > 1:
            issues.append(make_issue(year, code, "ERROR", "DUPLICATE_STEU_CODE", "Code du STEU", code, f"Code STEU présent {count} fois.", source_file))

    raw_rows: List[Dict[str, Any]] = []
    dim_rows: List[Dict[str, Any]] = []
    fact_rows: List[Dict[str, Any]] = []

    raw_field_map = {h: slugify(h) for h in headers}

    for r in records:
        code = r.get("Code du STEU", "").strip()
        cap = parse_float(r.get("Capacité nominale en EH"), missing)
        cap_dbo = parse_float(r.get("Capacité nominale en Kg de DBO5"), missing)
        p95 = parse_float(r.get("Percentile95 calculé en m3/j"), missing)
        charge = parse_float(r.get("Charge maximale entrante (EH)"), missing)
        debit = parse_float(r.get("Débit entrant en m3/j"), missing)
        boues = parse_float(r.get("Prod boues sans réactif (tMS/an)"), missing)
        lat = parse_float(r.get("Latitude du STEU (WGS84)"), missing)
        lon = parse_float(r.get("Longitude du STEU (WGS84)"), missing)
        d_service, err_service = parse_date(r.get("Date de mise en service du STEU"), missing)
        d_hors, err_hors = parse_date(r.get("Date de mise hors serv du STEU"), missing)
        d_modif, err_modif = parse_date(r.get("Date dernière modification STEU"), missing)
        d_agglo, err_agglo = parse_date(r.get("Date de mise à jour agglo"), missing)

        for field, raw, err in [
            ("Date de mise en service du STEU", r.get("Date de mise en service du STEU"), err_service),
            ("Date de mise hors serv du STEU", r.get("Date de mise hors serv du STEU"), err_hors),
            ("Date dernière modification STEU", r.get("Date dernière modification STEU"), err_modif),
            ("Date de mise à jour agglo", r.get("Date de mise à jour agglo"), err_agglo),
        ]:
            if err:
                issues.append(make_issue(year, code, "WARN", err, field, raw, "Date non exploitable, conservée uniquement dans le RAW.", source_file))

        if r.get("Nature du STEU") in config["public_nature_values"] and (cap is None or cap <= 0):
            issues.append(make_issue(year, code, "WARN", "PUBLIC_CAPACITY_MISSING_OR_ZERO", "Capacité nominale en EH", r.get("Capacité nominale en EH"), "STEU de nature publique/urbaine sans capacité nominale positive.", source_file))

        # RAW normalisé : toutes les colonnes + year_reference.
        raw = {"year_reference": year, "source_file": source_file}
        for h in headers:
            raw[raw_field_map[h]] = r.get(h, "")
        raw_rows.append(raw)

        epci = map_epci(r, config)
        dim_rows.append({
            "code_steu": code,
            "nom_steu": r.get("Nom du STEU", "").strip(),
            "nature_steu": r.get("Nature du STEU", "").strip(),
            "code_sandre_nature_steu": r.get("Code SANDRE nature STEU", "").strip(),
            "commune_implantation": r.get("Commune implantation", "").strip(),
            "code_insee_commune": r.get("Code INSEE commune implantation", "").strip(),
            "maitre_ouvrage": r.get("Maître ouvrage", "").strip(),
            "exploitant": r.get("Exploitant", "").strip(),
            "epci_normalise": epci,
            "latitude_wgs84": lat,
            "longitude_wgs84": lon,
            "date_mise_service": d_service,
            "date_mise_hors_service": d_hors,
            "source_file": source_file,
            "first_seen_year": year,
            "last_seen_year": year,
        })

        fact_rows.append({
            "year_reference": year,
            "code_steu": code,
            "code_agglo": r.get("Code SANDRE de l'agglomération", "").strip(),
            "nom_agglo": r.get("Nom de l'agglomération", "").strip(),
            "nature_steu": r.get("Nature du STEU", "").strip(),
            "epci_normalise": epci,
            "etat_steu": r.get(f"Etat du STEU en {year}", r.get("Etat du STEU en 2022", "")).strip(),
            "capacite_nominale_eh": cap,
            "capacite_nominale_kg_dbo5": cap_dbo,
            "percentile95_m3_j": p95,
            "charge_max_entree_eh": charge,
            "debit_entrant_m3_j": debit,
            "filiere_eau_principale": r.get("Filière eau principale", "").strip(),
            "filiere_boues_principale": r.get("Filière boues principale", "").strip(),
            "conformite_equipement_agglo": status_text(r.get("Conformité equipement agglo")),
            "conformite_performance_agglo": status_text(r.get("Conformité perf agglo")),
            "conformite_collecte_agglo": status_text(r.get("Conformité collecte agglo temps sec")),
            "conformite_globale_agglo": status_text(r.get("Conformité agglo globale")),
            "conformite_equipement_steu": status_text(r.get("Conformité ERU équipement STEU")),
            "conformite_performance_steu": status_text(r.get("Conformité globale ERU performances")),
            "conformite_station_reconstituee": station_global_reconstructed(r, config),
            "cause_non_conformite": r.get("Cause de non conformité", "").strip(),
            "production_boues_tms": boues,
            "code_systeme_collecte": r.get("Code SANDRE du système de collecte", "").strip(),
            "nom_systeme_collecte": r.get("Nom du système de collecte", "").strip(),
            "code_masse_eau": r.get("Code de masse eau", "").strip(),
            "nom_masse_eau": r.get("Nom de la masse eau", "").strip(),
            "nom_milieu_rejet": r.get("Nom du milieu de rejet", "").strip(),
            "type_milieu_rejet": r.get("Type du milieu du rejet", "").strip(),
            "latitude_rejet_wgs84": parse_float(r.get("Latitude du rejet (WGS84)"), missing),
            "longitude_rejet_wgs84": parse_float(r.get("Longitude du rejet (WGS84)"), missing),
            "date_derniere_modification_source": d_modif,
            "date_mise_a_jour_agglo": d_agglo,
            "source_file": source_file,
        })

    # Une ligne par agglomération : les champs agglo sont répétés pour chaque STEU.
    agglo_by_code: Dict[str, Dict[str, Any]] = {}
    for r in records:
        code = r.get("Code SANDRE de l'agglomération", "").strip()
        if not code:
            continue
        candidate = {
            "year_reference": year,
            "code_agglo": code,
            "nom_agglo": r.get("Nom de l'agglomération", "").strip(),
            "commune_principale": r.get("Nom de la commune principale", "").strip(),
            "code_insee_commune_principale": r.get("Code INSEE commune principale", "").strip(),
            "etat_agglo": r.get(f"Etat de agglomération en {year}", r.get("Etat de agglomération en 2022", "")).strip(),
            "taille_agglo_eh": parse_float(r.get("Taille agglomération (EH)"), missing),
            "tranche_obligation": r.get("Tranche obligation", "").strip(),
            "maximum_pollutions_entrantes_eh": parse_float(r.get("Maximum de la somme des pollutions entrantes (EH)"), missing),
            "somme_capacites_nominales_eh": parse_float(r.get("Somme des capacités nominales (EH)"), missing),
            "conformite_equipement_agglo": status_text(r.get("Conformité equipement agglo")),
            "conformite_performance_agglo": status_text(r.get("Conformité perf agglo")),
            "conformite_collecte_temps_sec": status_text(r.get("Conformité collecte agglo temps sec")),
            "conformite_globale_agglo": status_text(r.get("Conformité agglo globale")),
            "date_mise_a_jour_agglo": parse_date(r.get("Date de mise à jour agglo"), missing)[0],
            "type_reseau_majoritaire": r.get("Type de réseau majoritaire", "").strip(),
            "source_file": source_file,
        }
        if code in agglo_by_code:
            # Vérifier que les colonnes agrégées sont identiques sur les lignes répétées.
            old = agglo_by_code[code]
            for k in candidate:
                if k in {"source_file", "year_reference"}:
                    continue
                if old.get(k) != candidate.get(k):
                    issues.append(make_issue(year, r.get("Code du STEU", ""), "WARN", "AGGLO_REPEATED_VALUE_CONFLICT", k, candidate.get(k), f"Valeur différente pour l'agglomération {code}; première valeur conservée.", source_file))
                    break
        else:
            agglo_by_code[code] = candidate

    # Métriques synthétiques.
    public_vals = set(config["public_nature_values"])
    public_rows = [x for x in fact_rows if x["nature_steu"] in public_vals]
    if config.get("positive_capacity_required_for_public_inventory", True):
        public_inventory = [x for x in public_rows if (x["capacite_nominale_eh"] or 0) > 0]
    else:
        public_inventory = public_rows[:]
    public_gt = [x for x in public_inventory if (x["capacite_nominale_eh"] or 0) > threshold]
    public_ge = [x for x in public_inventory if (x["capacite_nominale_eh"] or 0) >= threshold]

    def count_epci(rows: List[Dict[str, Any]], epci: str) -> int:
        return sum(1 for x in rows if x["epci_normalise"] == epci)

    def sum_epci(rows: List[Dict[str, Any]], epci: str, field: str) -> float:
        return sum((x.get(field) or 0) for x in rows if x["epci_normalise"] == epci)

    def pct_true(rows: List[Dict[str, Any]], field: str, epci: Optional[str] = None) -> Optional[float]:
        rr = rows if epci is None else [x for x in rows if x["epci_normalise"] == epci]
        valid = [x.get(field) for x in rr if x.get(field) is not None]
        if not rr or not valid:
            return None
        # Pour la conformité reconstituée, les valeurs manquantes restent hors numérateur mais
        # le dénominateur correspond au parc retenu, afin de rendre visible la non-complétude.
        return 100.0 * sum(v is True for v in valid) / len(rr)

    def pct_text_yes(rows: List[Dict[str, Any]], field: str, epci: Optional[str] = None) -> Optional[float]:
        rr = rows if epci is None else [x for x in rows if x["epci_normalise"] == epci]
        if not rr:
            return None
        return 100.0 * sum(norm_bool(x.get(field), config) is True for x in rr) / len(rr)

    metrics: Dict[str, Any] = {
        "rows_total": len(fact_rows),
        "public_rows_nature_urbain": len(public_rows),
        "private_rows_nature_prive": sum(1 for x in fact_rows if x["nature_steu"] in set(config["private_nature_values"])),
        "public_stations_positive_capacity": len(public_inventory),
        "public_stations_gt_200": len(public_gt),
        "public_stations_ge_200": len(public_ge),
        "public_capacity_all_positive_eh": round(sum(x["capacite_nominale_eh"] or 0 for x in public_inventory), 3),
        "public_capacity_gt_200_eh": round(sum(x["capacite_nominale_eh"] or 0 for x in public_gt), 3),
        "public_capacity_ge_200_eh": round(sum(x["capacite_nominale_eh"] or 0 for x in public_ge), 3),
        "public_boues_tms_all": round(sum(x["production_boues_tms"] or 0 for x in public_inventory), 3),
        "public_stations_gt_200_caesm": count_epci(public_gt, "CAESM"),
        "public_stations_gt_200_cacem": count_epci(public_gt, "CACEM"),
        "public_stations_gt_200_cap_nord": count_epci(public_gt, "CAP Nord"),
        "public_boues_tms_caesm": round(sum_epci(public_inventory, "CAESM", "production_boues_tms"), 3),
        "public_boues_tms_cacem": round(sum_epci(public_inventory, "CACEM", "production_boues_tms"), 3),
        "public_boues_tms_cap_nord": round(sum_epci(public_inventory, "CAP Nord", "production_boues_tms"), 3),
        "public_gt200_station_global_reconstructed_pct": pct_true(public_gt, "conformite_station_reconstituee"),
        "public_gt200_station_global_reconstructed_pct_caesm": pct_true(public_gt, "conformite_station_reconstituee", "CAESM"),
        "public_gt200_station_global_reconstructed_pct_cacem": pct_true(public_gt, "conformite_station_reconstituee", "CACEM"),
        "public_gt200_station_global_reconstructed_pct_cap_nord": pct_true(public_gt, "conformite_station_reconstituee", "CAP Nord"),
        "public_gt200_agglo_global_yes_pct": pct_text_yes(public_gt, "conformite_globale_agglo"),
        "public_gt200_agglo_global_yes_pct_caesm": pct_text_yes(public_gt, "conformite_globale_agglo", "CAESM"),
        "public_gt200_agglo_global_yes_pct_cacem": pct_text_yes(public_gt, "conformite_globale_agglo", "CACEM"),
        "public_gt200_agglo_global_yes_pct_cap_nord": pct_text_yes(public_gt, "conformite_globale_agglo", "CAP Nord"),
        "quality_issue_count": len(issues),
        "year_reference": year,
        "large_station_threshold_eh": threshold,
    }

    # Max date de modification disponible.
    dates = [x["date_derniere_modification_source"] for x in fact_rows if x["date_derniere_modification_source"]]
    metrics["latest_source_modification_date"] = max(dates) if dates else None

    return {
        "raw_field_map": raw_field_map,
        "raw_rows": raw_rows,
        "dim_rows": dim_rows,
        "fact_rows": fact_rows,
        "agglo_rows": list(agglo_by_code.values()),
        "issues": issues,
        "metrics": metrics,
    }


def validate(metrics: Dict[str, Any], reference_path: Optional[Path]) -> List[Dict[str, Any]]:
    if reference_path is None:
        return []
    ref = json.loads(reference_path.read_text(encoding="utf-8"))
    output: List[Dict[str, Any]] = []
    for item in ref.get("references", []):
        key = item["pipeline_metric"]
        pipeline = metrics.get(key)
        report = item.get("value")
        if pipeline is None or report is None:
            abs_diff = None
            rel_diff = None
            status = "NON_CALCULABLE"
        else:
            abs_diff = pipeline - report
            rel_diff = (abs_diff / report * 100.0) if report not in (0, 0.0) else None
            if abs(abs_diff) < 1e-9:
                status = "OK"
            elif rel_diff is not None and abs(rel_diff) <= 1.0:
                status = "ECART_FAIBLE"
            else:
                status = "ECART_IMPORTANT"
        output.append({
            "reference_id": item.get("reference_id"),
            "pipeline_metric": key,
            "label": item.get("label"),
            "scope": item.get("scope"),
            "page_rapport": item.get("page"),
            "unite": item.get("unit"),
            "valeur_rapport": report,
            "valeur_pipeline": pipeline,
            "ecart_absolu": abs_diff,
            "ecart_relatif_pct": rel_diff,
            "statut": status,
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="ETL STEU Martinique — portail national assainissement")
    parser.add_argument("--input", required=True, type=Path, help="CSV source (séparateur |)")
    parser.add_argument("--out", required=True, type=Path, help="Répertoire de sortie")
    parser.add_argument("--year", type=int, help="Année de référence ; sinon déduite des en-têtes")
    parser.add_argument("--config", type=Path, help="Configuration JSON")
    parser.add_argument("--reference", type=Path, help="Références ODE JSON pour validation")
    args = parser.parse_args()

    config = DEFAULT_CONFIG.copy()
    if args.config:
        user_config = json.loads(args.config.read_text(encoding="utf-8"))
        config.update(user_config)
    # Normalisation des listes pour comparaison.
    config["status_yes"] = [str(x).lower() for x in config["status_yes"]]
    config["status_no"] = [str(x).lower() for x in config["status_no"]]
    config["missing_tokens"] = [str(x).lower() for x in config["missing_tokens"]]

    headers, records = read_pipe_csv(args.input)
    year = args.year or infer_year(headers)
    if year is None:
        raise SystemExit("Impossible de déduire l'année de référence ; utiliser --year YYYY")

    args.out.mkdir(parents=True, exist_ok=True)
    result = build_outputs(headers, records, year, config, args.input.name)
    validation = validate(result["metrics"], args.reference)

    # Sorties CSV.
    raw_fields = ["year_reference", "source_file"] + list(result["raw_field_map"].values())
    write_csv(args.out / f"raw_normalized_steu_{year}.csv", raw_fields, result["raw_rows"])

    dim_fields = [
        "code_steu","nom_steu","nature_steu","code_sandre_nature_steu","commune_implantation",
        "code_insee_commune","maitre_ouvrage","exploitant","epci_normalise","latitude_wgs84",
        "longitude_wgs84","date_mise_service","date_mise_hors_service","source_file","first_seen_year","last_seen_year"
    ]
    write_csv(args.out / "dim_steu.csv", dim_fields, result["dim_rows"])

    fact_fields = [
        "year_reference","code_steu","code_agglo","nom_agglo","nature_steu","epci_normalise","etat_steu",
        "capacite_nominale_eh","capacite_nominale_kg_dbo5","percentile95_m3_j","charge_max_entree_eh",
        "debit_entrant_m3_j","filiere_eau_principale","filiere_boues_principale","conformite_equipement_agglo",
        "conformite_performance_agglo","conformite_collecte_agglo","conformite_globale_agglo",
        "conformite_equipement_steu","conformite_performance_steu","conformite_station_reconstituee",
        "cause_non_conformite","production_boues_tms","code_systeme_collecte","nom_systeme_collecte",
        "code_masse_eau","nom_masse_eau","nom_milieu_rejet","type_milieu_rejet","latitude_rejet_wgs84",
        "longitude_rejet_wgs84","date_derniere_modification_source","date_mise_a_jour_agglo","source_file"
    ]
    write_csv(args.out / f"fact_steu_{year}.csv", fact_fields, result["fact_rows"])

    agg_fields = [
        "year_reference","code_agglo","nom_agglo","commune_principale","code_insee_commune_principale",
        "etat_agglo","taille_agglo_eh","tranche_obligation","maximum_pollutions_entrantes_eh",
        "somme_capacites_nominales_eh","conformite_equipement_agglo","conformite_performance_agglo",
        "conformite_collecte_temps_sec","conformite_globale_agglo","date_mise_a_jour_agglo",
        "type_reseau_majoritaire","source_file"
    ]
    write_csv(args.out / f"fact_agglo_{year}.csv", agg_fields, result["agglo_rows"])

    issue_fields = ["year_reference","code_steu","severity","issue_type","field_name","observed_value","message","source_file"]
    write_csv(args.out / f"data_quality_issues_{year}.csv", issue_fields, result["issues"])

    if validation:
        validation_fields = ["reference_id","pipeline_metric","label","scope","page_rapport","unite","valeur_rapport","valeur_pipeline","ecart_absolu","ecart_relatif_pct","statut"]
        write_csv(args.out / f"validation_rapport_{year}.csv", validation_fields, validation)

    summary = {
        "source_file": args.input.name,
        "source_sha256": sha256(args.input),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "headers_count": len(headers),
        "metrics": result["metrics"],
        "validation_status_counts": dict(Counter(x["statut"] for x in validation)),
        "raw_field_mapping": result["raw_field_map"],
    }
    (args.out / f"summary_{year}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "year": year,
        "records": len(records),
        "outputs": str(args.out),
        "metrics": result["metrics"],
        "validation": dict(Counter(x["statut"] for x in validation)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
