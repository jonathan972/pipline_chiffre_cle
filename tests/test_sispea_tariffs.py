"""Tests du module tarifaire SISPEA et de sa frontiere de publication."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.sispea_tariffs.sispea_tariffs_etl import build, read_csv, source_role, usable, weighted  # noqa: E402
from pipeline.master import Master  # noqa: E402
from pipeline.publication import production_rows  # noqa: E402
from pipeline.referentiel import Referentiel  # noqa: E402


class TestSispeaTariffs(unittest.TestCase):
    def test_snapshots_ne_contiennent_que_la_martinique(self):
        for year in (2023, 2024):
            for competence in ("AEP", "AC"):
                path = ROOT / f"modules/sispea_tariffs/data/tarifs_{competence}_Martinique_{year}.csv"
                rows = read_csv(path)
                self.assertTrue(rows)
                self.assertEqual({"972"}, {row["departement"] for row in rows})

    def test_ponderation_officielle_par_population_desservie(self):
        rows = [
            {"population_desservie": "100", "prix_ttc_120m3": "2"},
            {"population_desservie": "300", "prix_ttc_120m3": "4"},
        ]
        self.assertEqual(3.5, weighted(rows, "prix_ttc_120m3"))

    def test_statut_source_gouverne_le_role(self):
        confirmed = [{"statut": "Confirmé / publié"}]
        unverified = [{"statut": "Publié non vérifié"}]
        self.assertEqual("PRODUCTION", source_role(confirmed, True))
        self.assertEqual("VALIDATION", source_role(unverified, True))
        self.assertEqual("DIAGNOSTIC", source_role(confirmed, False))

    def test_millesimes_regenerables_depuis_les_snapshots(self):
        data = ROOT / "modules/sispea_tariffs/data"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            facts_2023 = build(2023, data, out)
            facts_2024 = build(2024, data, out)
        by_2023 = {row["indicator_id"]: row for row in facts_2023}
        by_2024 = {row["indicator_id"]: row for row in facts_2024}
        self.assertAlmostEqual(2.936283, float(by_2023["TAR_001"]["value"]), places=6)
        self.assertEqual(2.94, round(float(by_2023["TAR_001"]["value"]), 2))
        self.assertEqual(6.01, round(float(by_2023["TAR_005"]["value"]), 2))
        self.assertEqual("PRODUCTION", by_2023["TAR_006"]["record_role"])
        self.assertEqual("VALIDATION", by_2023["TAR_004"]["record_role"])
        self.assertEqual("VALIDATION", by_2024["TAR_001"]["record_role"])
        self.assertEqual("SOURCE_NOT_VERIFIED", by_2024["TAR_001"]["quality_status"])
        self.assertEqual(2.95, round(float(by_2024["TAR_001"]["value"]), 2))
        self.assertEqual(6.06, round(float(by_2024["TAR_005"]["value"]), 2))

    def test_master_derive_tarifs_mensuels_sans_promouvoir_validation(self):
        ref = Referentiel.load(ROOT)
        master_2023 = Master(ref, 2023).build()
        master_2024 = Master(ref, 2024).build()
        rows_2023 = {(r["indicator_id"], r["record_role"]): r for r in master_2023.facts if r["perimeter_id"] == "MARTINIQUE"}
        rows_2024 = {(r["indicator_id"], r["record_role"]): r for r in master_2024.facts if r["perimeter_id"] == "MARTINIQUE"}
        self.assertIn(("TAR_003", "PRODUCTION"), rows_2023)
        self.assertIn(("TAR_007", "PRODUCTION"), rows_2023)
        self.assertIn(("TAR_003", "VALIDATION"), rows_2024)
        self.assertIn(("TAR_007", "VALIDATION"), rows_2024)
        published_2024 = {(r["indicator_id"], r["perimeter_id"]) for r in production_rows(master_2024.facts)}
        self.assertNotIn(("TAR_001", "MARTINIQUE"), published_2024)
        self.assertNotIn(("TAR_007", "MARTINIQUE"), published_2024)

    def test_les_services_sans_population_ne_sont_pas_forces_a_zero(self):
        rows = [
            {"population_desservie": "", "prix_ttc_120m3": ""},
            {"population_desservie": "100", "prix_ttc_120m3": "2"},
        ]
        valid, complete = usable(rows)
        self.assertTrue(complete)
        self.assertEqual(1, len(valid))


if __name__ == "__main__":
    unittest.main()
