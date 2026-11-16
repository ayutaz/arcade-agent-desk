import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest

from arcade_agent_desk.cli import main
from arcade_agent_desk.protocol import decode_notice, encode_hello, State


class CliTests(unittest.TestCase):
    def test_watch_uses_one_bridge_for_validated_jobs_and_returns_failure_for_any_failed_job(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            key=Path(tmp)/'pair.json';main(['pair','--key',str(key)],out=io.StringIO())
            jobs=Path(tmp)/'jobs.json';jobs.write_text(json.dumps(dict(jobs=[dict(task=1,command=[sys.executable,'-c','pass'],timeout=2)])))
            output=io.StringIO()
            with patch('arcade_agent_desk.cli.run_jobs',return_value={1:0,2:7},create=True) as runner:
                self.assertEqual(main(['watch','--jobs',str(jobs),'--key',str(key),'--port','0','--linger','0'],out=output),1)
                self.assertEqual(runner.call_args.args[0][0]['task'],1)
            self.assertNotIn('pass',output.getvalue())
            jobs.write_text('{"jobs":[]}')
            with patch('arcade_agent_desk.cli.Bridge') as bridge:
                self.assertEqual(main(['watch','--jobs',str(jobs),'--key',str(key),'--linger','0'],out=io.StringIO()),2)
                bridge.assert_not_called()

    def test_pairing_does_not_print_key_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            key=Path(tmp)/'pair.json';output=io.StringIO()
            self.assertEqual(main(['pair','--key',str(key)],out=output),0)
            self.assertNotIn(json.loads(key.read_text())['key_hex'],output.getvalue())
            self.assertEqual(main(['pair','--key',str(key)],out=output),2)

    def test_real_command_exits_and_final_state_reaches_udp_device(self):
        with tempfile.TemporaryDirectory() as tmp, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as reservation:
            key=Path(tmp)/'pair.json';main(['pair','--key',str(key)],out=io.StringIO())
            secret=bytes.fromhex(json.loads(key.read_text())['key_hex'])
            reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1];reservation.close()
            stop=threading.Event();notices=[]
            def device():
                with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as peer:
                    peer.bind(('127.0.0.1',0));peer.settimeout(.03)
                    while not stop.is_set():
                        peer.sendto(encode_hello(1,secret),('127.0.0.1',port))
                        try:notices.append(decode_notice(peer.recvfrom(64)[0],secret))
                        except socket.timeout:pass
                        time.sleep(.01)
            thread=threading.Thread(target=device);thread.start()
            try:
                result=main(['run','--key',str(key),'--bind','127.0.0.1','--port',str(port),'--task','2','--linger','0.15','--',sys.executable,'-c','import sys;sys.exit(7)'],out=io.StringIO())
            finally:stop.set();thread.join(1)
            self.assertEqual(result,7)
            self.assertTrue(any(row.state==State.FAIL and row.task==2 for row in notices))

    def test_invalid_options_do_not_launch_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            key=Path(tmp)/'pair.json';main(['pair','--key',str(key)],out=io.StringIO())
            sentinel=Path(tmp)/'unexpected'
            result=main(['run','--key',str(key),'--linger','nan','--',sys.executable,'-c',f'open({str(sentinel)!r},"w").close()'],out=io.StringIO())
            self.assertEqual(result,2);self.assertFalse(sentinel.exists())


if __name__=='__main__':unittest.main()
