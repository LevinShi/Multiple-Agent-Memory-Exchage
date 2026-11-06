#!/usr/bin/env python3
"""Explicit owner-approved summary transfer; native browser bridge cannot call this."""
import argparse,json,subprocess,sys
from pathlib import Path
from private_capture import Store

def share(private_root,key,gateway,actor,project,run,task,summary_file,confirmed=False):
 if not confirmed:raise ValueError('Explicit approval of summary and target project required')
 # Check shared run authorization before reading any private content or draft.
 base=[sys.executable,str(gateway)]
 scope=['--actor',actor,'--project',project,'--run',run]
 check=subprocess.run(base+['evidence']+scope,capture_output=True,text=True)
 if check.returncode:raise PermissionError(check.stderr.strip())
 if summary_file.stat().st_size>65536:raise ValueError('Summary too large')
 summary=summary_file.read_text(encoding='utf-8')
 # Validate selected source is not deleted. Never copy its messages into the ledger.
 source=Store(private_root).show(key)['url']
 p=subprocess.run(base+['save']+scope+['--task',task,'--status','done','--source',source],input=summary,text=True,capture_output=True)
 if p.returncode:raise PermissionError(p.stderr.strip())
 return json.loads(p.stdout)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['key','actor','project','run','task']:p.add_argument('--'+name,required=True)
 for name in ['private-root','gateway','summary-file']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--confirm-share',action='store_true');a=p.parse_args()
 try:print(json.dumps(share(a.private_root,a.key,a.gateway,a.actor,a.project,a.run,a.task,a.summary_file,a.confirm_share),ensure_ascii=False,indent=2))
 except (ValueError,OSError,KeyError) as e:p.exit(1,str(e)+'\n')
