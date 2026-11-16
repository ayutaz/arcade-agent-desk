import sys
import threading
import unittest
from unittest.mock import patch
from arcade_agent_desk.runner import run_command
from arcade_agent_desk.protocol import State

class RunnerCancelTests(unittest.TestCase):
    def test_cancelled_before_launch_has_no_child_and_reports_cancel(self):
        stop=threading.Event();stop.set();events=[]
        with patch('arcade_agent_desk.runner.subprocess.Popen') as process:
            self.assertEqual(run_command([sys.executable,'-c','pass'],on_event=events.append,cancel=stop),130)
            process.assert_not_called()
        self.assertEqual(events[-1].state,State.CANCEL)
