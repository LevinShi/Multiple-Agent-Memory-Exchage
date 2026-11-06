#!/usr/bin/env python3
"""Length-prefixed Chrome native host; only private capture operations, no shell."""
import json,struct,sys
from private_capture import Store,MAX_INPUT

def dispatch(store,m):
 op=m.get('op')
 if op=='select':return store.select(m['url'],m['account_scope'])
 if op=='capture':return store.ingest(m)
 if op=='check':return store.check(m.get('session'))
 if op=='pause':return store.pause()
 if op=='status':return store.status()
 raise ValueError('Unsupported operation')
def read_exact(stream,n):
 parts=b''
 while len(parts)<n:
  chunk=stream.read(n-len(parts))
  if not chunk:raise EOFError()
  parts+=chunk
 return parts

def serve(root,inp,out):
 store=Store(root)
 while True:
  try:
   header=read_exact(inp,4);length=struct.unpack('=I',header)[0]
   if not 0<length<=MAX_INPUT:return
   try:r=dispatch(store,json.loads(read_exact(inp,length)))
   except (ValueError,TypeError,KeyError,OSError):r={'status':'error','message':'Invalid request or unavailable private store'}
   data=json.dumps(r,ensure_ascii=False).encode();out.write(struct.pack('=I',len(data))+data);out.flush()
  except EOFError:return
if __name__=='__main__':serve(sys.argv[1],sys.stdin.buffer,sys.stdout.buffer)
