from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from arcade_agent_desk.jobs import run_jobs
from arcade_agent_desk.runner import run_command
from arcade_agent_desk.protocol import State

class JobTests(unittest.TestCase):
    def test_four_real_jobs_report_their_own_success_failure_and_deadline(self):
        jobs=[dict(task=1,command=[sys.executable,'-c','pass'],timeout=2),
              dict(task=2,command=[sys.executable,'-c','raise SystemExit(7)'],timeout=2),
              dict(task=3,command=[sys.executable,'-c','import time;time.sleep(.1)'],timeout=2),
              dict(task=4,command=[sys.executable,'-c','import time;time.sleep(5)'],timeout=.08)]
        events=[];owner=threading.get_ident()
        def received(task,event):
            self.assertEqual(threading.get_ident(),owner);events.append((task,event.state))
        result=run_jobs(jobs,on_event=received)
        self.assertEqual(result,{1:0,2:7,3:0,4:124})
        for task,final in ((1,State.DONE),(2,State.FAIL),(3,State.DONE),(4,State.FAIL)):
            self.assertIn((task,State.WORK),events);self.assertEqual([state for ident,state in events if ident==task][-1],final)
    def test_invalid_group_is_rejected_before_any_process_starts(self):
        row=dict(task=1,command=[sys.executable,'-c','pass'],timeout=2)
        for jobs in ([],[row,row],[dict(row,task=5)],[dict(row,unexpected=True)],[dict(row,timeout=float('nan'))]):
            with patch('arcade_agent_desk.runner.subprocess.Popen') as process:
                with self.assertRaises(ValueError):run_jobs(jobs,on_event=lambda *_:None)
                process.assert_not_called()
    def test_precancelled_command_never_launches_and_emits_cancel(self):
        stop=threading.Event();stop.set();events=[]
        with patch('arcade_agent_desk.runner.subprocess.Popen') as process:
            code=run_command([sys.executable,'-c','pass'],on_event=events.append,cancel=stop)
        self.assertEqual(code,130);self.assertEqual(events[-1].state,State.CANCEL);process.assert_not_called()
    def test_cancellation_stops_owned_running_jobs(self):
        stop=threading.Event();events=[]
        def event(task,row):
            events.append(row.state)
            if row.state==State.WORK:stop.set()
        result=run_jobs([dict(task=1,command=[sys.executable,'-c','import time;time.sleep(10)'],timeout=20)],on_event=event,stop=stop)
        self.assertEqual(result,{1:130});self.assertEqual(events[-1],State.CANCEL)

    def test_event_sink_exceptions_are_not_confused_with_an_empty_internal_queue(self):
        import queue
        def sink(*_):raise queue.Empty('sink failed')
        with self.assertRaises(queue.Empty):
            run_jobs([dict(task=1,command=[sys.executable,'-c','pass'],timeout=2)],on_event=sink)
