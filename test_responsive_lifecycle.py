from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from responsive_lifecycle import responsive_wake

NONCE='a'*32
class Error(ValueError):pass
class C:
    GuardError=Error
    @staticmethod
    def validate_signal(value,**_):
        if set(value)!={'schema','action','nonce'} or value['action'] not in {'wake','stop','probe'}:
            raise Error('SIGNAL_INVALID')
        if len(value['nonce'])!=32:raise Error('NONCE_INVALID')
        return value
    @staticmethod
    def stop_until_confirmed(*,api,sleep,attempts):
        for i in range(attempts):
            if api('stop')['state']=='Shutdown':return {'state':'Shutdown','status':'STOP_CONFIRMED'}
            if i+1<attempts:sleep(5)
        raise Error('SHUTDOWN_NOT_CONFIRMED')

def sig(action='wake',nonce=NONCE):return {'schema':1,'action':action,'nonce':nonce}
class LifecycleTests(unittest.TestCase):
    def setUp(self):self.t=0;self.actions=[];self.reads=0;self.states=['Shutdown']
    def api(self,action):
        self.actions.append(action)
        if action=='start':return {'state':'Starting'}
        return {'state':self.states.pop(0) if len(self.states)>1 else self.states[0]}
    def sleep(self,n):self.t+=n
    def run_wake(self,reader,seconds=300):
        return responsive_wake(C,seconds,NONCE,read_current=reader,api=self.api,sleep=self.sleep,clock=lambda:self.t)
    def test_existing_stop_prevents_start(self):
        r=self.run_wake(lambda:sig('stop'))
        self.assertEqual(self.actions,['stop']);self.assertFalse(r['wake_requested'])
    def test_new_nonce_prevents_old_start(self):
        self.run_wake(lambda:sig(nonce='b'*32));self.assertNotIn('start',self.actions)
    def test_stop_is_observed_without_waiting_300_seconds(self):
        def reader():
            self.reads+=1
            return sig('stop' if self.reads>=3 else 'wake')
        r=self.run_wake(reader)
        self.assertEqual(self.t,5);self.assertEqual(r['state'],'Shutdown')
    def test_lease_is_bounded_when_signal_does_not_change(self):
        self.run_wake(lambda:sig(),seconds=17)
        self.assertEqual(self.t,17);self.assertEqual(self.actions,['start','stop'])
    def test_read_error_still_stops(self):
        def reader():
            self.reads+=1
            if self.reads>1:raise Error('READ_FAILED')
            return sig()
        with self.assertRaises(Error):self.run_wake(reader)
        self.assertEqual(self.actions,['start','stop'])
    def test_start_error_still_attempts_stop(self):
        def api(action):
            self.actions.append(action)
            if action=='start':raise Error('START_FAILED')
            return {'state':'Shutdown'}
        self.api=api
        with self.assertRaises(Error):self.run_wake(lambda:sig())
        self.assertEqual(self.actions,['start','stop'])
    def test_provider_stop_can_need_more_than_8_checks(self):
        self.states=['ShuttingDown']*10+['Shutdown']
        self.run_wake(lambda:sig('stop'))
        self.assertEqual(len(self.actions),11)
    def test_invalid_lease_never_starts(self):
        with self.assertRaises(Error):self.run_wake(lambda:sig(),seconds=901)
        self.assertEqual(self.actions,[])

if __name__=='__main__':unittest.main()
