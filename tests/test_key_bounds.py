import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class KeyBoundsTests(unittest.TestCase):
    def test_pairing_fifo_is_rejected_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pairing';os.mkfifo(path,0o600)
            code="from arcade_agent_desk.build import load_key; import sys\ntry: load_key(sys.argv[1])\nexcept ValueError: raise SystemExit(0)\nraise SystemExit(1)"
            result=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,timeout=.5)
            self.assertEqual(result.returncode,0)
