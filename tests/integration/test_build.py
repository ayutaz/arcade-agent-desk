import json
import os
from pathlib import Path
import tempfile
import unittest

from arcade_agent_desk.build import build_app, create_key, load_key

ROOT=Path(__file__).resolve().parents[2]
SDK=Path(os.environ.get('ARCADE_OS_ROOT',str(ROOT.parent/'scratch-arcade-os')))


class BuildTests(unittest.TestCase):
    def test_pairing_is_private_exclusive_and_errors_do_not_echo_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            keyfile=Path(tmp)/'pairing.json'
            create_key(keyfile);key=load_key(keyfile)
            self.assertEqual(len(key),16)
            self.assertEqual(keyfile.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):create_key(keyfile)
            alias=Path(tmp)/'alias';alias.symlink_to(keyfile)
            with self.assertRaises(ValueError):load_key(alias)
            keyfile.write_text('{"key_hex":"DO-NOT-ECHO-THIS"}')
            with self.assertRaises(ValueError) as caught:load_key(keyfile)
            self.assertNotIn('DO-NOT-ECHO',str(caught.exception))

    def test_real_wasm_build_is_deterministic_bound_and_key_specific(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);keyfile=base/'pairing.json';create_key(keyfile)
            a=build_app(SDK,keyfile,base/'first');b=build_app(SDK,keyfile,base/'second')
            self.assertEqual(a['sha256'],b['sha256'])
            self.assertLessEqual(a['package_bytes'],16384)
            self.assertEqual(a['capabilities'],['draw','speaker','network','storage'])
            other=base/'other.json';create_key(other)
            c=build_app(SDK,other,base/'third');self.assertNotEqual(a['sha256'],c['sha256'])
            self.assertFalse(a['device_tested'])
            self.assertFalse((ROOT/'app/desk_key.h').exists())

    def test_foreign_output_and_unpinned_sdk_rejected_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);keyfile=base/'pair.json';create_key(keyfile)
            out=base/'existing';out.mkdir();(out/'keep').write_text('preserve')
            with self.assertRaises(ValueError):build_app(SDK,keyfile,out)
            with self.assertRaises(ValueError):build_app(base,keyfile,base/'out')
            self.assertEqual((out/'keep').read_text(),'preserve')


if __name__=='__main__':unittest.main()

class DelayedBootTransportTests(unittest.TestCase):
    def test_connect_waits_for_a_slow_initial_beacon_without_sending_or_resetting_early(self):
        import importlib,struct
        from contextlib import contextmanager
        from unittest.mock import patch
        from arcade_agent_desk.build import pinned_sdk
        from arcade_agent_desk.transport import adapter
        pinned_sdk(SDK)
        module=importlib.import_module('labos.transfer');clock=[0.0];writes=[]
        class Stream:
            def __init__(self):self.pending=b''
            def read(self,n):
                clock[0]+=.1
                if self.pending:result=self.pending;self.pending=b'';return result
                if clock[0]>=3.5:
                    return module.encode(module.Frame(1,0,0,module.SIGNATURE+struct.pack('<4I',17,16384,512,2),response=True))
                return b''
            def write(self,data):
                self.assert_ready=clock[0]>=3.5
                writes.append((clock[0],data));frame=module.Parser().feed(data)[0]
                self.pending=module.encode(module.Frame(frame.op,frame.session,frame.request,b'',response=True))
                return len(data)
        @contextmanager
        def connection(port):yield Stream()
        original=module.Client
        def factory(stream,**kwargs):return original(stream,clock=lambda:clock[0],**kwargs)
        with patch.object(module,'serial_connection',connection),patch.object(module,'Client',factory):
            _,connect=adapter(SDK)
            with connect('fake-port') as client:self.assertTrue(client.connected)
        self.assertTrue(writes);self.assertTrue(all(when>=3.5 for when,_ in writes))
        self.assertLess(clock[0],12)
