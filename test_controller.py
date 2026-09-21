import unittest
from pathlib import Path
from unittest.mock import patch
import controller

class ControllerTests(unittest.TestCase):
    def signal(self, action='stop'):
        return {'schema':1, 'action':action, 'nonce':'a'*32}
    def test_stop_default(self):
        self.assertEqual(controller.validate_signal(self.signal())['action'],'stop')
    def test_no_arbitrary_target_or_commands(self):
        for payload in [dict(self.signal(),target='other'),dict(self.signal(),command='pwd'),dict(self.signal(),schema=True),dict(self.signal(),action='delete')]:
            with self.assertRaises(controller.GuardError): controller.validate_signal(payload)
    def test_wake_is_gated_until_installation(self):
        with self.assertRaises(controller.GuardError): controller.validate_signal(self.signal('wake'))
    def test_stop_observes_provider_shutdown(self):
        responses=iter([{'state':'ShuttingDown'},{'state':'Shutdown'}]); calls=[]
        def api(action): calls.append(action); return next(responses)
        result=controller.stop_until_confirmed(api=api,sleep=lambda _:None)
        self.assertEqual(result['state'],'Shutdown');self.assertEqual(calls,['stop','stop'])
    def test_stop_does_not_claim_shutdown_from_acceptance(self):
        with self.assertRaises(controller.GuardError):
            controller.stop_until_confirmed(api=lambda _: {},sleep=lambda _:None, attempts=2)
    def test_stop_http_failure_is_closed(self):
        def api(_): raise controller.GuardError('HTTP_403')
        with self.assertRaises(controller.GuardError): controller.stop_until_confirmed(api=api,sleep=lambda _:None)
    def test_api_target_is_fixed(self):
        self.assertTrue(controller.CODESPACE.startswith('diana-luna-secure-auth-'))
        self.assertNotIn('/', controller.CODESPACE)
    def test_missing_credential_does_not_get_printed(self):
        with patch.dict(controller.os.environ,{},clear=True), self.assertRaisesRegex(controller.GuardError,'LIFECYCLE_SECRET_MISSING'):
            controller.api_post('stop')
    def test_foreign_endpoint_is_rejected(self):
        with self.assertRaises(controller.GuardError): controller.api_post('exports')

if __name__=='__main__': unittest.main()
