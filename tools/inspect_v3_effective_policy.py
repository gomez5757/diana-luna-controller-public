"""Inspect thread metadata only. It intentionally never calls turn/start."""
import asyncio,json,os,sys
from pathlib import Path
assert os.environ.get('CODESPACE_NAME')=='diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
sys.path.insert(0,'/opt/diana-luna/parallel_v3/src')
import runtime_rpc_parallel as rpc
async def main():
    env=rpc.server_environment();env['PATH']='/opt/diana-node/bin:'+env.get('PATH','')
    cwd=Path('/workspaces/.diana-luna-probes-v3/alpha')
    async with rpc.AppServer(cwd=Path('/opt/diana-luna'),env=env) as server:
        await server._preflight()
        profiles=await server.rpc('permissionProfile/list',{'cwd':str(cwd)})
        print(json.dumps({'stage':'named-profile-list','profiles':[p for p in profiles.get('data',[]) if p.get('id')==rpc.PROFILE]}),flush=True)
        # Metadata-only observer: preserve actual server response before any validation.
        original=rpc.observed_policy
        def show(meta,job):
            safe={k:meta.get(k) for k in ['model','reasoningEffort','modelProvider','serviceTier','cwd','approvalPolicy','activePermissionProfile','sandbox','runtimeWorkspaceRoots']}
            print(json.dumps({'stage':'actual-thread-policy',**safe,'model_turns':0}),flush=True)
            original(meta,job)
        rpc.observed_policy=show
        await server._thread(rpc.Job('inspect-effective-policy',cwd,'No model turn',120))
asyncio.run(main())
