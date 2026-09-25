"""Vérifie qu'un clone propre contient les fichiers nécessaires à l'application.

Le test regroupe les fichiers manquants dans un seul message afin de rendre
immédiatement visibles les dépendances non versionnées du dépôt.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "modules/reporting/report_builder.py",
    "modules/reporting/reporting_config.json",
    "modules/local_reports/config.json",
    "application/source_registry.json",
    "resources/MANIFEST.json",
    "resources/MANIFEST.csv",
    "modules/assainissement_portal/outputs/2023/fact_assainissement_portal_2023.csv",
    "modules/assainissement_portal/outputs/2024/fact_assainissement_portal_2024.csv",
]


class RepositoryIntegrityTests(unittest.TestCase):
    def test_required_files_are_versioned(self) -> None:
        missing = [p for p in REQUIRED_FILES if not (ROOT / p).exists()]
        self.assertEqual(
            [],
            missing,
            "Fichiers requis absents du dépôt :\n  - " + "\n  - ".join(missing),
        )

    def test_local_report_pdfs_are_present(self) -> None:
        cfg_path = ROOT / "modules/local_reports/config.json"
        if not cfg_path.exists():
            self.skipTest("config RAD/RPQS absente")
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        missing = [
            f"resources/source_documents/{s['year']}/{s['file']}"
            for s in cfg["sources"]
            if not (ROOT / "resources/source_documents" / str(s["year"]) / s["file"]).exists()
        ]
        self.assertEqual(
            [],
            missing,
            "PDF RAD/RPQS absents du corpus versionné :\n  - " + "\n  - ".join(missing),
        )


if __name__ == "__main__":
    unittest.main()
