const label=document.querySelector('#status');
const labels={paused:'已暂停：不再保存新内容',tombstoned:'这条会话已停采并隐藏；需要明确恢复后才能重新采集',bridge_error:'本地连接失败，请检查桥接安装',selected:'已选择当前会话'};
const describe=r=>r.message||labels[r.status]||r.status;
document.querySelector('#start').onclick=async()=>{
 try{
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  if(!tab.url?.startsWith('https://gemini.google.com/'))throw Error('请先打开 Gemini 中的一条具体会话');
  await chrome.scripting.executeScript({target:{tabId:tab.id},files:['capture.js']});
  const result=await chrome.tabs.sendMessage(tab.id,{op:'start'});
  label.textContent=describe(result)||'未启动';
 }catch(e){label.textContent=String(e.message);}
};
document.querySelector('#pause').onclick=async()=>{
 const r=await chrome.runtime.sendMessage({op:'pause'});label.textContent=describe(r);
};
