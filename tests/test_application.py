from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from application import core

ROOT=Path(__file__).resolve().parents[1]

class ApplicationTests(unittest.TestCase):
    def test_status_has_core_sources(self):
        keys={s.key for s in core.source_status(2023)}
        self.assertTrue({'master','ars','portal','local_reports','population','bnpe','maps'} <= keys)

    def test_master_status_ne_retombe_pas_sur_les_anciens_masters(self):
        status=next(s for s in core.source_status(2023) if s.key=='master')
        canonical=ROOT/'outputs'/'2023'/'fact_indicateur_master_2023.csv'
        if canonical.exists():
            self.assertEqual('OK',status.status)
            self.assertEqual(str(canonical),status.detail)
        else:
            self.assertEqual('MANQUANT',status.status)
            self.assertIn('update_observatoire.py',status.detail)
        self.assertNotIn('outputs_v',status.detail)

    def test_portal_outputs_exist(self):
        for y in (2023,2024):
            p=ROOT/'modules/assainissement_portal/outputs'/str(y)/f'fact_assainissement_portal_{y}.csv'
            self.assertTrue(p.exists() and p.stat().st_size>100)

    def test_map_names_match_reporting_config(self):
        cfg=json.loads((ROOT/'modules/reporting/reporting_config.json').read_text(encoding='utf-8'))['asset_filename_by_token']
        for token, pattern in core.ASSET_FILENAME.items():
            self.assertEqual(pattern,cfg['{{'+token+'}}'])

    def test_draft_2023_smoke(self):
        r=core.build_report(2023,final=False)
        self.assertTrue(Path(r.docx).exists())
        self.assertTrue(Path(r.preflight).exists())

    def test_draft_2024_smoke(self):
        r=core.build_report(2024,final=False)
        self.assertTrue(Path(r.docx).exists())
        self.assertTrue(Path(r.preflight).exists())

class ManualOverrideTests(unittest.TestCase):
    """Import de valeurs complémentaires vers saisie/, dans une copie temporaire du référentiel."""

    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree,self.tmp)
        shutil.copytree(ROOT/'referentiel',self.tmp/'referentiel')
        (self.tmp/'modules/perimeters').mkdir(parents=True)
        shutil.copy2(ROOT/'modules/perimeters/known_absences.csv',self.tmp/'modules/perimeters/known_absences.csv')
        patcher=mock.patch.object(core,'ROOT',self.tmp); patcher.start(); self.addCleanup(patcher.stop)

    def write_src(self,rows):
        src=self.tmp/'complements.csv'
        core.write_scsv(src,rows,['indicator_id','territoire','value','validated'])
        return src

    def test_seules_les_lignes_validees_passent_en_production(self):
        src=self.write_src([{'indicator_id':'TAR_001','territoire':'CACEM','value':'3,12','validated':'oui'},
                            {'indicator_id':'TAR_001','territoire':'CAESM','value':'2.9','validated':'non'}])
        dest=core.import_manual_overrides(2024,src)
        rows={r['perimeter_id']:r for r in core.read_scsv(dest)}
        self.assertEqual(dest,self.tmp/'saisie'/'saisie_locale_2024.csv')
        self.assertEqual(('PRODUCTION','3.12'),(rows['CACEM_EPCI']['record_role'],rows['CACEM_EPCI']['value']))
        self.assertEqual('VALIDATION',rows['CAESM_EPCI']['record_role'])

    def test_indicateur_inconnu_refuse_sans_ecriture(self):
        src=self.write_src([{'indicator_id':'XXX_999','territoire':'CACEM','value':'1','validated':'oui'}])
        with self.assertRaises(ValueError): core.import_manual_overrides(2024,src)
        self.assertFalse((self.tmp/'saisie').exists())

if __name__=='__main__': unittest.main()
