"""Permission-first project context entry; local, no network, no identity claim."""
import argparse
import datetime as dt
import fcntl
import json
from pathlib import Path
import re
import sys
import uuid
import memory
from dashboard import atomic, observe_cli
ROOT = Path(__file__).resolve().parent

def stamp(): return dt.datetime.now(dt.timezone.utc).isoformat()
def scoped(root, project):
    rows = [r for r in memory.records(root) if r['project'] == project]
    old = {r['supersedes'] for r in rows if r.get('supersedes')}
    return sorted([r for r in rows if r['id'] not in old], key=lambda r:r['created_at'], reverse=True)

def execute(args):
    root=args.root.resolve()
    op='write' if args.command=='save' else 'read'
    # No records, rules, overview or run directory accessed before authorization.
    memory.permission(root,args.actor,args.project,op)
    runs=root/'runs';runs.mkdir(exist_ok=True)
    with (runs/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.command=='begin':
            rid=uuid.uuid4().hex
            state={'run_id':rid,'actor':args.actor,'project':args.project,'created_at':stamp(),
                   'events':[{'seq':1,'action':'authorize','operation':'read','outcome':'allowed','time':stamp()}]}
            path=runs/(rid+'.json')
        else:
            if not re.fullmatch('[a-f0-9]{32}', args.run or ''): raise PermissionError('begin required: missing/invalid run ID')
            path=runs/(args.run+'.json')
            if path.is_symlink(): raise PermissionError('Invalid run file')
            state=json.loads(path.read_text())
            if state['actor']!=args.actor or state['project']!=args.project: raise PermissionError('Run scope mismatch')
            if len(state['events'])>=128: raise ValueError('Run event limit reached; begin a new run')
        if args.command=='begin':
            result={'run_id':rid,'project':args.project,'actor':args.actor,'authorization':'read allowed',
                    'rules':(root/'RULES.md').read_text(),
                    'overview':(root/'OVERVIEW.md').read_text() if args.project=='shared-memory' and (root/'OVERVIEW.md').exists() else None,
                    'recent_heads':scoped(root,args.project)[:8],
                    'next':'Use gateway search/show/save/evidence with this --run, --actor and --project. Do not read raw library files. Save body through stdin. Evidence does not assert full acceptance.'}
        elif args.command=='search':
            terms=args.query.casefold().split()
            result=[r for r in scoped(root,args.project) if all(t in json.dumps(r,ensure_ascii=False).casefold() for t in terms)][:20]
        elif args.command=='show':
            result=next((r for r in memory.records(root) if r['project']==args.project and r['id']==args.id),None)
            if result is None: raise ValueError('Record not found in authorized project')
        elif args.command=='save':
            result=memory.append(root,args.actor,args.project,args.task,args.kind,args.status,args.source,sys.stdin.read(65537),args.supersedes)
        else:
            result={'run_id':state['run_id'],'observed_events':list(state['events']),
                    'assessment':'not_assessed','raw_file_access':'not_observable_by_gateway',
                    'review_required':'Compare actual client tool trace; claims inside records are not evidence. No automatic all-pass.'}
        event={'seq':len(state['events'])+1,'action':args.command,'operation':op,'authorization':'allowed','outcome':'success','time':stamp()}
        if args.command=='save': event['record_id']=result['id']
        state['events'].append(event)
        try: atomic(path,json.dumps(state,ensure_ascii=False,indent=2))
        except OSError:
            if args.command!='save': raise
            result['evidence_warning']='Record saved; run evidence persistence failed'
        # Automatic run creation bounded; retain most recent 100 local run summaries.
        if args.command=='begin':
            for old in sorted(runs.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[100:]: old.unlink()
    command={'begin':'brief','save':'add','evidence':'show'}.get(args.command,args.command)
    try: observe_cli(['--root',str(root),command,'--actor',args.actor,'--project',args.project],root,'success')
    except Exception:
        print('Status update failed; operation result is authoritative.',file=sys.stderr)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['begin','search','show','save','evidence']:
        c=sub.add_parser(name);c.add_argument('--actor',required=True);c.add_argument('--project',required=True)
        if name!='begin': c.add_argument('--run',required=True)
        if name=='search': c.add_argument('query')
        if name=='show': c.add_argument('--id',required=True)
        if name=='save':
            c.add_argument('--task',required=True);c.add_argument('--source',required=True)
            c.add_argument('--kind',choices=['progress','decision','finding','correction'],default='progress')
            c.add_argument('--status',choices=['active','done','blocked','proposed','cancelled'],required=True)
            c.add_argument('--supersedes',default='')
    args=p.parse_args()
    try: result=execute(args)
    except (OSError,ValueError,KeyError,TypeError) as error:
        try: observe_cli(['--root',str(args.root),{'save':'add','begin':'brief'}.get(args.command,args.command),'--actor',args.actor,'--project',args.project],args.root,'denied' if isinstance(error,PermissionError) else 'error')
        except Exception: pass
        sys.exit(str(error))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
