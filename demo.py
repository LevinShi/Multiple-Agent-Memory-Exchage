#!/usr/bin/env python3
"""Synthetic CLI relay in a temporary vault; no actual model/client calls."""
import json,subprocess,sys,tempfile
from pathlib import Path
from init_vault import initialize

def run_demo():
 with tempfile.TemporaryDirectory() as td:
  vault=initialize(Path(td)/'vault',demo=True)
  def call(command,actor='codex',run=None,extra=(),body=None,project='demo'):
   args=[sys.executable,str(vault/'gateway.py'),command,'--actor',actor,'--project',project]
   if run:args+=['--run',run]
   return subprocess.run(args+list(extra),input=body,text=True,capture_output=True)
  a=json.loads(call('begin').stdout)['run_id']
  saved=call('save',run=a,extra=('--task','example','--status','active','--source','synthetic-demo'),body='演示项目已完成需求分析；下一步制作草图。')
  assert saved.returncode==0,saved.stderr
  saved=json.loads(saved.stdout);assert saved['handoff_skipped']=='export_not_authorized'
  b=json.loads(call('begin',actor='cursor').stdout)
  assert b['recent_heads'][0]['id']==saved['id']
  result=call('save',actor='cursor',run=b['run_id'],extra=('--task','example','--status','done','--source','synthetic-demo','--supersedes',saved['id']),body='演示草图已完成，下一步等待用户评审。')
  assert result.returncode==0,result.stderr
  result=json.loads(result.stdout)
  back=call('show',run=a,extra=('--id',result['id']))
  assert json.loads(back.stdout)['id']==result['id']
  denied=call('begin',actor='unapproved');assert denied.returncode!=0 and denied.stdout==''
  unknown=call('begin',project='unknown');assert unknown.returncode!=0 and unknown.stdout==''
  evidence=json.loads(call('evidence',run=a).stdout);assert evidence['assessment']=='not_assessed'
  assert not (vault/'handoffs').exists()
  return {'synthetic_cli_relay':'passed','unapproved_actor':'denied','unknown_project':'denied','export':'disabled','real_client_acceptance':'not_tested_by_this_script'}
if __name__=='__main__':print(json.dumps(run_demo(),ensure_ascii=False,indent=2))
