"""Metadata-only RPC probe. No model turn, auth-file read, or account output."""
from pathlib import Path
import asyncio,json,os,re,sys
assert os.environ.get('CODESPACE_NAME')=='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
sys.path.insert(0,'/opt/diana-luna/parallel_v3/src')
import runtime_rpc_parallel as rpc
STATE=Path('/workspaces/.diana-luna-state')
def safe(text):
    text=re.sub(r'(?i)bearer\s+\S+','Bearer [REDACTED]',text)
    text=re.sub(r'(github_pat_|gh[pousr]_|sk-)[A-Za-z0-9_-]{12,}','[REDACTED]',text)
    text=re.sub(r'(?i)([\"\x27]?(?:access_token|refresh_token|id_token|password)[\"\x27]?\s*[:=]\s*[\"\x27])[^\"\x27]+',r'\1[REDACTED]',text)
    return text[-5000:]
p=STATE/'v3-appserver-preflight-stderr.log'
if p.is_file() and not p.is_symlink():print(json.dumps({'stage':'previous-stderr','error':safe(p.read_text(errors='replace'))}),flush=True)
class Diagnostic(rpc.AppServer):
    async def _read(self):
        try:
            while raw:=await self.proc.stdout.readline():
                msg=json.loads(raw)
                if 'error' in msg:
                    print(json.dumps({'stage':'rpc-error','error':safe(json.dumps(msg['error']))}),flush=True)
                if 'id' in msg and 'method' not in msg:
                    f=self.pending.get(msg['id'])
                    if f and not f.done():
                        if 'error' in msg:f.set_exception(rpc.PolicyError('RPC_REJECTED'))
                        else:f.set_result(msg.get('result'))
                elif 'method' in msg and 'id' in msg:
                    self._fail('INTERACTIVE_REQUEST_DENIED');return
                elif 'method' in msg:self._event(msg['method'],msg.get('params',{}))
            self._fail('TRANSPORT_EOF')
        except asyncio.CancelledError:pass
        except Exception:self._fail('PROTOCOL_ERROR')
    async def _stderr(self):
        while block:=await self.proc.stderr.read(8192):
            self.stderr_hash.update(block)
            print(json.dumps({'stage':'stderr','error':safe(block.decode(errors='replace'))}),flush=True)
async def main():
    env=rpc.server_environment();env['PATH']='/opt/diana-node/bin:'+env.get('PATH','')
    async with Diagnostic(cwd=Path('/opt/diana-luna'),env=env) as server:
        await server._preflight()
        print('ACCOUNT_AND_MODEL_CATALOG_PREFLIGHT_PASS',flush=True)
        meta=await server._thread(rpc.Job('diagnostic-metadata',Path('/workspaces/.diana-luna-probes-v3/alpha'),'No model turn',120))
        print(json.dumps({'stage':'thread-ok','model':meta.get('model'),'effort':meta.get('reasoningEffort'),'sandbox':meta.get('sandbox'),'profile':meta.get('activePermissionProfile'),'model_turns':0}),flush=True)
asyncio.run(main())
