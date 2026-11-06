import json,subprocess,sys,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).with_name('gateway.py')
class GatewayTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.policy={'version':1,'default':'deny','projects':{'shared-memory':{'status':'approved','approval_source':'fixture','grants':{'minimax':['read','write'],'codex':['read','write']}}}}
  (self.root/'permissions.json').write_text(json.dumps(self.policy));(self.root/'RULES.md').write_text('RULE_SENTINEL');(self.root/'OVERVIEW.md').write_text('OVERVIEW_SENTINEL')
 def tearDown(self): self.temp.cleanup()
 def call(self,command,*args,actor='minimax',project='shared-memory',body=None):
  return subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),command,'--actor',actor,'--project',project,*args],input=body,text=True,capture_output=True)
 def test_denied_before_context_reads(self):
  (self.root/'RULES.md').unlink()
  r=self.call('begin',actor='kimi');self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertIn('未授权',r.stderr);self.assertFalse((self.root/'runs').exists())
 def test_begin_and_scoped_run_required(self):
  r=json.loads(self.call('begin').stdout);rid=r['run_id'];self.assertEqual(r['overview'],'OVERVIEW_SENTINEL')
  self.assertNotEqual(self.call('search','x','--run',rid,actor='codex').returncode,0)
  self.assertNotEqual(self.call('search','x','--run','../outside').returncode,0)
  self.assertNotEqual(self.call('search','x','--run',rid,project='unknown').returncode,0)
 def test_save_evidence_and_revocation(self):
  rid=json.loads(self.call('begin').stdout)['run_id']
  r=self.call('save','--run',rid,'--task','pilot','--status','done','--source','fixture',body='PRIVATE_SAMPLE')
  saved=json.loads(r.stdout);self.assertEqual(saved['handoff_skipped'],'export_not_authorized')
  evidence=json.loads(self.call('evidence','--run',rid).stdout)
  self.assertEqual(evidence['assessment'],'not_assessed');self.assertEqual(evidence['observed_events'][0]['action'],'authorize')
  self.assertNotIn('PRIVATE_SAMPLE',json.dumps(evidence));self.assertEqual(evidence['observed_events'][-1]['record_id'],saved['id'])
  self.policy['projects']['shared-memory']['grants']={};(self.root/'permissions.json').write_text(json.dumps(self.policy))
  self.assertNotEqual(self.call('show','--run',rid,'--id',saved['id']).returncode,0)
if __name__=='__main__':unittest.main()
