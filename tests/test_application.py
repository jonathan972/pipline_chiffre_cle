from __future__ import annotations
import csv
import hashlib
import json
import unittest
from pathlib import Path

from application import core
from modules.assainissement_portal import assainissement_portal_etl as portal

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

    def test_portal_outputs_sont_reproductibles_depuis_les_sources_versionnees(self):
        for year in (2023, 2024):
            source=ROOT/'resources'/'source_csv'/str(year)/f'export-portail_assainissement_{year}.csv'
            expected=core.read_scsv(ROOT/'modules'/'assainissement_portal'/'outputs'/str(year)/f'fact_assainissement_portal_{year}.csv')
            facts, _, _=portal.aggregate(portal.read_portal(source),year,ROOT,source.name)
            normalized=[{key:str(value) for key,value in row.items()} for row in facts]
            self.assertEqual(expected,normalized)

    def test_manifest_ressources(self):
        manifest=ROOT/'resources'/'MANIFEST.csv'
        with manifest.open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream,delimiter=';'))
        self.assertGreaterEqual(len(rows),5)
        for row in rows:
            path=ROOT/row['path']
            self.assertTrue(path.is_file(),row['path'])
            self.assertEqual(int(row['bytes']),path.stat().st_size,row['path'])
            self.assertEqual(row['sha256'],hashlib.sha256(path.read_bytes()).hexdigest().upper(),row['path'])

    def test_map_names_match_reporting_config(self):
        cfg=json.loads((ROOT/'modules/reporting/reporting_config.json').read_text(encoding='utf-8'))['asset_filename_by_token']
        for token, pattern in core.ASSET_FILENAME.items():
            self.assertEqual(pattern,cfg['{{'+token+'}}'])

    def test_local_report_resources_match_config(self):
        cfg=json.loads((ROOT/'modules/local_reports/config.json').read_text(encoding='utf-8'))
        missing=set()
        for src in cfg['sources']:
            p=ROOT/'resources/source_documents'/str(src['year'])/src['file']
            if not p.exists(): missing.add((str(src['year']),src['file']))
        declared={(r['year'],r['file']) for r in core.read_scsv(ROOT/'resources'/'MISSING_SOURCES.csv')}
        self.assertEqual(declared,missing)

    def test_draft_2023_smoke(self):
        r=core.build_report(2023,final=False)
        self.assertTrue(Path(r.docx).exists())
        self.assertTrue(Path(r.preflight).exists())
        ready=sum(x.get('status')=='READY' for x in core.read_scsv(Path(r.preflight)))
        self.assertEqual(ready,r.summary['production_count'])

    def test_draft_2024_smoke(self):
        r=core.build_report(2024,final=False)
        self.assertTrue(Path(r.docx).exists())
        self.assertTrue(Path(r.preflight).exists())
        ready=sum(x.get('status')=='READY' for x in core.read_scsv(Path(r.preflight)))
        self.assertEqual(ready,r.summary['production_count'])

    def test_final_reste_bloque_si_le_millesime_n_est_pas_certifie(self):
        with self.assertRaisesRegex(RuntimeError,'Rapport final bloqué'):
            core.build_report(2024,final=True)

if __name__=='__main__': unittest.main()
