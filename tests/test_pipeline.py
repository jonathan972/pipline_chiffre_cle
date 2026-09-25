"""Tests structurants du socle de données (master unique + certification)."""
from __future__ import annotations

import csv
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.certification import STATUTS_CELLULE, STATUTS_INDICATEUR, certify  # noqa: E402
from pipeline.master import Master  # noqa: E402
from pipeline.publication import production_index, production_rows  # noqa: E402
from pipeline.referentiel import Referentiel  # noqa: E402
from pipeline.run import run  # noqa: E402

REF = Referentiel.load(ROOT)
CODES_HISTORIQUES = re.compile(r"^(EP_ABONNES|AC_ABONNES|POP_MUNICIPALE|QUAL_|P1\d\d\.\d|P301|D301|ANC_CONTROLE|SOURCE_COVERAGE)")


def _build(year: int) -> Master:
    return Master(REF, year).build()


class TestNomenclature(unittest.TestCase):
    def test_catalogue_80_indicateurs(self):
        self.assertEqual(80, len(REF.publication_ids()))

    def test_correspondances_pointent_vers_le_referentiel(self):
        for (src, code), m in REF.correspondances.items():
            if m["record_role_force"] == "IGNORE":
                continue
            self.assertIn(m["indicator_id"], REF.indicateurs, f"{src}:{code}")

    def test_attentes_sur_ids_et_perimetres_connus(self):
        for a in REF.attentes:
            self.assertIn(a["indicator_id"], REF.indicateurs)
            self.assertIn(a["perimeter_id"], REF.perimetres)

    def test_tous_les_indicateurs_de_publication_ont_une_attente(self):
        expected_ids = {a["indicator_id"] for a in REF.attentes}
        self.assertEqual(set(), set(REF.publication_ids()) - expected_ids)

    def test_attentes_sans_doublon_exact(self):
        keys = [(a["indicator_id"], a["perimeter_id"], a["annee_debut"], a["annee_fin"])
                for a in REF.attentes]
        self.assertEqual(len(keys), len(set(keys)))

    def test_master_uniquement_en_ids_canoniques(self):
        for year in (2022, 2023, 2024):
            m = _build(year)
            for f in m.facts:
                self.assertIn(f["indicator_id"], REF.indicateurs, f"{year} {f['indicator_id']}")
                self.assertNotRegex(f["indicator_id"], CODES_HISTORIQUES)
                self.assertIn(f["perimeter_id"], REF.perimetres)


