from pathlib import Path
import hashlib,json,os,re,subprocess
assert os.environ.get('CODESPACE_NAME')=='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
state=Path('/workspaces/.diana-luna-state')
def safe(text):
    text=re.sub(r'(?i)(bearer\s+)[A-Za-z0-9_.~+/-]+',r'\1[REDACTED]',text)
    text=re.sub(r'(github_pat_|gh[pousr]_|sk-)[A-Za-z0-9_-]{12,}','[REDACTED]',text)
    text=re.sub(r'(?i)([\"\x27]?(?:access_token|refresh_token|id_token|password)[\"\x27]?\s*[:=]\s*[\"\x27])[^\"\x27]+',r'\1[REDACTED]',text)
    return text[-7000:]
for name in ['v3-sandbox-probe.log','v3-appserver-preflight-stderr.log','v3-staging-command-error.log']:
    p=state/name
    if p.is_file() and not p.is_symlink():
        print('DIAGNOSTIC_'+name+'_BEGIN');print(safe(p.read_text(errors='replace')));print('DIAGNOSTIC_END')
env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','USER','LOGNAME','LANG','SHELL'}}
env['PATH']='/opt/diana-node/bin:'+env.get('PATH','');env['CODEX_HOME']='/workspaces/.diana-codex-secure'
for args in [['codex','sandbox','--help'],['codex','app-server','--help']]:
    p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=20)
    print(json.dumps({'command':args,'exit':p.returncode,'help':safe(p.stdout+p.stderr)}))
