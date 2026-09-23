"""Public lifecycle helper: observe only the fixed public control signal.

No model credentials or private repository contents. A signal reader failure
causes stop, never a wider retry or a longer unbounded compute lease.
"""
from __future__ import annotations
import base64
import json
import os
import time
import urllib.error
import urllib.request

SIGNAL_URL = 'https://api.github.com/repos/gomez5757/diana-luna-controller-public/contents/control/signal.json?ref=main'


def read_signal(controller):
    token = os.environ.get('GITHUB_TOKEN', '')
    if not token:
        raise controller.GuardError('CONTROL_READ_TOKEN_MISSING')
    req = urllib.request.Request(SIGNAL_URL, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'diana-lifecycle/3',
        'Cache-Control': 'no-cache',
    })
    try:
        with urllib.request.build_opener(controller.NoRedirect).open(req, timeout=10) as response:
            if response.status != 200:
                raise controller.GuardError('CONTROL_HTTP_STATUS_INVALID')
            raw = response.read(16385)
            if len(raw) > 16384:
                raise controller.GuardError('CONTROL_RESPONSE_TOO_LARGE')
            obj = json.loads(raw)
            if (type(obj) is not dict or obj.get('path') != 'control/signal.json'
                or obj.get('encoding') != 'base64' or type(obj.get('content')) is not str):
                raise controller.GuardError('CONTROL_RESPONSE_INVALID')
            encoded = obj['content'].replace('\n', '')
            value = base64.b64decode(encoded, validate=True)
            if len(value) > 2048:
                raise controller.GuardError('CONTROL_SIGNAL_TOO_LARGE')
            return controller.validate_signal(json.loads(value), wake_enabled=True)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        if isinstance(exc, controller.GuardError):
            raise
        raise controller.GuardError('CONTROL_READ_FAILED') from None


def responsive_wake(controller, seconds, nonce, *, read_current=None,
                    api=None, sleep=time.sleep, clock=time.monotonic):
    if type(seconds) is not int or not 1 <= seconds <= 900:
        raise controller.GuardError('LEASE_DURATION_INVALID')
    controller.validate_signal({'schema': 1, 'action': 'wake', 'nonce': nonce}, wake_enabled=True)
    read_current = (lambda: read_signal(controller)) if read_current is None else read_current
    api = controller.api_post if api is None else api
    deadline = clock() + seconds
    requested = False
    reason = 'LEASE_EXPIRED'
    try:
        current = controller.validate_signal(read_current(), wake_enabled=True)
        if current['action'] == 'stop' or current['nonce'] != nonce:
            reason = 'REQUEST_SUPERSEDED_BEFORE_START'
        else:
            api('start')
            requested = True
            while clock() < deadline:
                current = controller.validate_signal(read_current(), wake_enabled=True)
                if current['action'] == 'stop' or current['nonce'] != nonce:
                    reason = 'STOP_OR_NEW_REQUEST_OBSERVED'
                    break
                sleep(min(5, max(0, deadline - clock())))
    finally:
        # More provider-confirmation time than the original 8-attempt stop.
        stopped = controller.stop_until_confirmed(api=api, sleep=sleep, attempts=25)
    return {**stopped, 'wake_requested': requested, 'lease_seconds': seconds,
            'stop_reason': reason, 'worker_result': 'READ_PRIVATE_RECEIPT_SEPARATELY'}
