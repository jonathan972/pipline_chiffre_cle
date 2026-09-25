from __future__ import annotations
import json
import unittest
from pathlib import Path

from application import core

ROOT=Path(__file__).resolve().parents[1]

class ApplicationTests(unittest.TestCase):
    def test_status_has_core_sources(self):
        keys={s.key for s in core.source_status(2023)}
        self.assertTrue({'master','ars','portal','local_reports','population','bnpe','maps'} <= keys)

    def test_portal_outputs_exist(self):
        for y in (2023,2024):
            p=ROOT/'modules/assainissement_portal/outputs'/str(y)/f'fact_assainissement_portal_{y}.csv'
            self.assertTrue(p.exists() and p.stat().st_size>100)

    def test_map_names_match_reporting_config(self):
        cfg=json.loads((ROOT/'modules/reporting/reporting_config.json').read_text(encoding='utf-8'))['asset_filename_by_token']
        for token, pattern in core.ASSET_FILENAME.items():
            self.assertEqual(pattern,cfg['{{'+token+'}}'])

    def test_local_report_resources_match_config(self):
        cfg=json.loads((ROOT/'modules/local_reports/config.json').read_text(encoding='utf-8'))
        missing=[]
        for src in cfg['sources']:
            p=ROOT/'resources/source_documents'/str(src['year'])/src['file']
            if not p.exists(): missing.append(str(p))
        self.assertEqual([],missing)

    def test_draft_2023_smoke(self):
        r=core.build_report(2023,final=False)
        self.assertTrue(Path(r.docx).exists())
        self.assertTrue(Path(r.preflight).exists())

    def test_draft_2024_smoke(self):
        r=core.build_report(2024,final=False)
        self.assertTrue(Path(r.docx).exists())
        self.assertTrue(Path(r.preflight).exists())

if __name__=='__main__': unittest.main()
