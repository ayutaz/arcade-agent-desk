import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from arcade_agent_desk.protocol import Notice, State, decode_hello, encode_notice

ROOT=Path(__file__).resolve().parents[1]
KEY=bytes(range(16))


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        out=Path(cls.temp.name)/'app.dylib'
        result=subprocess.run(['clang','-std=c99','-shared','-fPIC','-Wno-unknown-attributes',
                        '-I'+str(ROOT/'vendor'),'-I'+str(ROOT/'tests'),str(ROOT/'app/app.c'),
                        str(ROOT/'tests/mock_os.c'),'-o',str(out)],capture_output=True,text=True)
        if result.returncode:raise AssertionError(result.stderr)
        cls.lib=ctypes.CDLL(str(out))
        cls.lib.mock_input.argtypes=[ctypes.c_char_p,ctypes.c_int]
        cls.lib.mock_output.argtypes=[ctypes.c_void_p]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):self.lib.mock_reset(6);self.lib.init()
    def tick(self,key=0,dt=0):return self.lib.tick(key,key,0,dt)
    def send(self,notice):
        packet=encode_notice(notice,KEY)
        self.lib.mock_input(packet,len(packet));self.tick()
    def test_generation_is_persisted_before_authenticated_hello(self):
        self.assertEqual(self.lib.mock_generation(),7)
        self.tick(dt=1000);out=ctypes.create_string_buffer(64)
        n=self.lib.mock_output(out)
        self.assertEqual(decode_hello(bytes(out)[:n],KEY),7)
    def test_authenticated_status_beep_duplicate_and_expiry(self):
        self.send(Notice(7,1,1,State.WORK));self.assertEqual(self.lib.debug_value(),State.WORK)
        self.send(Notice(7,2,1,State.DONE));self.assertEqual(self.lib.debug_value(),State.DONE)
        self.assertEqual(self.lib.mock_beeps(),1)
        self.send(Notice(7,2,1,State.DONE));self.assertEqual(self.lib.mock_beeps(),1)
        self.tick(dt=5000);self.assertEqual(self.lib.debug_value(),State.LOST)
        self.assertLessEqual(self.lib.mock_rects(),128)
    def test_replay_tampering_ordering_and_launch_replay_rejected(self):
        self.send(Notice(7,9,1,State.WORK))
        for notice in (Notice(6,10,1,State.DONE),Notice(7,8,1,State.DONE)):
            self.send(notice);self.assertEqual(self.lib.debug_value(),State.WORK)
        packet=bytearray(encode_notice(Notice(7,10,1,State.DONE),KEY));packet[20]^=1
        self.lib.mock_input(bytes(packet),40);self.tick()
        self.assertEqual(self.lib.debug_value(),State.WORK)
        self.lib.init();self.assertEqual(self.lib.mock_generation(),8)
        self.send(Notice(7,10,1,State.DONE));self.assertEqual(self.lib.debug_value(),State.LOST)
    def test_task_selection_and_back_exits_before_io(self):
        self.send(Notice(7,1,1,State.WORK));self.send(Notice(7,2,2,State.FAIL))
        self.tick(1);self.assertEqual(self.lib.debug_x(),2)
        self.assertEqual(self.lib.debug_value(),State.FAIL)
        before=self.lib.mock_io();self.assertEqual(self.tick(64),1)
        self.assertEqual(self.lib.mock_io(),before)
    def test_storage_unavailable_or_exhausted_fails_closed(self):
        for value in (-1,0x7fffffff):
            self.lib.mock_reset(value);self.lib.init()
            self.send(Notice(1,1,1,State.DONE));self.assertEqual(self.lib.debug_value(),State.LOST)
            self.tick(dt=1000);out=ctypes.create_string_buffer(64)
            self.assertEqual(self.lib.mock_output(out),0)


if __name__=='__main__':unittest.main()
