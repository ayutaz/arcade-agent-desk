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
