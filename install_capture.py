#!/usr/bin/env python3
"""Install local Native Messaging bridge for a specific Chrome extension ID."""
import argparse,json,os,re,shlex,sys,shutil
from pathlib import Path
from private_capture import Store,atomic
SOURCE=Path(__file__).resolve().parent
HOST='ai.local_agent_memory.capture'
def install(root,extension_id,manifest_dir,runtime_dir=None):
 if not re.fullmatch('[a-p]{32}',extension_id):raise ValueError('Invalid Chrome extension ID')
 root=root.expanduser().resolve()
 runtime=Path(runtime_dir).expanduser().resolve() if runtime_dir else root/'runtime'
 launcher=runtime/'native-host.sh'
 script='#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(runtime/'native_capture.py'))+' '+shlex.quote(str(root))+' "$@"\n'
 path=manifest_dir/(HOST+'.json')
 config={'name':HOST,'description':'Local Agent Memory private capture only','path':str(launcher),'type':'stdio','allowed_origins':['chrome-extension://'+extension_id+'/']}
 # Validate ownership/configuration before changing any store or runtime files.
 if path.exists() and json.loads(path.read_text())!=config:
  raise ValueError('Existing host differs; refusing overwrite')
 if launcher.exists() and launcher.read_text()!=script:
  raise ValueError('Existing runtime targets another store or interpreter; refusing overwrite')
 if not root.exists():Store(root).initialize()
 else:Store(root).status()
 runtime.mkdir(parents=True,exist_ok=True);os.chmod(runtime,0o700)
 for name in ('native_capture.py','private_capture.py'):
  shutil.copyfile(SOURCE/name,runtime/name);os.chmod(runtime/name,0o600)
 launcher.write_text(script);os.chmod(launcher,0o700)
 manifest_dir.mkdir(parents=True,exist_ok=True)
 atomic(path,config)
 return path
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--extension-id',required=True)
 default=Path.home()/('Library/Application Support/Google/Chrome/NativeMessagingHosts' if sys.platform=='darwin' else '.config/google-chrome/NativeMessagingHosts')
 p.add_argument('--manifest-dir',type=Path,default=default)
 p.add_argument('--runtime-dir',type=Path,default=Path.home()/('Library/Application Support/LocalAgentMemory/runtime' if sys.platform=='darwin' else '.local/share/local-agent-memory/runtime'))
 a=p.parse_args()
 print(install(a.root,a.extension_id,a.manifest_dir,a.runtime_dir))