class TestCertification(unittest.TestCase):
    def test_1_annee_vide_non_certifiee(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run(2099, Path(tmp), ROOT)
        c = res["certification"]
        self.assertEqual("NOT_CERTIFIED", c["status"])
        self.assertEqual(0, c["cellules"]["PRODUCTION"])
        self.assertEqual(c["cellules_attendues"], c["cellules"]["MANQUANT"])

    def test_3_chaque_indicateur_a_un_statut_explicite(self):
        for year in (2022, 2023, 2024):
            m = _build(year)
            _, cells, par_ind = certify(REF, year, m.facts, m.anomalies)
            self.assertEqual(sorted(REF.publication_ids()), sorted(p["indicator_id"] for p in par_ind))
            for p in par_ind:
                self.assertIn(p["statut_indicateur"], STATUTS_INDICATEUR)
            self.assertEqual(len(REF.attentes_annee(year)), len(cells))
            for c in cells:
                self.assertIn(c["statut_couverture"], STATUTS_CELLULE)

    def test_code_source_inconnu_bloquant(self):
        m = Master(REF, 2099)
        m.translate({"source": "LOCAL", "code_source": "CODE_INVENTE", "perimeter_raw": "CACEM_EPCI",
                     "territoire_raw": "", "value": "1"})
        self.assertEqual("CODE_NON_MAPPE", m.anomalies[0]["type"])
        cert, _, _ = certify(REF, 2099, m.facts, m.anomalies)
        self.assertEqual("NOT_CERTIFIED", cert["status"])

    def test_conflit_de_production_bloquant(self):
        m = Master(REF, 2099)
        for v in ("10", "12"):
            m.add("EP_005", "CACEM_EPCI", v, "abonnés", "PRODUCTION", source="TEST")
        m.check()
        self.assertIn("CONFLIT_PRODUCTION", {a["type"] for a in m.anomalies})

    def test_absence_declaree_devient_lacune_et_bloque_le_total(self):
        m = _build(2024)
        _, cells, _ = certify(REF, 2024, m.facts, m.anomalies)
        by = {(c["indicator_id"], c["perimeter_id"]): c["statut_couverture"] for c in cells}
        self.assertEqual("LACUNE_DECLAREE", by[("EP_006", "CACEM_EPCI")])
        self.assertEqual("LACUNE_DECLAREE", by[("EP_006", "MARTINIQUE")])

    def test_diagnostic_jamais_compte_comme_production(self):
        m = _build(2023)
        _, cells, _ = certify(REF, 2023, m.facts, m.anomalies)
        for c in cells:
            if c["statut_couverture"] == "PRODUCTION":
                rows = [f for f in m.facts if f["indicator_id"] == c["indicator_id"]
                        and f["perimeter_id"] == c["perimeter_id"] and f["record_role"] == "PRODUCTION"]
                self.assertTrue(rows)

    def test_frontiere_publication_exclut_tous_les_roles_non_production(self):
        rows = [
            {"indicator_id": "EP_003", "perimeter_id": "MARTINIQUE", "record_role": "DIAGNOSTIC", "value": "99"},
            {"indicator_id": "EP_004", "perimeter_id": "MARTINIQUE", "record_role": "VALIDATION", "value": "98"},
            {"indicator_id": "EP_005", "perimeter_id": "MARTINIQUE", "record_role": "AUDIT", "value": "1"},
            {"indicator_id": "EP_006", "perimeter_id": "MARTINIQUE", "record_role": "PRODUCTION", "value": "2"},
        ]
        self.assertEqual([rows[-1]], production_rows(rows))
        self.assertEqual({("EP_006", "MARTINIQUE")}, set(production_index(rows)))

    def test_frontiere_publication_refuse_deux_valeurs_production(self):
        rows = [
            {"indicator_id": "EP_006", "perimeter_id": "MARTINIQUE", "record_role": "PRODUCTION", "value": "1"},
            {"indicator_id": "EP_006", "perimeter_id": "MARTINIQUE", "record_role": "PRODUCTION", "value": "2"},
        ]
        with self.assertRaisesRegex(ValueError, "Plusieurs lignes PRODUCTION"):
            production_rows(rows)


class TestRegeneration2022(unittest.TestCase):
    """Valeurs stables du rapport 2022, que le pipeline doit retrouver à 0,1 % près."""
    ATTENDU = {
        ("EP_005", "MARTINIQUE"): 190066,
        ("EP_017", "MARTINIQUE"): 3867,
        ("EP_019", "CACEM_EPCI"): 64.5,
        ("EP_019", "CAP_NORD_DSP_2020_2024"): 52.4,
        ("EP_019", "EX_SICSM_DSP_2015_2027"): 81.8,
        ("RES_014", "MARTINIQUE"): 44771108,
        ("RES_018", "MARTINIQUE"): 1419.53,
        ("AC_003", "MARTINIQUE"): 103,
        ("AC_012", "MARTINIQUE"): 1622,
    }

    def test_valeurs_production_2022(self):
        m = _build(2022)
        for (iid, pid), expected in self.ATTENDU.items():
            rows = [f for f in m.facts if f["indicator_id"] == iid and f["perimeter_id"] == pid and f["record_role"] == "PRODUCTION"]
            self.assertEqual(1, len(rows), f"{iid} {pid}")
            self.assertAlmostEqual(expected, float(rows[0]["value"]), delta=abs(expected) * 0.001, msg=f"{iid} {pid}")


class TestRattachementTerritorial(unittest.TestCase):
    def test_aucun_code_commune_en_dur(self):
        for p in [*ROOT.glob("pipeline/*.py"), ROOT / "modules/ars_quality/ars_quality_etl.py",
                  ROOT / "modules/assainissement_portal/assainissement_portal_etl.py"]:
            self.assertIsNone(re.search(r"972\d\d", p.read_text(encoding="utf-8")), p.name)

    def test_ars_partition_epci(self):
        for year in (2022, 2023, 2024):
            p = ROOT / f"modules/ars_quality/outputs/{year}/fact_ars_quality_{year}.csv"
            with p.open(encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            for iid in ("QUAL_MICROBIO_CONFORMITE", "QUAL_PC_CONFORMITE"):
                d = {r["territoire"]: int(r["denominator"]) for r in rows if r["indicator_id"] == iid}
                self.assertEqual(d["Martinique"], d["CACEM"] + d["CAESM"] + d["CAP_NORD"], f"{year} {iid}")


if __name__ == "__main__":
    unittest.main()
