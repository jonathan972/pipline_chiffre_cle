from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "certify_year", ROOT / "modules" / "orchestrator" / "certify_year.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CertificationRegressionTests(unittest.TestCase):
    def test_historical_certifications(self) -> None:
        expected = {
            2022: ("CERTIFIED_WITH_GAPS", 3, 0),
            2023: ("CERTIFIED_WITH_GAPS", 3, 0),
            2024: ("CERTIFIED_WITH_GAPS", 4, 0),
        }
        absences = MODULE.read_semicolon(
            ROOT / "modules" / "perimeters" / "known_absences.csv"
        )
        for year, (status, gap_count, blocker_count) in expected.items():
            folder = ROOT / "modules" / "orchestrator" / "outputs" / f"certif_{year}"
            result = MODULE.certify(
                year,
                MODULE.read_semicolon(folder / f"fact_indicateur_master_{year}.csv"),
                MODULE.read_semicolon(folder / f"quality_report_{year}.csv"),
                absences,
            )
            self.assertEqual(status, result["status"])
            self.assertEqual(gap_count, result["gaps_count"])
            self.assertEqual(blocker_count, result["blocking_anomalies_count"])

    def test_production_error_is_blocking(self) -> None:
        result = MODULE.certify(
            2025,
            [{
                "indicator_id": "X",
                "territoire": "Martinique",
                "perimeter_id": "MARTINIQUE",
                "record_role": "PRODUCTION",
                "coverage_status": "COMPLETE",
                "quality_status": "SOURCE_ERROR_SUSPECTED",
            }],
            [],
            [],
        )
        self.assertEqual("NOT_CERTIFIED", result["status"])

    def test_audit_error_is_not_blocking(self) -> None:
        result = MODULE.certify(
            2025,
            [{
                "indicator_id": "X_PUBLISHED",
                "territoire": "Martinique",
                "perimeter_id": "MARTINIQUE",
                "record_role": "AUDIT",
                "coverage_status": "COMPLETE",
                "quality_status": "SOURCE_CALCULATION_ERROR",
            }],
            [],
            [],
        )
        self.assertEqual("CERTIFIED", result["status"])
        self.assertEqual(1, result["audit_findings_count"])


if __name__ == "__main__":
    unittest.main()
