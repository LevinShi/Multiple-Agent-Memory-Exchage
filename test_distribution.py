import json,tempfile,unittest
from pathlib import Path
from init_vault import initialize
from demo import run_demo
class DistributionTest(unittest.TestCase):
 def test_default_deny_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   target=initialize(Path(td)/'new')
   self.assertEqual(json.loads((target/'permissions.json').read_text())['projects'],{})
   with self.assertRaises(FileExistsError):initialize(target,True)
   self.assertEqual(json.loads((target/'permissions.json').read_text())['projects'],{})
   self.assertIn(str(target/'gateway.py'),(target/'ENTRY-codex.md').read_text())
 def test_synthetic_relay(self):self.assertEqual(run_demo()['synthetic_cli_relay'],'passed')
if __name__=='__main__':unittest.main()
