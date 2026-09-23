import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import controller as c
class MainWiringTests(unittest.TestCase):
    def test_main_uses_responsive_reader_instead_of_fixed_sleep(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'control').mkdir()
            (root/'control/installation.json').write_text('{"wake_enabled":true}')
            (root/'control/signal.json').write_text(json.dumps({'schema':1,'action':'probe','nonce':'a'*32}))
            cwd=os.getcwd()
            try:
                os.chdir(d)
                with patch.object(c,'responsive_wake',create=True,return_value={'status':'STOP_CONFIRMED'}) as new, \
                     patch.object(c,'bounded_wake',return_value={'status':'OLD'}), \
                     patch.object(c.sys,'argv',['controller.py']), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(c.main(),0)
                    new.assert_called_once_with(c,300,'a'*32)
            finally:os.chdir(cwd)
    def test_explicit_stop_uses_extended_confirmation(self):
        with patch.object(c,'stop_until_confirmed',return_value={'status':'STOP_CONFIRMED'}) as stop, \
             patch.object(c.sys,'argv',['controller.py','--stop']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(),0)
            stop.assert_called_once_with(attempts=25)
if __name__=='__main__':unittest.main()
