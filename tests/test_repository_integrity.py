"""Vérifie qu'un clone propre contient les fichiers nécessaires à l'application.

Les PDF RAD/RPQS ne sont pas nécessaires à l'exécution : leurs données sont
déjà extraites et versionnées dans modules/local_reports/outputs/, et leurs
empreintes SHA-256 sont dans source_manifest.csv. Les PDF ne servent qu'à
réextraire ; on vérifie donc la traçabilité de chaque source, pas sa présence.
"""
from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "modules/reporting/report_builder.py",
    "modules/reporting/reporting_config.json",
    "modules/local_reports/config.json",
    "modules/local_reports/outputs/source_manifest.csv",
    "modules/local_reports/outputs/fact_local_reports_2023.csv",
    "modules/local_reports/outputs/fact_local_reports_2024.csv",
    "application/source_registry.json",
    "modules/assainissement_portal/outputs/2023/fact_assainissement_portal_2023.csv",
    "modules/assainissement_portal/outputs/2024/fact_assainissement_portal_2024.csv",
]


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


class RepositoryIntegrityTests(unittest.TestCase):
    def test_required_files_are_versioned(self) -> None:
        missing = [p for p in REQUIRED_FILES if not (ROOT / p).exists()]
        self.assertEqual([], missing, "Fichiers requis absents du dépôt :\n  - " + "\n  - ".join(missing))

    def test_chaque_source_rad_rpqs_est_extraite_et_tracee(self) -> None:
        cfg = json.loads((ROOT / "modules/local_reports/config.json").read_text(encoding="utf-8"))
        out = ROOT / "modules/local_reports/outputs"
        manifest = {r["source_file"]: r for r in read(out / "source_manifest.csv")}
        extracted = {r["source_file"] for y in (2023, 2024) for r in read(out / f"fact_local_reports_{y}.csv")}
        problems = []
        for src in cfg["sources"]:
            name = src["file"]
            if len(manifest.get(name, {}).get("sha256", "")) != 64:
                problems.append(f"{name} : empreinte SHA-256 absente de source_manifest.csv")
            if name not in extracted:
                problems.append(f"{name} : aucune donnée extraite")
        self.assertEqual([], problems, "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
