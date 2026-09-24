import asyncio,json,os,sys
from pathlib import Path
assert os.environ.get('CODESPACE_NAME')=='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
sys.path.insert(0,'/opt/diana-luna/parallel_v3/src')
import runtime_rpc_parallel as rpc
class ScopedProbe(rpc.AppServer):
    async def rpc(self,method,params,timeout=None):
        if method=='thread/start':
            params=dict(params);cfg=dict(params.get('config',{}));cwd=params['cwd']
            cfg[f'permissions.{rpc.PROFILE}.filesystem."{cwd}"']='write'
            for part in ['.git','.codex','.devcontainer']:
                cfg[f'permissions.{rpc.PROFILE}.filesystem."{cwd}/{part}"']='read'
            params['config']=cfg
        value=await super().rpc(method,params,timeout)
        if method=='thread/start':
            print(json.dumps({'stage':'explicit-scope-probe',**{k:value.get(k) for k in ['model','reasoningEffort','approvalPolicy','activePermissionProfile','sandbox','runtimeWorkspaceRoots']},'model_turns':0}),flush=True)
        return value
async def main():
    env=rpc.server_environment();env['PATH']='/opt/diana-node/bin:'+env.get('PATH','')
    async with ScopedProbe(cwd=Path('/opt/diana-luna'),env=env) as server:
        await server._preflight()
        await server._thread(rpc.Job('explicit-scope-probe',Path('/workspaces/.diana-luna-probes-v3/alpha'),'No model turn',120))
        print('EXPLICIT_WORKSPACE_POLICY_VERIFIED_NO_MODEL_TURN',flush=True)
asyncio.run(main())
