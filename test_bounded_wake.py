import unittest
import controller as c
class WakeTests(unittest.TestCase):
    def test_wake_is_always_followed_by_confirmed_stop(self):
        self.assertTrue(hasattr(c,'bounded_wake'))
        calls=[]
        def api(action):
            calls.append(action)
            return {'state':'Shutdown' if action=='stop' else 'Starting'}
        result=c.bounded_wake(30,api=api,sleep=lambda seconds:calls.append(seconds))
        self.assertEqual(calls,['start',30,'stop'])
        self.assertEqual(result['status'],'STOP_CONFIRMED')
        self.assertTrue(result['wake_requested'])
    def test_exception_in_lease_still_stops(self):
        self.assertTrue(hasattr(c,'bounded_wake'))
        calls=[]
        def api(action):calls.append(action);return {'state':'Shutdown'}
        def interrupt(seconds):raise RuntimeError('synthetic interruption')
        with self.assertRaises(RuntimeError):c.bounded_wake(30,api=api,sleep=interrupt)
        self.assertEqual(calls,['start','stop'])
    def test_oversized_lease_rejected_before_start(self):
        self.assertTrue(hasattr(c,'bounded_wake'))
        for seconds in [True,0,901,-1]:
            with self.subTest(seconds=seconds),self.assertRaises(c.GuardError):
                c.bounded_wake(seconds,api=lambda action:self.fail('API called'),sleep=lambda _:None)
if __name__=='__main__':unittest.main(verbosity=2)
