import sys
import time
import unittest

from arcade_agent_desk.protocol import State
from arcade_agent_desk.runner import run_command


class RunnerTests(unittest.TestCase):
    def test_real_success_failure_and_elapsed_are_reported_without_command_text(self):
        for code, expected in ((0, State.DONE), (7, State.FAIL)):
            events = []
            result = run_command([sys.executable, '-c', f'raise SystemExit({code})'],
                                 on_event=events.append, timeout=2)
            self.assertEqual(result, code)
            self.assertEqual(events[0].state, State.WORK)
            self.assertEqual(events[-1].state, expected)
            self.assertGreaterEqual(events[-1].elapsed_ms, 0)
            self.assertNotIn('argv', vars(events[-1]))

    def test_timeout_stops_owned_child_and_reports_failure(self):
        events=[]; before=time.monotonic()
        result=run_command([sys.executable,'-c','import time; time.sleep(10)'],
                           on_event=events.append,timeout=.15)
        self.assertEqual(result,124)
        self.assertEqual(events[-1].state,State.FAIL)
        self.assertLess(time.monotonic()-before,2)

    def test_missing_executable_is_failure_and_bad_parameters_do_not_start(self):
        events=[]
        self.assertEqual(run_command(['/not-an-executable'],on_event=events.append,timeout=1),127)
        self.assertEqual(events[-1].state,State.FAIL)
        for command,timeout in (([],1),(['true'],0),(['true'],float('inf')),('true',1)):
            with self.assertRaises(ValueError):run_command(command,on_event=lambda event:None,timeout=timeout)


if __name__=='__main__':unittest.main()
