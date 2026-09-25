#!/usr/bin/env python3
"""Point d'entrée annuel du Référentiel Eau & Assainissement.

    py update_observatoire.py --year 2024
    py update_observatoire.py --year 2024 --refresh-ars      (réseau requis)
    py update_observatoire.py --year 2024 --out D:/travail/2024

Construit le master unique en identifiants canoniques puis le certifie contre
referentiel/attentes.csv. Voir pipeline/run.py pour le détail des sorties.

L'ancien orchestrateur (modules/orchestrator/update_observatoire.py, qui
reprenait un master v1/v2/v3 préparé en amont) n'est plus utilisé.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pipeline.run import run

ROOT = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Master unique + certification d'un millésime.")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", type=Path, help="Répertoire de sortie (défaut : outputs/YYYY)")
    ap.add_argument("--refresh-ars", action="store_true", help="Retélécharge les résultats ARS depuis Hub'Eau.")
    a = ap.parse_args()

    if a.refresh_ars:
        subprocess.run([sys.executable, str(ROOT / "modules/ars_quality/ars_quality_etl.py"), "--year", str(a.year),
                        "--out", str(ROOT / "modules/ars_quality/outputs" / str(a.year))], check=True)

    res = run(a.year, a.out.resolve() if a.out else None, ROOT)
    c = res["certification"]
    print(f"Millésime {a.year} : {c['status']}")
    print(f"  cellules attendues : {c['cellules_attendues']} — production {c['cellules']['PRODUCTION']} "
          f"({c['taux_production_pct']} %), lacunes déclarées {c['cellules']['LACUNE_DECLAREE']}, "
          f"à valider {c['cellules']['A_VALIDER']}, manquantes {c['cellules']['MANQUANT']}")
    print(f"  anomalies bloquantes : {c['anomalies_bloquantes']}")
    print(f"  détail : {res['out'] / f'couverture_{a.year}.csv'}")
    return 0 if c["status"] != "NOT_CERTIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
