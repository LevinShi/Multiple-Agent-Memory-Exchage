#!/usr/bin/env python3
"""Private Gemini import store. No network and no shared-memory writes."""
import argparse, contextlib, fcntl, hashlib, json, os, re, secrets, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlsplit
MAX_INPUT=2*1024*1024
MAX_STORE=50*1024*1024

def encoded(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def digest(value): return hashlib.sha256(encoded(value)).hexdigest()
def identity(url, account):
 u=urlsplit(url)
 if u.scheme!='https' or u.netloc!='gemini.google.com' or u.query or u.fragment: raise ValueError('Only canonical Gemini conversation URLs accepted')
 m=re.fullmatch(r'/(?:u/\d+/)?(?:app/([a-zA-Z0-9_-]+)|gem/[a-zA-Z0-9_-]+/([a-zA-Z0-9_-]+))',u.path)
 if not m or not re.fullmatch('[a-f0-9]{64}',account):raise ValueError('Missing stable conversation/account identity')
 cid=m.group(1) or m.group(2)
 return digest(['gemini',account,cid])

def atomic(path,value):
 data=encoded(value)
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.pending-')
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

class Store:
 def __init__(self,root): self.root=Path(root).expanduser().resolve()
 def initialize(self):
  self.root.mkdir(mode=0o700,parents=True,exist_ok=False);os.chmod(self.root,0o700)
  atomic(self.root/'control.json',{'version':1,'paused':True,'max_bytes':MAX_STORE})
  atomic(self.root/'state.json',{'version':1,'sessions':{},'conversations':{},'blobs':{},'tombstones':{}})
  (self.root/'.gitignore').write_text('*\n')
 @contextlib.contextmanager
 def locked(self):
  if not self.root.is_dir():raise ValueError('Private store is not initialized')
  with (self.root/'.lock').open('a') as f:
   os.chmod(self.root/'.lock',0o600);fcntl.flock(f,fcntl.LOCK_EX)
   c=json.loads((self.root/'control.json').read_text());s=json.loads((self.root/'state.json').read_text())
   if c.get('version')!=1 or not isinstance(c.get('paused'),bool):raise ValueError('Invalid control; fail closed')
   yield c,s
 def pause(self):
  with self.locked() as (c,s):
   c['paused']=True;atomic(self.root/'control.json',c)
   s['sessions']={};atomic(self.root/'state.json',s)
  return {'status':'paused'}
 def select(self,url,account):
  key=identity(url,account)
  with self.locked() as (c,s):
   if key in s['tombstones']:return {'status':'tombstoned','key':key}
   token=secrets.token_hex(32)
   # One explicit selection at a time. Old browser requests cannot resume later.
   s['sessions']={token:{'key':key,'url':url,'account_scope':account,'seq':0,'expires':time.time()+12*3600}}
   atomic(self.root/'state.json',s)
   c['paused']=False;atomic(self.root/'control.json',c)
   return {'status':'selected','key':key,'session':token}
 def check(self,token):
  with self.locked() as (c,s):
   ses=s['sessions'].get(token)
   status='paused' if c['paused'] else 'active' if ses and ses['expires']>time.time() else 'not_selected'
   return {'status':status}
 def ingest(self,p):
  if len(encoded(p))>MAX_INPUT:raise ValueError('Input too large')
  with self.locked() as (c,s):
   if c['paused']:return {'status':'paused'}
   key=identity(p['url'],p['account_scope'])
   if key in s['tombstones']:return {'status':'tombstoned','key':key}
   ses=s['sessions'].get(p.get('session'))
   if not ses or ses['key']!=key or ses['url']!=p['url'] or ses['expires']<=time.time():return {'status':'not_selected'}
   seq=p.get('seq')
   if type(seq)!=int or seq<=ses['seq']:return {'status':'stale'}
   if p.get('complete') not in (True,False) or type(p.get('complete'))!=bool:raise ValueError('complete must be boolean')
   if p.get('streaming') is not False:return {'status':'streaming'}
   messages=p.get('messages')
   if not isinstance(messages,list) or not messages or len(messages)>2000:return {'status':'empty_or_oversized'}
   incoming={};ids=[]
   for msg in messages:
    mid=msg.get('id');role=msg.get('role');text=msg.get('text')
    if not isinstance(mid,str) or not re.fullmatch(r'[a-zA-Z0-9_:-]{1,160}',mid) or mid in incoming:raise ValueError('Invalid or duplicate message ID')
    if role not in ('user','assistant') or not isinstance(text,str) or not text.strip() or len(text.encode())>65536:raise ValueError('Invalid message')
    item={'id':mid,'role':role,'text':text.replace('\r\n','\n').strip()}
    h=digest(item);incoming[mid]=h;ids.append(mid);s['blobs'][h]=item
   conv=s['conversations'].setdefault(key,{'url':p['url'],'account_scope':p['account_scope'],'messages':{},'order':[],'revisions':{},'last_complete':None})
   # Preserve all previously observed messages when the page shows only a window.
   existing=[mid for mid in ids if mid in conv['order']]
   if [mid for mid in conv['order'] if mid in existing]!=existing:return {'status':'order_conflict'}
   order=conv['order'][:]
   for index,mid in enumerate(ids):
    if mid not in order:
     next_known=next((x for x in ids[index+1:] if x in order),None)
     if next_known:order.insert(order.index(next_known),mid)
     else:order.append(mid)
   revision=digest({'ids':ids,'refs':[incoming[x] for x in ids],'complete':p['complete']})
   known_revision=revision in conv['revisions']
   if not known_revision and len(conv['revisions'])>=5000:return {'status':'revision_limit'}
   conv['messages'].update(incoming);conv['order']=order
   if not known_revision:
    conv['revisions'][revision]={'time':time.time(),'refs':[incoming[x] for x in ids],'complete':p['complete']}
   if p['complete']:conv['last_complete']=revision
   conv['last_revision']=revision;ses['seq']=seq
   if len(encoded(s))>min(int(c['max_bytes']),MAX_STORE):
    c['paused']=True;atomic(self.root/'control.json',c);return {'status':'capacity_paused'}
   atomic(self.root/'state.json',s)
   return {'status':'duplicate' if known_revision else 'saved','key':key,'revision':revision,'message_count':len(order),'observed_count':len(ids),'complete':p['complete'],'bytes':len(encoded(s))}
 def delete(self,key):
  with self.locked() as (c,s):
   if key not in s['conversations']:raise ValueError('Unknown conversation')
   s['tombstones'][key]={'time':time.time()};s['sessions']={}
   atomic(self.root/'state.json',s)
  return {'status':'tombstoned','key':key,'original_retained':True}
 def restore(self,key):
  with self.locked() as (c,s):
   if key not in s['tombstones']:raise ValueError('Not tombstoned')
   del s['tombstones'][key];atomic(self.root/'state.json',s)
  return {'status':'restored_requires_new_selection'}
 def status(self):
  with self.locked() as (c,s):
   return {'paused':c['paused'],'bytes':(self.root/'state.json').stat().st_size,'max_bytes':c['max_bytes'],
    'conversations':[{'key':k,'messages':len(v['order']),'revisions':len(v['revisions']),'deleted':k in s['tombstones'],'last_complete':v['last_complete']} for k,v in s['conversations'].items()]}
 def show(self,key):
  with self.locked() as (c,s):
   if key in s['tombstones']:raise ValueError('Deleted; explicitly restore to view')
   v=s['conversations'][key]
   return {'url':v['url'],'messages':[s['blobs'][v['messages'][i]] for i in v['order']], 'last_complete':v['last_complete']}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
 sub=p.add_subparsers(dest='op',required=True)
 for op in ['init','pause','status']:sub.add_parser(op)
 x=sub.add_parser('select');x.add_argument('--url',required=True);x.add_argument('--account-scope',required=True)
 x=sub.add_parser('import');x.add_argument('--file',type=Path,required=True)
 for op in ['show','delete','restore']:
  x=sub.add_parser(op);x.add_argument('--key',required=True)
 a=p.parse_args();s=Store(a.root)
 try:
  if a.op=='init':s.initialize();r={'status':'initialized_paused'}
  elif a.op=='select':r=s.select(a.url,a.account_scope)
  elif a.op=='import':
   if a.file.stat().st_size>MAX_INPUT:raise ValueError('Input too large')
   r=s.ingest(json.loads(a.file.read_text()))
  elif a.op in ('show','delete','restore'):r=getattr(s,a.op)(a.key)
  else:r=getattr(s,a.op)()
  print(json.dumps(r,ensure_ascii=False,indent=2))
 except (ValueError,OSError,KeyError,TypeError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
