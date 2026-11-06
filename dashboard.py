"""Local owner-facing metadata snapshot. No server, network, or record bodies."""
import datetime as dt
import fcntl
import html
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent
ACTORS = ('codex', 'cursor', 'zcode', 'minimax', 'kimi', 'kimi-code')
COMMANDS = ('brief', 'status', 'search', 'recent', 'show', 'add', 'export', 'handoff')

def atomic(path, content):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.status-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def render(root):
    policy = json.loads((root / 'permissions.json').read_text())
    events = []
    for file in (root / 'activity').glob('*.json'):
        try: events.append(json.loads(file.read_text()))
        except (ValueError, OSError): pass
    esc = lambda x: html.escape(str(x), quote=True)
    rows = []
    for project, item in sorted(policy['projects'].items()):
        grants = item.get('grants', {}) if item.get('status') == 'approved' else {}
        mode = '独占' if item.get('access_mode') == 'exclusive' else '共享' if grants else '未授权'
        recent = sorted((e for e in events if e['project'] == project), key=lambda e:e['time'], reverse=True)
        last = lambda commands: next((e['time']+' · '+e['actor'] for e in recent if e['command'] in commands and e['outcome']=='success'), '未知（尚未观测）')
        failure = next((e['time']+' · '+e['actor']+' / '+e['command']+' · '+e['outcome'] for e in recent if e['outcome']!='success'), '暂无已记录失败')
        cells = [project, mode, '; '.join(a+': '+','.join(ops) for a,ops in grants.items()), last(('brief','status','search','recent','show')), last(('add',)), failure]
        rows.append('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in cells)+'</tr>')
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>本地记忆状态</title>
<style>body{font:15px system-ui;background:#f5f6fa;color:#182238;padding:30px}h1{font-size:26px}p{max-width:1000px;line-height:1.7}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:14px;border-bottom:1px solid #ddd;vertical-align:top;word-break:break-word}th{background:#e6edf7}input{padding:12px;width:340px;margin:15px 0}small{color:#526175}</style>
<h1>本地共享记忆 · 用户管理视图</h1><p>权限、已观测的CLI结果与更新时间。此页不包含记忆正文，不证明客户端已接入或其他Agent已收到内容。来源定位：使用获授权的 search，再用 show --id 查询原记录的 source、file 与 supersedes。</p>
<p>本页是快照。读写命令完成后自动重新生成，浏览器需刷新；也可运行 python3 dashboard.py。查询词、正文及原始错误信息不写入状态数据。每组操作分别保留最近成功与失败结果，失败会标为 denied 或 error；详细原因见当次CLI错误。</p><small>生成时间（UTC）：'''+esc(now)+'''</small><br><input id="filter" placeholder="筛选项目、Agent或状态" aria-label="筛选项目"><table><thead><tr><th>项目</th><th>模式</th><th>权限</th><th>最近成功读取</th><th>最近成功写入</th><th>最近已记录失败</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table><script>document.getElementById('filter').addEventListener('input',e=>{for(const row of document.querySelectorAll('tbody tr'))row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase())});</script>'''
    atomic(root/'dashboard.html', page)

def observe_cli(argv, default_root, outcome):
    def option(name, default=None):
        if name in argv:
            i=argv.index(name)
            return argv[i+1] if i+1<len(argv) else default
        return default
    root=Path(option('--root',str(default_root))).resolve()
    command=next((x for x in argv if x in COMMANDS), None)
    actor,project=option('--actor'),option('--project')
    if command is None or actor not in ACTORS or not project: return
    policy=json.loads((root/'permissions.json').read_text())
    if project not in policy.get('projects',{}): return
    directory=root/'activity';directory.mkdir(exist_ok=True)
    # Fixed filename avoids unbounded event growth; separate lock serializes renders.
    with (directory/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        event=dict(time=dt.datetime.now(dt.timezone.utc).isoformat(),project=project,actor=actor,command=command,outcome=outcome)
        import hashlib
        key=hashlib.sha256((project+'\0'+actor+'\0'+command+'\0'+outcome).encode()).hexdigest()
        atomic(directory/(key+'.json'),json.dumps(event,ensure_ascii=False))
        render(root)

if __name__=='__main__':
    render(ROOT)
    print(ROOT/'dashboard.html')
