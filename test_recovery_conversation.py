"""Behavioral regressions for unattended repairs and conversational context."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import covenant_heal as heal
import covenant_highway as highway
import covenant_unified_v8 as core
import covenant_model as model


class RecoveryTests(unittest.TestCase):
    def test_unreadable_after_repair_is_not_fixed(self):
        for after in ({}, {'fault': {'state': 'UNKNOWN', 'measured': {}}}):
            with self.subTest(after=after), tempfile.TemporaryDirectory() as td:
                with patch('covenant_pause.paused', return_value=(False, '')), patch('covenant_immune.state', return_value={}):
                    out=heal.heal(ledger_path=str(Path(td)/'heal.jsonl'),
                                  sense=unittest.mock.Mock(side_effect=[{'fault':{'state':'PRESENT'}},after]),
                                  run=lambda **kw:([],[]))
                self.assertFalse(out['healthy'])
                self.assertEqual(out['fixed'],[])
                self.assertEqual(out['unverified'][0]['condition'],'fault')
                self.assertNotIn('nothing was wrong',out['summary'])

    def test_unknown_only_and_new_fault_remain_visible(self):
        with tempfile.TemporaryDirectory() as td, patch('covenant_pause.paused',return_value=(False,'')), patch('covenant_immune.state',return_value={}):
            out=heal.heal(ledger_path=str(Path(td)/'heal.jsonl'),
                          sense=unittest.mock.Mock(side_effect=[{'a':{'state':'UNKNOWN'}}, {'a':{'state':'UNKNOWN'},'b':{'state':'PRESENT'}}]),run=lambda **kw:([],[]))
            self.assertFalse(out['healthy'])
            self.assertEqual(out['still_needs_a_person'][0]['condition'],'b')

    def test_unattended_pass_continues_after_one_remedy_raises(self):
        with tempfile.TemporaryDirectory() as td:
            repaired=Path(td)/'repaired'
            def fail(measured,dry_run=False):raise RuntimeError('fixture repair failed')
            def fix(measured,dry_run=False):
                if not dry_run:repaired.write_text('recovered')
                return True,'wrote reversible fixture marker'
            detectors={'a_broken':lambda **kw:{'state':'PRESENT','measured':{}},
                       'b_fixable':lambda **kw:{'state':'ABSENT' if repaired.exists() else 'PRESENT','measured':{}}}
            def remedy(fn,condition):return {'fn':fn,'klass':highway.AUTO_REVERSIBLE,'for':[condition], 'kind':'stateless','touches':[], 'benefit':{'gains':'restore fixture','cost':'temporary file'}}
            with patch.dict(highway.DETECTORS,detectors,clear=True), patch.dict(highway.REMEDIES,{'broken':remedy(fail,'a_broken'),'working':remedy(fix,'b_fixable')},clear=True), patch.object(highway,'save_last_sense'), patch.object(highway,'_operator_choices',return_value={}), patch('covenant_pause.paused',return_value=(False,'')):
                alerts,infos=highway.run_once(ledger=str(Path(td)/'ledger.jsonl'),cooldown_s=0,health={})
            self.assertTrue(repaired.exists())
            self.assertTrue(any('error' in a for a in alerts))
            self.assertTrue(any('fixed' in i for i in infos))

    def test_history_rejects_privileged_roles_and_keeps_recent_correction(self):
        self.assertEqual(core.conversation_context([{'role':'system','content':'bad'},{'role':'assistant','content':'a'}]),[])
        text='opening '+('x'*5000)+' corrected preference: shorter answers'
        context=core.conversation_context([{'role':'user','content':text},{'role':'assistant','content':'understood'}])
        self.assertIn('corrected preference: shorter answers',context[0]['content'])
        self.assertLessEqual(sum(len(x['content']) for x in context),core.AGENT_HISTORY_BUDGET)

    def test_malformed_log_row_does_not_erase_good_context(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'ask.jsonl'
            p.write_text('[]\nnull\n'+json.dumps({'kind':'agent','from':'phone','text':'remember this','answer':'yes'})+'\n')
            self.assertEqual(len(core.agent_history(str(p),'phone')),2)

    def test_muse_adds_capacity_without_replacing_smaller_models(self):
        with tempfile.TemporaryDirectory() as td, patch.object(model,'MODELS',td):
            for name in (model.MUSE_FILE,model.CANDIDATES[-1][0]): (Path(td)/name).write_bytes(b'fixture')
            with patch.object(model,'_runtime_supports_muse',return_value=True),patch.object(model,'free_gb',return_value=25):
                self.assertEqual(model.pick_model()[1],model.MUSE_FILE)
            with patch.object(model,'_runtime_supports_muse',return_value=True),patch.object(model,'free_gb',return_value=4):
                self.assertEqual(model.pick_model()[1],model.CANDIDATES[-1][0])
            with patch.object(model,'_runtime_supports_muse',return_value=False),patch.object(model,'free_gb',return_value=25):
                self.assertEqual(model.pick_model()[1],model.CANDIDATES[-1][0])
            with patch.object(model,'_runtime_supports_muse',return_value=True),patch.object(model,'free_gb',return_value=None):
                self.assertNotEqual(model.pick_model()[1],model.MUSE_FILE)


if __name__ == '__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryTests))
    failed=len(result.failures)+len(result.errors)
    print('RCV: %d/%d passed' % (result.testsRun-failed,result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
