"""Metadata-only controlled experiments; no model turn, no persisted config edits."""
import asyncio,json,os,re,sys
from pathlib import Path
assert os.environ.get('CODESPACE_NAME')=='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
sys.path.insert(0,'/opt/diana-luna/parallel_v3/src')
import runtime_rpc_parallel as rpc
class D(rpc.AppServer):
    variant='base'
    async def _read(self):
        try:
            while raw:=await self.proc.stdout.readline():
                msg=json.loads(raw)
                if 'error' in msg:
                    text=str(msg['error'].get('message',''))[:2000]
                    text=re.sub(r'(github_pat_|gh[pousr]_|sk-)[A-Za-z0-9_-]{12,}','[REDACTED]',text)
                    print(json.dumps({'variant':self.variant,'rpc_error':text}),flush=True)
                if 'id' in msg and 'method' not in msg:
                    f=self.pending.get(msg['id'])
                    if f is not None and not f.done():
                        if 'error'in msg:f.set_exception(rpc.PolicyError('RPC_REJECTED'))
                        else:f.set_result(msg.get('result'))
                elif 'id' in msg:self._fail('INTERACTIVE_REQUEST_DENIED');return
                elif 'method'in msg:self._event(msg['method'],msg.get('params',{}))
            self._fail('TRANSPORT_EOF')
        except asyncio.CancelledError:pass
        except Exception:self._fail('PROTOCOL_ERROR')
    async def rpc(self,method,params,timeout=None):
        if method=='thread/start':
            params=dict(params)
            if self.variant=='minimal':
                for key in ['environments','selectedCapabilityRoots','dynamicTools','runtimeWorkspaceRoots']:
                    params.pop(key,None)
            if self.variant=='no-environments':params.pop('environments',None)
            if self.variant=='no-capability-filter':params.pop('selectedCapabilityRoots',None)
            if self.variant=='absolute-nested':
                cfg=dict(params['config']);cwd=params['cwd']
                cfg['permissions']={rpc.PROFILE:{'extends':':workspace','filesystem':{cwd:'write',cwd+'/.git':'read',cwd+'/.codex':'read'},'network':{'enabled':False}}}
                params['config']=cfg
        meta=await super().rpc(method,params,timeout)
        if method=='thread/start':
            print(json.dumps({'variant':self.variant,'stage':'metadata',**{k:meta.get(k) for k in ['model','reasoningEffort','activePermissionProfile','sandbox','runtimeWorkspaceRoots']},'model_turns':0}),flush=True)
        return meta
async def main():
    env=rpc.server_environment();env['PATH']='/opt/diana-node/bin:'+env.get('PATH','')
    async with D(cwd=Path('/opt/diana-luna'),env=env) as server:
        await server._preflight()
        for variant in ['minimal','no-environments','no-capability-filter','absolute-nested']:
            server.variant=variant
            try:
                await server._thread(rpc.Job('metadata-'+variant,Path('/workspaces/.diana-luna-probes-v3/alpha'),'No turn',120))
                print(json.dumps({'variant':variant,'policy_verifier':'PASS','model_turns':0}),flush=True)
            except rpc.PolicyError as error:print(json.dumps({'variant':variant,'policy_verifier':str(error)}),flush=True)
asyncio.run(main())
