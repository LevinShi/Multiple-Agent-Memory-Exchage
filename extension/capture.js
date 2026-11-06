(()=>{
 if(globalThis.__lamCaptureInstalled)return;
 globalThis.__lamCaptureInstalled=true;
 let active=null,busy=false,last='',candidate='',stableSince=0,seq=0;
 const turnOwners=new Map();
 const badge=document.createElement('div');badge.id='lam-private-status';
 Object.assign(badge.style,{position:'fixed',bottom:'12px',right:'12px',zIndex:2147483647,background:'#17324d',color:'white',padding:'9px',borderRadius:'8px',font:'13px system-ui',maxWidth:'340px'});
 badge.textContent='私有采集：未启用';document.body.append(badge);
 const status=s=>{if(badge.textContent!==s)badge.textContent=s;};
 const sha=async s=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join('');
 function context(){
  if(location.origin!=='https://gemini.google.com' || !/^\/(?:u\/\d+\/)?(?:app\/[\w-]+|gem\/[\w-]+\/[\w-]+)$/.test(location.pathname))throw Error('请选择已生成链接的Gemini会话');
  const account=document.querySelector('a[href*="SignOutOptions"]')?.getAttribute('aria-label')||'';
  const email=account.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0]?.toLowerCase();
  if(!email)throw Error('无法确认当前账号，已停止');
  return {url:location.origin+location.pathname,email};
 }
 function extract(owner){
  const messages=[];
  for(const turn of document.querySelectorAll('.conversation-container[id]')){
   const id=turn.id;if(!/^[\w-]+$/.test(id))throw Error('轮次标识无效');
   if(turnOwners.has(id)&&turnOwners.get(id)!==owner)throw Error('页面还残留上一会话，请刷新后重新选择');
   turnOwners.set(id,owner);
   const q=turn.querySelector('user-query .query-text');
   const a=turn.querySelector('model-response .markdown');
   if(q){
    const clone=q.cloneNode(true);clone.querySelectorAll('.cdk-visually-hidden,[aria-hidden="true"],button').forEach(n=>n.remove());
    const text=clone.textContent.trim();if(text)messages.push({id:id+':user',role:'user',text});
   }
   if(a){const text=a.innerText.trim();if(text)messages.push({id:id+':assistant',role:'assistant',text});}
  }
  if(!messages.length || messages.at(-1).role!=='assistant')return null;
  const streaming=[...document.querySelectorAll('button')].some(b=>/stop response|stop generating|停止|停止答覆/i.test(b.getAttribute('aria-label')||''));
  if(streaming)return null;
  return messages;
 }
 async function tick(){
  if(!active||busy)return;
  busy=true;const current=active;
  try{
   const ctx=context();const account=await sha(ctx.email);
   if(current!==active)return;
   if(ctx.url!==current.url || account!==current.account){active=null;status('私有采集已停止：会话或账号改变，请重新选择');return;}
   const check=await chrome.runtime.sendMessage({op:'check',session:current.session});
   if(current!==active)return;
   if(check.status!=='active'){active=null;status('私有采集已停止：'+check.status);return;}
   const messages=extract(ctx.url+account);if(!messages){status('私有采集：等待正文/回答完成，未保存');return;}
   const signature=JSON.stringify(messages);
   if(signature!==candidate){candidate=signature;stableSince=Date.now();return;}
   if(Date.now()-stableSince<2500 || signature===last)return;
   const after=context();if(after.url!==ctx.url||after.email!==ctx.email||current!==active)return;
   const result=await chrome.runtime.sendMessage({op:'capture',session:current.session,url:ctx.url,account_scope:account,seq:++seq,messages,complete:false,streaming:false});
   if(current!==active)return;
   if(['saved','duplicate'].includes(result.status)){
    last=signature;status(`私有已保存 ${result.message_count} 条消息 · 历史完整性未确认 · 未共享`);
   }else{status('私有采集：'+result.status);if(['paused','not_selected','tombstoned','capacity_paused','revision_limit'].includes(result.status))active=null;}
  }catch(e){active=null;status('私有采集停止：'+e.message);}
  finally{busy=false;}
 }
 chrome.runtime.onMessage.addListener((m,sender,reply)=>{
  if(sender.id!==chrome.runtime.id||m.op!=='start')return;
  (async()=>{
   try{
    active=null;const ctx=context();const account=await sha(ctx.email);
    const r=await chrome.runtime.sendMessage({op:'select',url:ctx.url,account_scope:account});
    if(r.status!=='selected'){status('私有采集：'+r.status);reply(r);return;}
    active={url:ctx.url,account,session:r.session};seq=0;last='';candidate='';
    status('私有采集已启用：等待正文稳定');reply({status:'selected',message:'已启用当前会话。后续自动增量保存到私有库，不会自动共享。'});
   }catch(e){reply({status:'error',message:e.message});}
  })();return true;
 });
 // Local polling only; stability timer resets when extracted message text changes.
 setInterval(tick,1500);
})();
