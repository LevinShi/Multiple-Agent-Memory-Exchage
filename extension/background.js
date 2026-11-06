const HOST='ai.local_agent_memory.capture';
chrome.runtime.onMessage.addListener((m,sender,respond)=>{
  if(sender.id!==chrome.runtime.id) return;
  const content=!!sender.tab;
  if(content && !['select','check','capture','pause'].includes(m.op))return;
  if(content && !sender.url?.startsWith('https://gemini.google.com/'))return;
  // Scope checks in the native host bind the session to account + exact URL.
  chrome.runtime.sendNativeMessage(HOST,m).then(respond).catch(e=>respond({status:'bridge_error',message:e.message}));
  return true;
});
