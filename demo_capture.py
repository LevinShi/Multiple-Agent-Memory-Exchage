#!/usr/bin/env python3
"""Offline synthetic private capture; no browser, installation or network."""
import copy, hashlib, json, tempfile
from pathlib import Path
from private_capture import Store

def run_demo():
 with tempfile.TemporaryDirectory(prefix='capture demo ') as folder:
  store=Store(Path(folder)/'private');store.initialize()
  assert store.status()['paused']
  url='https://gemini.google.com/app/offline-demo'
  selected=store.select(url,hashlib.sha256(b'offline-demo').hexdigest())
  packet=dict(url=url,account_scope=hashlib.sha256(b'offline-demo').hexdigest(),session=selected['session'],seq=1,streaming=False,complete=False,messages=[dict(id='one:assistant',role='assistant',text='Synthetic original')])
  first=store.ingest(packet);original=copy.deepcopy(packet)
  packet['seq']=2;packet['messages'][0]['text']='Synthetic edit';store.ingest(packet)
  original['seq']=3;assert store.ingest(original)['status']=='duplicate'
  assert store.show(first['key'])['messages'][0]['text']=='Synthetic original'
  store.pause();original['seq']=4;assert store.ingest(original)['status']=='paused'
  store.delete(first['key']);assert store.select(url,packet['account_scope'])['status']=='tombstoned'
  return dict(offline_private_capture='passed',revert_preserves_history=True,pause_blocks_writes=True,tombstone_blocks_reselection=True,shared_records_written=0,browser_started=False)
if __name__=='__main__':print(json.dumps(run_demo(),indent=2))
