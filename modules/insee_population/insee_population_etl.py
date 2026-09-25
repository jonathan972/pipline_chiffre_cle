#!/usr/bin/env python3
"""ETL population INSEE pour le référentiel ODE Martinique.

- Historique initial : fichier seed officiel 2019-2023.
- Mise à jour annuelle : API Melodi DS_POPULATIONS_REFERENCE (population municipale PMUN).
- Résolution d'une population pour un millésime eau : même millésime si disponible,
  sinon dernière population officielle disponible si la politique l'autorise.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        w.writeheader(); w.writerows(rows)


def fetch_latest(api_base: str, territory: dict[str, str], measure: str) -> dict[str, Any]:
    geo = f"{territory['niveau_geo']}-{territory['code_geo']}"
    params = urllib.parse.urlencode({"GEO": geo, "POPREF_MEASURE": measure, "maxResult": 20})
    url = f"{api_base}?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ODE-Martinique-Referentiel/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.load(resp)
    # L'API peut renvoyer directement une liste ou un objet contenant observations/data.
    if isinstance(payload, list):
        rows = payload
    else:
        rows = payload.get("observations") or payload.get("data") or payload.get("results") or payload.get("series") or []
    if isinstance(rows, dict):
        rows = rows.get("observations") or rows.get("data") or []
    candidates = []
    for row in rows:
        if str(row.get("POPREF_MEASURE", "")) != measure:
            continue
        if row.get("OBS_VALUE") is None and row.get("OBS_VALUE_NIVEAU") is None:
            continue
        candidates.append(row)
    if not candidates:
        raise RuntimeError(f"Aucune population {measure} retournée pour {geo}. URL: {url}")
    row = max(candidates, key=lambda r: int(r.get("TIME_PERIOD", 0)))
    value = row.get("OBS_VALUE", row.get("OBS_VALUE_NIVEAU"))
    return {
        "annee_population": int(row["TIME_PERIOD"]),
        "niveau_geo": territory["niveau_geo"],
        "code_geo": territory["code_geo"],
        "territoire": territory["territoire"],
        "population_municipale": int(round(float(value))),
        "date_publication": "",
        "date_entree_vigueur": "",
        "source_url": url,
        "source_type": "INSEE_MELODI",
    }


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    d: dict[tuple[int, str, str], dict[str, Any]] = {}
    for r in rows:
        key = (int(r["annee_population"]), r["niveau_geo"], r["code_geo"])
        d[key] = r
    return sorted(d.values(), key=lambda r: (int(r["annee_population"]), r["niveau_geo"], r["territoire"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="data/population_reference_seed.csv")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--refresh", action="store_true", help="Interroger l'API Melodi et ajouter/remplacer le dernier millésime officiel")
    ap.add_argument("--start-year", type=int, default=2019)
    ap.add_argument("--end-year", type=int, default=2024)
    ap.add_argument("--fallback", choices=["latest_official", "none"], default=None)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    seed = (here / args.seed).resolve() if not Path(args.seed).is_absolute() else Path(args.seed)
    config_path = (here / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    out = (here / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.load(config_path.open(encoding="utf-8"))
    fallback = args.fallback or cfg.get("fallback_policy", "latest_official")

    rows: list[dict[str, Any]] = []
    for r in read_csv(seed):
        rr = dict(r); rr["annee_population"] = int(rr["annee_population"]); rr["population_municipale"] = int(rr["population_municipale"])
        rows.append(rr)

    refresh_errors = []
    if args.refresh:
        for t in cfg["territories"]:
            try:
                rows.append(fetch_latest(cfg["api_base"], t, cfg.get("measure", "PMUN")))
            except Exception as e:
                refresh_errors.append({"territoire": t["territoire"], "error": str(e)})
    rows = dedupe(rows)

    official_fields = ["annee_population","niveau_geo","code_geo","territoire","population_municipale","date_publication","date_entree_vigueur","source_url","source_type"]
    write_csv(out / "fact_population_officielle.csv", rows, official_fields)

    # Contrôles de cohérence EPCI -> Martinique
    issues = []
    by_year: dict[int, list[dict[str, Any]]] = {}
    for r in rows: by_year.setdefault(int(r["annee_population"]), []).append(r)
    for year, yr in sorted(by_year.items()):
        mart = next((r for r in yr if r["territoire"] == "Martinique"), None)
        epci = [r for r in yr if r["territoire"] in cfg["expected_epci"]]
        if mart and len(epci) == len(cfg["expected_epci"]):
            s = sum(int(r["population_municipale"]) for r in epci)
            if s != int(mart["population_municipale"]):
                issues.append({"annee":year,"severity":"ERROR","type":"EPCI_SUM_MISMATCH","message":f"Somme EPCI={s} != Martinique={mart['population_municipale']}"})
        else:
            issues.append({"annee":year,"severity":"WARNING","type":"COVERAGE","message":"Couverture EPCI/Martinique incomplète pour le millésime."})

    # Résolution 2019..N, avec fallback explicite si l'année officielle n'existe pas encore.
    resolved = []
    territories = cfg["territories"]
    for target_year in range(args.start_year, args.end_year + 1):
        for t in territories:
            candidates = [r for r in rows if r["territoire"] == t["territoire"] and int(r["annee_population"]) <= target_year]
            exact = next((r for r in candidates if int(r["annee_population"]) == target_year), None)
            chosen = exact
            status = "OFFICIEL_MILLESIME_N" if exact else "INDISPONIBLE"
            if chosen is None and fallback == "latest_official" and candidates:
                chosen = max(candidates, key=lambda r: int(r["annee_population"]))
                status = "DERNIERE_OFFICIELLE_DISPONIBLE"
            resolved.append({
                "annee_indicateur": target_year,
                "territoire": t["territoire"],
                "niveau_geo": t["niveau_geo"],
                "code_geo": t["code_geo"],
                "population_utilisee": chosen["population_municipale"] if chosen else "",
                "millesime_population": chosen["annee_population"] if chosen else "",
                "statut_resolution": status,
                "source_url": chosen["source_url"] if chosen else "",
            })
            if status == "DERNIERE_OFFICIELLE_DISPONIBLE":
                issues.append({"annee":target_year,"severity":"INFO","type":"POPULATION_FALLBACK","message":f"{t['territoire']}: millésime {chosen['annee_population']} utilisé pour l'indicateur {target_year}."})
    write_csv(out / f"fact_population_resolue_{args.start_year}_{args.end_year}.csv", resolved,
              ["annee_indicateur","territoire","niveau_geo","code_geo","population_utilisee","millesime_population","statut_resolution","source_url"])
    write_csv(out / "data_quality_issues.csv", issues, ["annee","severity","type","message"])

    # Validation clé du rapport 2022 : 21 041 846 m³ -> ~160 L/j/hab avec 361 019 habitants.
    pop_2022 = next(int(r["population_municipale"]) for r in rows if int(r["annee_population"]) == 2022 and r["territoire"] == "Martinique")
    volume_facture_ode_2022 = 21_041_846
    l_j_hab = volume_facture_ode_2022 * 1000 / (pop_2022 * 365)
    validation = [{
        "indicator_id":"EP_001_VALIDATION",
        "annee":2022,
        "territoire":"Martinique",
        "population":pop_2022,
        "volume_facture_m3":volume_facture_ode_2022,
        "valeur_calculee_l_j_hab":round(l_j_hab, 4),
        "valeur_rapport_l_j_hab":160,
        "ecart":round(l_j_hab-160, 4),
        "note":"Validation uniquement : le volume facturé provient du rapport/RAD-RPQS, la population de l'INSEE."
    }]
    write_csv(out / "validation_population_2022.csv", validation, list(validation[0].keys()))

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": cfg["dataset"],
        "api_base": cfg["api_base"],
        "official_years": sorted(by_year),
        "latest_official_year": max(by_year),
        "target_years": [args.start_year,args.end_year],
        "fallback_policy": fallback,
        "quality_issue_count": len(issues),
        "refresh_errors": refresh_errors,
        "validation_2022_l_j_hab": l_j_hab,
        "seed_sha256": hashlib.sha256(seed.read_bytes()).hexdigest(),
    }
    json.dump(summary, (out / "summary.json").open("w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
