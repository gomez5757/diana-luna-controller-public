"""Read-only host metadata. Never open authentication files or print secrets."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib

ROOT=Path('/workspaces/diana-plus')
EXPECTED='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
if os.environ.get('CODESPACE_NAME') != EXPECTED:
    raise SystemExit('WRONG_CODESPACE')
env=dict(os.environ)
env['PATH']='/opt/diana-node/bin:'+env.get('PATH','')
def cmd(args):
    p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
    return p.returncode,p.stdout.strip()
def metadata(path):
    p=Path(path)
    if not p.exists(): return {'exists':False}
    s=p.stat()
    return {'exists':True,'uid':s.st_uid,'mode':oct(s.st_mode & 0o777),'symlink':p.is_symlink()}
def load(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink(): return {}
    return json.loads(p.read_text())
now=int(time.time())
out={'schema':1,'stage':'host-integrity-inspection','now':now,'uid':os.geteuid()}
code,version=cmd(['codex','--version'])
out['codex']={'exit':code,'version':version if re.fullmatch(r'codex-cli [0-9.a-z-]+',version) else 'UNEXPECTED_VERSION_FORMAT'}
out['sudo_noninteractive']=(cmd(['sudo','-n','true'])[0]==0)
for key,args in [('head',['rev-parse','HEAD']),('branch',['branch','--show-current'])]:
    code,val=cmd(['git','-C',str(ROOT),*args]);out[key]=val if code==0 else 'GIT_READ_FAILED'
code,status=cmd(['git','-C',str(ROOT),'status','--porcelain=v1','--untracked-files=all'])
out['checkout_clean']=(code==0 and not status)
out['dirty_paths']=[line[3:] for line in status.splitlines() if line[3:].startswith(('infra/luna-codespace/','.devcontainer/','docs/superpowers/'))]
out['other_dirty_paths_count']=sum(not line[3:].startswith(('infra/luna-codespace/','.devcontainer/','docs/superpowers/')) for line in status.splitlines())
policy=load('/opt/diana-luna/installation.json')
out['installation']={k:policy.get(k) for k in ['repository','codespace','review_valid_until','runtime_source_sha','parallel_v2_source_sha','parallel_worker_limit']}
out['installation_metadata']=metadata('/opt/diana-luna/installation.json')
source_files=policy.get('source_files',{})
out['source_hash_mismatches']=[]
for rel,digest in source_files.items():
    path=ROOT/rel
    if not (rel.startswith(('infra/luna-codespace/','.devcontainer/')) and '..' not in Path(rel).parts):continue
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        out['source_hash_mismatches'].append(rel)
authority=load('/etc/diana-luna/launch-authorization.json')
out['authorization']={'expires_at_epoch':authority.get('expires_at_epoch'),'review_evidence_keys':sorted(authority.get('owner_reviewed_evidence',{}))}
for file,key in [('/etc/codex/requirements.toml','requirements'),('/etc/codex/config.toml','managed_config')]:
    out[key]={'metadata':metadata(file)}
    if Path(file).is_file() and not Path(file).is_symlink():
        data=tomllib.loads(Path(file).read_text())
        out[key]['sha256']=hashlib.sha256(Path(file).read_bytes()).hexdigest()
        for field in ['allowed_approval_policies','allowed_sandbox_modes','allowed_models','allowed_permissions','default_permissions','sandbox_mode','forced_login_method']:
            if field in data:out[key][field]=data[field]
        out[key]['permission_profiles']=sorted(data.get('permissions',{}))
        out[key]['top_level_keys']=sorted(data)
for base,key in [(Path('/opt/diana-luna/runtime'),'installed_functions'),(ROOT/'infra/luna-codespace/runtime','source_functions')]:
    out[key]={}
    for name in ['runtime_budget.py','runtime_executor.py','runtime_boot.py','renew_authority.py']:
        p=base/name
        if p.is_file() and not p.is_symlink():
            tree=ast.parse(p.read_text())
            out[key][name]={f.name:ast.unparse(f.args) for f in tree.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef))}
for path,label in [('/workspaces/.diana-luna-state/parallel-v2-poststart-failure.json','prior_failure'),('/opt/diana-luna/parallel-v2-install.json','v2_install')]:
    data=load(path)
    out[label]={k:data.get(k) for k in ['status','source_sha','observed_at_epoch']}
    reason=str(data.get('reason',''))
    if re.fullmatch(r'[A-Za-z0-9_:./ -]{0,400}',reason) and not re.search(r'(?i)token|secret|bearer|password|auth.json',reason):out[label]['reason']=reason
print(json.dumps(out,sort_keys=True))
