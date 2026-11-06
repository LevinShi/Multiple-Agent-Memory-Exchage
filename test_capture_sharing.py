import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from init_vault import initialize
from private_capture import Store
from share_summary import share
class SharingTest(unittest.TestCase):
 def test_private_isolation_and_approved_summary_only(self):
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);vault=initialize(base/'shared',True);s=Store(base/'private');s.initialize()
   url='https://gemini.google.com/app/synthetic';account=hashlib.sha256(b'test').hexdigest();sel=s.select(url,account)
   s.ingest({'url':url,'account_scope':account,'session':sel['session'],'seq':1,'complete':False,'streaming':False,'messages':[{'id':'one','role':'user','text':'PRIVATE_ONLY_SENTINEL'}]})
   g=vault/'gateway.py'
   def call(op,*args):return subprocess.run([sys.executable,str(g),op,'--actor','codex','--project','demo',*args],capture_output=True,text=True)
   run=json.loads(call('begin').stdout)['run_id'];self.assertEqual(json.loads(call('search','PRIVATE_ONLY_SENTINEL','--run',run).stdout),[])
   draft=base/'summary.txt';draft.write_text('Approved minimal summary')
   with self.assertRaises(ValueError):share(s.root,sel['key'],g,'codex','demo',run,'capture',draft)
   with self.assertRaises(PermissionError):share(s.root,sel['key'],g,'codex','unknown',run,'capture',draft,True)
   result=share(s.root,sel['key'],g,'codex','demo',run,'capture',draft,True)
   self.assertEqual(result['handoff_skipped'],'export_not_authorized')
   found=json.loads(call('show','--run',run,'--id',result['id']).stdout)
   self.assertEqual(found['body'],'Approved minimal summary');self.assertNotIn('PRIVATE_ONLY_SENTINEL',json.dumps(found))
if __name__=='__main__':unittest.main()
