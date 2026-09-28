#!/usr/bin/env python3
"""Extraction et consolidation des tarifs SISPEA pour la Martinique.

Les classeurs nationaux ne sont pas versionnes. La commande ``extract`` en
extrait les seules lignes du departement 972 dans des snapshots CSV legers.
La commande ``build`` regenere ensuite les faits canoniques a partir de ces
snapshots. D102.0 et D204.0 sont ponderes par les populations desservies
D101.0 et D201.0, conformement aux fiches indicateurs SISPEA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.sispea.sispea_etl_v2 import read_xls  # noqa: E402

SOURCE_URL = "https://services.eaufrance.fr/documents/tarifsDescriptions/{name}"
FIELDS = [
    "competence", "departement", "collectivite_id", "collectivite", "service_id", "service",
    "mode_gestion", "population_service", "statut", "population_desservie", "prix_ttc_120m3",
    "VP.179", "VP.191", "VP.177", "VP.178", "VP.190", "VP.213", "VP.214", "VP.215",
    "VP.216", "VP.217", "VP.218", "VP.219", "VP.345", "VP.346",
]
FACT_FIELDS = [
    "annee_reference", "indicator_id", "territoire", "value", "unit", "record_role",
    "quality_status", "coverage_status", "source_file", "source_detail", "definition", "note",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def number(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def text(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\x92", "’")


def plain(value) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "")) if not unicodedata.combining(c)).lower()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fields} for row in rows])


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=";"))


def detail_rows(path: Path, competence: str) -> list[dict]:
    workbook = read_xls(path)
    matrix = next((rows for name, rows in workbook.items() if "tarifaire" in plain(name) and "zone" not in plain(name)), [])
    if not matrix:
        raise ValueError(f"Feuille Detail tarifaire introuvable dans {path.name}")
    header = [str(value).strip() for value in matrix[0]]
    records = [dict(zip(header, row + [""] * (len(header) - len(row)))) for row in matrix[1:]]
    price = "D102.0" if competence == "AEP" else "D204.0"
    population = "D101.0" if competence == "AEP" else "D201.0"
    out = []
    for row in records:
        if text(row.get(header[0])).zfill(3) != "972":
            continue
        result = {
            "competence": competence,
            "departement": "972",
            "collectivite_id": text(row.get(header[1])),
            "collectivite": text(row.get(header[2])),
            "service_id": text(row.get(header[4])),
            "service": text(row.get(header[5])),
            "mode_gestion": text(row.get(header[6])),
            "population_service": text(row.get(header[7])),
            "statut": text(row.get(header[8])),
            "population_desservie": text(row.get(population)),
            "prix_ttc_120m3": text(row.get(price)),
        }
        for code in FIELDS[11:]:
            result[code] = text(row.get(code))
        out.append(result)
    return out


def extract(year: int, aep: Path, ac: Path, data_dir: Path) -> None:
    manifest = {"year": year, "department": "972", "sources": []}
    for competence, path in (("AEP", aep), ("AC", ac)):
        name = f"tarifs_{competence}_Martinique_{year}.csv"
        rows = detail_rows(path, competence)
        write_csv(data_dir / name, rows, FIELDS)
        manifest["sources"].append({
            "competence": competence, "national_file": path.name,
            "url": SOURCE_URL.format(name=path.name), "sha256": sha256(path),
            "snapshot": name, "rows_972": len(rows),
        })
    (data_dir / f"manifest_{year}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def usable(rows: list[dict]) -> tuple[list[dict], bool]:
    candidates = [r for r in rows if number(r["population_desservie"]) is not None]
    valid = [r for r in candidates if number(r["prix_ttc_120m3"]) is not None]
    return valid, bool(candidates) and len(valid) == len(candidates)


def source_role(rows: list[dict], complete: bool) -> str:
    if not complete:
        return "DIAGNOSTIC"
    statuses = [plain(r["statut"]) for r in rows]
    if statuses and all("confirm" in status and "publi" in status for status in statuses):
        return "PRODUCTION"
    if statuses and all("publi" in status for status in statuses):
        return "VALIDATION"
    return "DIAGNOSTIC"


def weighted(rows: list[dict], field: str) -> float | None:
    pairs = [(number(r["population_desservie"]), number(r[field])) for r in rows]
    if not pairs or any(weight is None or value is None for weight, value in pairs):
        return None
    total = sum(weight for weight, _ in pairs)
    return sum(weight * value for weight, value in pairs) / total if total else None


def weighted_sum(rows: list[dict], fields: tuple[str, ...]) -> float | None:
    values = []
    for row in rows:
        weight = number(row["population_desservie"])
        parts = [number(row[field]) for field in fields]
        if weight is None:
            continue
        # Dans SISPEA, une part absente vaut zero lorsque le service n'a pas de
        # part delegataire/collectivite. Ces calculs restent en VALIDATION.
        values.append((weight, sum(value or 0 for value in parts)))
    total = sum(weight for weight, _ in values)
    return sum(weight * value for weight, value in values) / total if total else None


def make_fact(year: int, indicator: str, value: float, unit: str, role: str, source_file: str,
              detail: str, definition: str, quality: str = "OK", note: str = "") -> dict:
    return {
        "annee_reference": year, "indicator_id": indicator, "territoire": "Martinique",
        "value": f"{value:.6f}".rstrip("0").rstrip("."), "unit": unit, "record_role": role,
        "quality_status": quality, "coverage_status": "COMPLETE", "source_file": source_file,
        "source_detail": detail, "definition": definition, "note": note,
    }


def build(year: int, data_dir: Path, output_dir: Path) -> list[dict]:
    aep_path = data_dir / f"tarifs_AEP_Martinique_{year}.csv"
    ac_path = data_dir / f"tarifs_AC_Martinique_{year}.csv"
    aep_all, ac_all = read_csv(aep_path), read_csv(ac_path)
    aep, aep_complete = usable(aep_all)
    ac, ac_complete = usable(ac_all)
    aep_role, ac_role = source_role(aep, aep_complete), source_role(ac, ac_complete)
    price_aep, price_ac = weighted(aep, "prix_ttc_120m3"), weighted(ac, "prix_ttc_120m3")
    if price_aep is None or price_ac is None:
        raise ValueError(f"Tarifs incomplets pour {year}: AEP={price_aep}, AC={price_ac}")
    combined_role = "PRODUCTION" if aep_role == ac_role == "PRODUCTION" else "VALIDATION" if aep_role in {"PRODUCTION", "VALIDATION"} and ac_role in {"PRODUCTION", "VALIDATION"} else "DIAGNOSTIC"
    aep_quality = "OK" if aep_role == "PRODUCTION" else "SOURCE_NOT_VERIFIED" if aep_role == "VALIDATION" else "SOURCE_INCOMPLETE"
    combined_quality = "OK" if combined_role == "PRODUCTION" else "SOURCE_NOT_VERIFIED" if combined_role == "VALIDATION" else "SOURCE_INCOMPLETE"
    component_aep_role = "VALIDATION" if aep_role in {"PRODUCTION", "VALIDATION"} else aep_role
    component_combined_role = "VALIDATION" if combined_role in {"PRODUCTION", "VALIDATION"} else combined_role
    sources = f"{aep_path.name} + {ac_path.name}"
    common = "Moyenne ponderee par la population desservie (D101.0/D201.0)."
    facts = [
        make_fact(year, "TAR_001", price_aep, "€/m³", aep_role, aep_path.name, "D102.0 pondere par D101.0", common, aep_quality,
                  note=f"{len(aep)} services; statuts source: {', '.join(sorted({r['statut'] for r in aep}))}."),
        make_fact(year, "TAR_002", price_aep * 120, "€/an", aep_role, aep_path.name, "TAR_001 x 120", "Facture type annuelle de 120 m3.", aep_quality),
        make_fact(year, "TAR_005", price_aep + price_ac, "€/m³", combined_role, sources, "D102.0 + D204.0", common, combined_quality),
        make_fact(year, "TAR_006", (price_aep + price_ac) * 120, "€/an", combined_role, sources, "TAR_005 x 120", "Facture type annuelle EP + AC de 120 m3.", combined_quality),
    ]
    # La table de faits publie la composante attendue par le gabarit historique.
    # La decomposition complete demeure en VALIDATION tant que le mapping ODE /
    # ODM des variables tarifaires n'est pas certifie.
    subscription = weighted_sum(aep, ("VP.191", "VP.190"))
    ep_service = weighted_sum(aep, ("VP.178", "VP.177"))
    ac_service = weighted_sum(ac, ("VP.178", "VP.177"))
    if subscription is not None:
        facts.append(make_fact(year, "TAR_004", subscription / (price_aep * 120) * 100, "%", component_aep_role, aep_path.name,
                               "Part abonnement = (VP.191 + VP.190) / facture TTC", "Part abonnement de la facture EP.",
                               "COMPONENT_MAPPING_REVIEW", "Ne pas publier avant validation des composantes ODE/ODM."))
    if ep_service is not None and ac_service is not None:
        facts.append(make_fact(year, "TAR_008", ep_service / ((price_aep + price_ac) * 120) * 100, "%", component_combined_role, sources,
                               "Part EP HT = (VP.178 + VP.177) EP / facture TTC EP+AC", "Part eau potable de la facture combinee.",
                               "COMPONENT_MAPPING_REVIEW", "Ne pas publier avant validation des composantes ODE/ODM."))
    write_csv(output_dir / f"fact_tarifs_sispea_{year}.csv", facts, FACT_FIELDS)
    composition = [
        {"annee_reference": year, "component": "EP_ABONNEMENT_HT", "value": subscription or "", "unit": "€/an", "record_role": "VALIDATION"},
        {"annee_reference": year, "component": "EP_SERVICE_HT", "value": ep_service or "", "unit": "€/an", "record_role": "VALIDATION"},
        {"annee_reference": year, "component": "AC_SERVICE_HT", "value": ac_service or "", "unit": "€/an", "record_role": "VALIDATION"},
        {"annee_reference": year, "component": "EP_TAXES_REDEVANCES", "value": weighted(aep, "VP.179") or "", "unit": "€/an", "record_role": "VALIDATION"},
        {"annee_reference": year, "component": "AC_TAXES_REDEVANCES", "value": weighted(ac, "VP.179") or "", "unit": "€/an", "record_role": "VALIDATION"},
    ]
    write_csv(output_dir / f"composition_tarifs_sispea_{year}.csv", composition,
              ["annee_reference", "component", "value", "unit", "record_role"])
    return facts


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    extract_parser = sub.add_parser("extract")
    extract_parser.add_argument("--year", type=int, required=True)
    extract_parser.add_argument("--aep", type=Path, required=True)
    extract_parser.add_argument("--ac", type=Path, required=True)
    extract_parser.add_argument("--data-dir", type=Path, required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--year", type=int, required=True)
    build_parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    build_parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "outputs")
    args = parser.parse_args()
    if args.command == "extract":
        extract(args.year, args.aep, args.ac, args.data_dir)
    else:
        build(args.year, args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
