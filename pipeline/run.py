"""Exécution complète d'un millésime : master unique puis certification.

    py -m pipeline.run --year 2024 [--out dossier]

Sorties (par défaut outputs/YYYY/) :
- fact_indicateur_master_YYYY.csv : table de faits canonique (toutes les lignes, tous les rôles) ;
- anomalies_YYYY.csv              : anomalies bloquantes et avertissements ;
- couverture_YYYY.csv             : une ligne par cellule attendue indicateur × périmètre ;
- statut_indicateurs_YYYY.csv     : une ligne par indicateur de publication (80) ;
- certification_YYYY.json         : statut global ;
- run_manifest.json               : sources lues avec empreintes SHA-256.
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .certification import COUVERTURE_FIELDS, certify
from .master import ANOMALY_FIELDS, FIELDS, Master
from .referentiel import ROOT, Referentiel, write_csv


def run(year: int, out: Path | None = None, root: Path = ROOT) -> dict:
    start = datetime.now(timezone.utc)
    ref = Referentiel.load(root)
    out = out or root / "outputs" / str(year)
    m = Master(ref, year).build()
    cert, cells, par_ind = certify(ref, year, m.facts, m.anomalies)

    write_csv(out / f"fact_indicateur_master_{year}.csv", m.facts, FIELDS)
    write_csv(out / f"anomalies_{year}.csv", m.anomalies, ANOMALY_FIELDS)
    write_csv(out / f"couverture_{year}.csv", cells, COUVERTURE_FIELDS)
    write_csv(out / f"statut_indicateurs_{year}.csv", par_ind,
              ["annee", "indicator_id", "libelle", "statut_indicateur", "cellules", "cellules_production"])
    (out / f"certification_{year}.json").write_text(json.dumps(cert, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "run_id": str(uuid.uuid4()), "year": year, "started_at": start.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(), "modules": m.events,
        "sources": m.manifest_sources(), "lignes": len(m.facts),
        "roles": {r: sum(f["record_role"] == r for f in m.facts) for r in ("PRODUCTION", "VALIDATION", "DIAGNOSTIC", "AUDIT")},
        "certification": cert["status"],
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"out": out, "certification": cert, "manifest": manifest}


def main() -> int:
    ap = argparse.ArgumentParser(description="Master unique + certification d'un millésime.")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = run(a.year, a.out)
    c = res["certification"]
    print(f"Millésime {a.year} : {c['status']}")
    print(f"  cellules attendues : {c['cellules_attendues']} — production {c['cellules']['PRODUCTION']} "
          f"({c['taux_production_pct']} %), lacunes déclarées {c['cellules']['LACUNE_DECLAREE']}, "
          f"à valider {c['cellules']['A_VALIDER']}, manquantes {c['cellules']['MANQUANT']}")
    print(f"  anomalies bloquantes : {c['anomalies_bloquantes']} — avertissements : {c['avertissements']}")
    print(f"  sorties : {res['out']}")
    return 0 if c["status"] != "NOT_CERTIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
