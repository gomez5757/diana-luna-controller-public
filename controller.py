"""GitHub-only lifecycle preflight. No code, prompts or ChatGPT auth are read.

Only the named pre-existing Codespace can be stopped. Waking remains disabled
until the private worker and its independent shutdown mechanism pass validation.
This program never exports a Codespace or follows HTTP redirects.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from responsive_lifecycle import responsive_wake

CODESPACE = 'diana-luna-secure-auth-pjxq7jrj7xpwfrpjx'
API = 'https://api.github.com'

class GuardError(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GuardError('API_REDIRECT_REJECTED')

def validate_signal(data: object, *, wake_enabled=False) -> dict:
    if type(data) is not dict or set(data) != {'schema', 'action', 'nonce'}:
        raise GuardError('SIGNAL_FIELDS_INVALID')
    if type(data['schema']) is not int or data['schema'] != 1:
        raise GuardError('SCHEMA_INVALID')
    if type(data['nonce']) is not str or re.fullmatch(r'[a-f0-9]{32}',data['nonce']) is None:
        raise GuardError('NONCE_INVALID')
    if data['action'] != 'stop' and not (wake_enabled is True and data['action'] in ('wake','probe')):
        raise GuardError('WAKE_DISABLED_PENDING_PRIVATE_WORKER_VALIDATION')
    return data

def api_post(action: str) -> dict:
    if action not in ('stop','start'):
        raise GuardError('ENDPOINT_NOT_ALLOWED')
    token = os.environ.get('DIANA_CODESPACE_LIFECYCLE_TOKEN','')
    if not token:
        raise GuardError('LIFECYCLE_SECRET_MISSING')
    request=urllib.request.Request(
        f'{API}/user/codespaces/{CODESPACE}/{action}',method='POST',
        headers={'Authorization':f'Bearer {token}',
                 'Accept':'application/vnd.github+json',
                 'X-GitHub-Api-Version':'2026-03-10',
                 'User-Agent':'diana-lifecycle-preflight/1'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as response:
            if response.status != 200:
                raise GuardError('HTTP_STATUS_NOT_200')
            raw=response.read(131073)
            if len(raw)>131072:
                raise GuardError('API_RESPONSE_TOO_LARGE')
            value=json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise GuardError(f'GITHUB_HTTP_{exc.code}') from None
    except (urllib.error.URLError,TimeoutError,ValueError) as exc:
        if isinstance(exc,GuardError): raise
        raise GuardError('GITHUB_RESPONSE_UNAVAILABLE') from None
    if type(value) is not dict:
        raise GuardError('API_RESPONSE_INVALID')
    # Never log the full API reply; it can contain private repository metadata.
    return {'state':value.get('state')}

def stop_until_confirmed(*,api=api_post,sleep=time.sleep,attempts=8) -> dict:
    for n in range(attempts):
        reply=api('stop')
        if reply.get('state') == 'Shutdown':
            return {'schema':1,'status':'STOP_CONFIRMED','state':'Shutdown','model_calls':0}
        if n+1<attempts: sleep(5)
    raise GuardError('SHUTDOWN_NOT_CONFIRMED')

def bounded_wake(seconds: int, *, api=api_post, sleep=time.sleep) -> dict:
    if type(seconds) is not int or not 1 <= seconds <= 900:
        raise GuardError('LEASE_DURATION_INVALID')
    try:
        api('start')
        # Acceptance is not proof of private worker success.
        sleep(seconds)
    finally:
        stopped=stop_until_confirmed(api=api,sleep=sleep)
    return {**stopped,'wake_requested':True,'lease_seconds':seconds,
            'worker_result':'READ_PRIVATE_RECEIPT_SEPARATELY'}


def main() -> int:
    try:
        if sys.argv[1:] == ['--stop']:
            print(json.dumps(stop_until_confirmed(attempts=25),sort_keys=True));return 0
        path=Path('control/signal.json')
        if path.is_symlink() or path.stat().st_size>2048:
            raise GuardError('SIGNAL_FILE_INVALID')
        installed=json.loads(Path('control/installation.json').read_text(encoding='utf-8'))
        signal=validate_signal(json.loads(path.read_text(encoding='utf-8')),wake_enabled=installed.get('wake_enabled') is True)
        result=stop_until_confirmed(attempts=25) if signal['action']=='stop' else responsive_wake(sys.modules[__name__], 300 if signal['action']=='probe' else 900, signal['nonce'])
        print(json.dumps(result,sort_keys=True))
        return 0
    except (GuardError,OSError,ValueError) as exc:
        reason=str(exc) if isinstance(exc,GuardError) else type(exc).__name__
        print(json.dumps({'status':'BLOCKED','reason':reason}),file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
