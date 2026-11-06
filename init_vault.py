#!/usr/bin/env python3
"""Create a new, private local vault; never overwrite existing directories."""
import argparse,json,os,shutil
from pathlib import Path
SOURCE=Path(__file__).resolve().parent

def initialize(target,demo=False):
 target=target.expanduser().resolve()
 target.mkdir(mode=0o700,parents=True,exist_ok=False)
 os.chmod(target,0o700)
 for name in ('memory.py','gateway.py','dashboard.py','RULES.md'):
  shutil.copyfile(SOURCE/name,target/name)
 policy={'version':1,'default':'deny','projects':{}}
 if demo:
  policy['projects']['demo']={'status':'approved','approval_source':'Owner explicitly initialized synthetic demo',
   'access_mode':'shared','grants':{'codex':['read','write'],'cursor':['read','write'],'zcode':['read','write'],'minimax':['read','write']}}
 (target/'permissions.json').write_text(json.dumps(policy,indent=2)+'\n',encoding='utf-8')
 (target/'.gitignore').write_text('*\n',encoding='utf-8')
 template=(SOURCE/'ENTRY.template.md').read_text(encoding='utf-8')
 for actor in ('codex','cursor','zcode','minimax'):
  (target/f'ENTRY-{actor}.md').write_text(template.replace('{{GATEWAY}}',str(target/'gateway.py')).replace('{{ACTOR}}',actor),encoding='utf-8')
 return target

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('target',type=Path)
 p.add_argument('--demo',action='store_true',help='Explicitly authorize four actors on synthetic demo only; no export')
 a=p.parse_args()
 try: print(initialize(a.target,a.demo))
 except FileExistsError: p.exit(1,'Target exists; refusing to overwrite. Choose a NEW directory.\n')
