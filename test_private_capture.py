import copy,hashlib,io,json,struct,tempfile,unittest,subprocess,sys
from pathlib import Path
from private_capture import Store,identity
from native_capture import serve,dispatch
from install_capture import install

URL='https://gemini.google.com/app/synthetic01'
ACCOUNT=hashlib.sha256(b'synthetic-account').hexdigest()
class CaptureTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'private';self.store=Store(self.root);self.store.initialize()
  self.selection=self.store.select(URL,ACCOUNT)
  self.packet={'op':'capture','session':self.selection['session'],'url':URL,'account_scope':ACCOUNT,'seq':1,'streaming':False,'complete':False,'messages':[{'id':'t1:user','role':'user','text':'Synthetic question'},{'id':'t1:assistant','role':'assistant','text':'Synthetic answer'}]}
 def tearDown(self):self.temp.cleanup()
 def test_duplicate_incremental_edit_partial_retention(self):
  a=self.store.ingest(self.packet);self.assertEqual(a['status'],'saved')
  self.packet['seq']=2;self.assertEqual(self.store.ingest(self.packet)['status'],'duplicate')
  self.packet['seq']=3;self.packet['messages'][1]['text']='Edited answer';self.store.ingest(self.packet)
  self.packet['seq']=4;self.packet['messages']=[{'id':'t2:user','role':'user','text':'Next question'},{'id':'t2:assistant','role':'assistant','text':'Next answer'}];self.store.ingest(self.packet)
  status=self.store.status()['conversations'][0];self.assertEqual(status['messages'],4);self.assertEqual(status['revisions'],3)
  state=json.loads((self.root/'state.json').read_text());self.assertEqual(len(state['blobs']),5)
  self.assertEqual(self.store.show(a['key'])['messages'][1]['text'],'Edited answer')
 def test_revert_to_known_snapshot_updates_current_without_new_revision(self):
  original=copy.deepcopy(self.packet);first=self.store.ingest(self.packet)
  self.packet['seq']=2;self.packet['messages'][1]['text']='Edited answer';self.store.ingest(self.packet)
  original['seq']=3;self.assertEqual(self.store.ingest(original)['status'],'duplicate')
  self.assertEqual(self.store.show(first['key'])['messages'][1]['text'],'Synthetic answer')
  self.assertEqual(self.store.status()['conversations'][0]['revisions'],2)
 def test_installer_conflict_leaves_existing_runtime_and_new_root_untouched(self):
  base=Path(self.temp.name);runtime=base/'runtime';manifests=base/'manifests'
  manifest=install(self.root,'a'*32,manifests,runtime)
  before={p.name:p.read_bytes() for p in runtime.iterdir()}
  newroot=base/'other-private'
  for ext in ['b'*32,'a'*32]:
   with self.assertRaises(ValueError):install(newroot,ext,manifests,runtime)
   self.assertFalse(newroot.exists())
   self.assertEqual(before,{p.name:p.read_bytes() for p in runtime.iterdir()})
  self.assertEqual(json.loads(manifest.read_text())['allowed_origins'],['chrome-extension://'+'a'*32+'/'])
 def test_pause_cancels_queued_and_old_sessions(self):
  self.store.pause();self.assertEqual(self.store.ingest(self.packet)['status'],'paused')
  self.store.select(URL,ACCOUNT);self.assertEqual(self.store.ingest(self.packet)['status'],'not_selected')
 def test_delete_prevents_refresh_until_explicit_restore(self):
  key=self.store.ingest(self.packet)['key'];self.store.delete(key)
  self.assertEqual(self.store.select(URL,ACCOUNT)['status'],'tombstoned')
  self.packet['seq']=2;self.assertEqual(self.store.ingest(self.packet)['status'],'tombstoned')
  with self.assertRaises(ValueError):self.store.show(key)
  self.store.restore(key);self.assertEqual(self.store.select(URL,ACCOUNT)['status'],'selected')
 def test_account_route_and_sequence(self):
  bad=copy.deepcopy(self.packet);bad['url']='https://gemini.google.com/app/other';self.assertEqual(self.store.ingest(bad)['status'],'not_selected')
  bad=copy.deepcopy(self.packet);bad['account_scope']='0'*64;self.assertEqual(self.store.ingest(bad)['status'],'not_selected')
  self.store.ingest(self.packet);self.assertEqual(self.store.ingest(self.packet)['status'],'stale')
  with self.assertRaises(ValueError):identity('https://evil.example/app/x',ACCOUNT)
 def test_empty_streaming_and_complete_snapshot_preserved(self):
  self.packet['complete']=True;first=self.store.ingest(self.packet)
  self.packet.update(seq=2,complete=False);self.packet['messages']=self.packet['messages'][1:]
  self.store.ingest(self.packet);self.assertEqual(self.store.show(first['key'])['last_complete'],first['revision'])
  self.packet.update(seq=3,streaming=True);self.assertEqual(self.store.ingest(self.packet)['status'],'streaming')
  self.packet.update(streaming=False,messages=[]);self.assertEqual(self.store.ingest(self.packet)['status'],'empty_or_oversized')
 def test_capacity_pauses_without_saving(self):
  c=json.loads((self.root/'control.json').read_text());c['max_bytes']=100;(self.root/'control.json').write_text(json.dumps(c))
  self.assertEqual(self.store.ingest(self.packet)['status'],'capacity_paused');self.assertTrue(self.store.status()['paused']);self.assertEqual(self.store.status()['conversations'],[])
 def test_corrupt_control_fails_closed(self):
  (self.root/'control.json').write_text('{}')
  with self.assertRaises(ValueError):self.store.ingest(self.packet)
 def test_native_protocol_and_no_share_or_shell(self):
  data=json.dumps(self.packet).encode();out=io.BytesIO();serve(self.root,io.BytesIO(struct.pack('=I',len(data))+data),out)
  raw=out.getvalue();result=json.loads(raw[4:]);self.assertEqual(result['status'],'saved');self.assertEqual(struct.unpack('=I',raw[:4])[0],len(raw)-4)
  for op in ['share','shell','read_file','show']:
   with self.assertRaises(ValueError):dispatch(self.store,{'op':op})
 def test_install_paths_with_spaces_and_permissions(self):
  m=install(self.root,'a'*32,Path(self.temp.name)/'manifest dir')
  self.assertEqual(json.loads(m.read_text())['allowed_origins'],['chrome-extension://'+'a'*32+'/'])
  self.assertEqual((self.root/'state.json').stat().st_mode&0o777,0o600)
  self.assertEqual(self.root.stat().st_mode&0o777,0o700)
 def test_late_history_insert_order(self):
  self.packet['messages']=[{'id':'t2:assistant','role':'assistant','text':'second'}];self.store.ingest(self.packet)
  self.packet['seq']=2;self.packet['messages'].insert(0,{'id':'t1:assistant','role':'assistant','text':'first'});self.store.ingest(self.packet)
  self.assertEqual([m['id'] for m in self.store.show(self.selection['key'])['messages']],['t1:assistant','t2:assistant'])
 def test_cli_import_and_duplicate(self):
  packet=Path(self.temp.name)/'sample.json';packet.write_text(json.dumps(self.packet))
  cmd=[sys.executable,str(Path(__file__).with_name('private_capture.py')),'--root',str(self.root),'import','--file',str(packet)]
  first=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(first.returncode,0,first.stderr);self.assertEqual(json.loads(first.stdout)['status'],'saved')
  self.packet['seq']=2;packet.write_text(json.dumps(self.packet))
  second=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(json.loads(second.stdout)['status'],'duplicate')
if __name__=='__main__':unittest.main()
