import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from arcade_agent_desk.build import build_app, create_key, load_key
from arcade_agent_desk.protocol import Notice, State, decode_hello, encode_notice

ROOT=Path(__file__).resolve().parents[2]
SDK=Path(os.environ.get('ARCADE_OS_ROOT',str(ROOT.parent/'scratch-arcade-os')))

class Network:
    def __init__(self):self.queue=[];self.sent=[]
    def call(self,op,data,capacity):
        if op==3:return 1
        if op==1:self.sent.append(bytes(data));return 1
        if not self.queue:return 0
        packet=self.queue.pop(0);data[:len(packet)]=packet;return len(packet)

class Storage:
    def __init__(self):self.value=0
    def call(self,op,slot,value):
        if op==1:return (1,self.value)
        self.value=value;return (1,value)

class Audio:
    def __init__(self):self.tones=[]
    def call(self,op,a,b):
        if op==4:return 0
        if op==1:self.tones.append((a,b));return 1
        return 1

class WasmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();base=Path(cls.temp.name)
        keyfile=base/'pair.json';create_key(keyfile);cls.key=load_key(keyfile)
        build_app(SDK,keyfile,base/'build')
        cls.blob=(base/'build/app.wasm').read_bytes()
        cls.manifest=json.loads((base/'build/manifest.json').read_text())
        cls.Session=importlib.import_module('labos.sdk').Session
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_real_wasm_authentication_expiry_selection_and_early_exit(self):
        network=Network();storage=Storage();audio=Audio()
        session=self.Session(self.blob,self.manifest,network=network,state=storage,audio=audio)
        try:
            session.frame(0,1000);self.assertEqual(decode_hello(network.sent[-1],self.key),1)
            network.queue.append(encode_notice(Notice(1,1,2,State.DONE,100,123),self.key))
            session.frame(0,1020)
            self.assertEqual(session.debug('debug_value'),State.DONE)
            self.assertEqual(session.debug('debug_x'),2);self.assertEqual(session.debug('debug_elapsed'),123)
            self.assertEqual(len(audio.tones),1);self.assertLessEqual(len(session.commands),128)
            network.queue.append(encode_notice(Notice(1,1,2,State.FAIL),self.key))
            session.frame(0,1040);self.assertEqual(session.debug('debug_value'),State.DONE)
            session.frame(0,6100);self.assertEqual(session.debug('debug_value'),State.LOST)
            before=len(network.sent);self.assertTrue(session.frame(192,6120));self.assertEqual(len(network.sent),before)
        finally:session.close()
        again=self.Session(self.blob,self.manifest,network=Network(),state=storage,audio=Audio())
        try:self.assertEqual(storage.value,2)
        finally:again.close()
