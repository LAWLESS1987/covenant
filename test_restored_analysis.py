"""Restored analysis tools keep evidence and fail on missing or invalid analysis."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import covenant_scenarios as scenarios
import covenant_thesis as thesis
import covenant_local_analysis as analysis


class AnalysisTests(unittest.TestCase):
    def test_scenario_pass_records_evidence_and_updates_memory(self):
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            priv=Path(td)/'private';priv.mkdir();memory=Path(td)/'ops/chat/MEMORY.md'
            scenario={'name':'fixture','question':'Could this improve mutual benefit?'}
            (priv/'SCENARIOS.json').write_text(json.dumps({'scenarios':[scenario],'history':[]}))
            response={'weights':{'fixture':{'p':0.6,'moved_by':'fixture observation','would_move_it':'replication'}},'introspection':['not measured']}
            with patch.object(scenarios,'PRIV',str(priv)),patch.object(scenarios,'TABLE',str(priv/'SCENARIOS.json')),patch.object(scenarios,'LEDGER',str(priv/'SCENARIOS.md')),patch.object(scenarios,'MEMORY',str(memory)),patch.object(scenarios,'live_state',return_value='fixture state'),patch('covenant_model.alive',return_value=True),patch('covenant_model.ask',return_value=(json.dumps(response),{'model':'fixture-model'})):
                self.assertEqual(scenarios.main([]),0)
                first=(priv/'SCENARIOS.md').read_text()
                self.assertIn('fixture observation',first)
                self.assertIn('[scenario]',memory.read_text())
                self.assertEqual(scenarios.main([]),0)
                self.assertTrue((priv/'SCENARIOS.md').read_text().startswith(first))

    def test_invalid_probabilities_are_not_recorded_as_success(self):
        for p in (True,float('nan'),-0.1,1.1,'0.5'):
            with self.assertRaises(ValueError):
                scenarios.validate_weights({'weights':{'f':{'p':p,'moved_by':'x','would_move_it':'y'}}},[{'name':'f'}])

    def test_unreadable_table_and_failed_replace_preserve_previous_record(self):
        with tempfile.TemporaryDirectory() as td,patch.object(scenarios,'PRIV',td),patch.object(scenarios,'TABLE',str(Path(td)/'SCENARIOS.json')):
            table=Path(td)/'SCENARIOS.json';table.write_text('corrupt fixture')
            with self.assertRaises(ValueError):scenarios.load_table()
            self.assertEqual(table.read_text(),'corrupt fixture')
            table.write_text('{"scenarios":[],"history":[]}')
            previous=table.read_bytes()
            with patch.object(scenarios.os,'replace',side_effect=OSError('fixture write failure')):
                with self.assertRaises(OSError):scenarios.save_table({'new':'fixture'})
            self.assertEqual(table.read_bytes(),previous)
            self.assertEqual([p.name for p in Path(td).iterdir()],['SCENARIOS.json'])

    def test_thesis_retains_findings_and_previous_record(self):
        with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(io.StringIO()),patch.object(thesis,'HERE',td):
            memory=Path(td)/'ops/chat/MEMORY.md';memory.parent.mkdir(parents=True)
            memory.write_text('Fixture record: one observed mutual benefit, one unresolved concern.')
            replies=[json.dumps({'claims':['fixture'],'contradictions':['concern'],'dated_examples':[]}),json.dumps({'claims':['fixture'],'contradictions':['concern']}),'# Thesis\nFixture only.\n## What is not known\nReplication.']
            for _ in range(2):
                with patch.object(thesis,'ask',side_effect=replies):self.assertEqual(thesis.main([]),0)
            written=list((Path(td)/'private').glob('THESIS_*.md'))[0].read_text()
            self.assertEqual(written.count('# Thesis'),2)
            self.assertIn('Chunk findings',written)

    def test_missing_sources_and_partial_failure_return_error(self):
        with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(io.StringIO()),patch.object(thesis,'HERE',td):
            self.assertEqual(thesis.main([]),2)
            self.assertFalse((Path(td)/'private').exists())
            memory=Path(td)/'ops/chat/MEMORY.md';memory.parent.mkdir(parents=True);memory.write_text('fixture')
            with patch.object(thesis,'ask',side_effect=RuntimeError('fixture model failure')):
                self.assertEqual(thesis.main([]),2)
            written=list((Path(td)/'private').glob('THESIS_*.md'))[0].read_text()
            self.assertIn('MISSING',written)

    def test_local_interface_rejects_nonobject_and_oversized_context(self):
        self.assertEqual(analysis.parse_object('```json\n{"evidence":"fixture"}\n```')['evidence'],'fixture')
        with self.assertRaises(ValueError):analysis.parse_object('[]')
        with patch('covenant_model.ask') as ask:
            with self.assertRaises(ValueError):analysis.complete('system','x'*25000)
            ask.assert_not_called()

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AnalysisTests))
    failed=len(result.failures)+len(result.errors)
    print('RAN: %d/%d passed' % (result.testsRun-failed,result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
