from pathlib import Path
import json,os,re,sqlite3,subprocess,tomllib
assert os.environ.get('CODESPACE_NAME')=='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
state=Path('/workspaces/.diana-luna-state')
p=state/'v3-target-tests.log'
if p.is_file() and not p.is_symlink():
    lines=p.read_text().splitlines()
    print('SYNTHETIC_TEST_FAILURE_BEGIN')
    for line in lines[-35:]:
        if re.search('(?i)access_token|refresh_token|bearer |password|github_pat_|ghp_',line):continue
        print(line[:500])
    print('SYNTHETIC_TEST_FAILURE_END')
req=Path('/etc/codex/requirements.toml')
print(json.dumps({'stage':'managed-permissions','permissions':tomllib.loads(req.read_text()).get('permissions',{})},sort_keys=True))
p=Path('/workspaces/.diana-codex-secure/config.toml')
if p.is_file() and not p.is_symlink():
    cfg=tomllib.loads(p.read_text())
    print(json.dumps({'stage':'config-shape','keys':sorted(cfg),'has_legacy_sandbox':'sandbox_mode' in cfg,'profile_names':sorted(cfg.get('permissions',{}))}))
env=dict(os.environ);env['PATH']='/opt/diana-node/bin:'+env.get('PATH','')
p=subprocess.run(['codex','sandbox','linux','--help'],env=env,capture_output=True,text=True,timeout=20)
print('SANDBOX_HELP_BEGIN\n'+p.stdout+'SANDBOX_HELP_END')
db=state/'runtime.sqlite'
if db.is_file() and not db.is_symlink():
    with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as con:rows=con.execute('select id,status from rounds').fetchall()
    print(json.dumps({'stage':'journal-status','rounds':rows}))
