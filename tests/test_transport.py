from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_device import Device
from arcade_agent_desk.transport import device_action,load_network

class TransportTests(unittest.TestCase):
    def test_private_settings_refuse_symlinks_and_never_echo_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'network.json';file.write_text('{broken');file.chmod(0o600)
            with self.assertRaisesRegex(ValueError,'network settings'):load_network(file)
            file.write_text(json.dumps(dict(ssid='example-ssid',password='example-password',token='unused')))
            self.assertEqual(load_network(file),('example-ssid','example-password'))
            file.chmod(0o644)
            with self.assertRaises(ValueError):load_network(file)
            link=Path(tmp)/'linked';link.symlink_to(file)
            with self.assertRaises(ValueError):load_network(link)
    def test_connect_and_disconnect_use_the_selected_package_and_close_on_all_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);package=base/'paired.labapp';data=b'x'*300;package.write_bytes(data)
            network=base/'network.json';network.write_text(json.dumps(dict(ssid='example-ssid',password='example-password')));network.chmod(0o600)
            client=Device();client.rows[1]['sha256']=hashlib.sha256(data).hexdigest();events=[]
            manifest=dict(id='agent-desk',title='Agent Desk',version='1.0.0',capabilities=['draw','speaker','network','storage'])
            @contextmanager
            def connect(port):
                events.append('open')
                try:yield client
                finally:events.append('close')
            with patch('arcade_agent_desk.transport.adapter',return_value=(lambda _: (manifest,b''),connect)):
                self.assertTrue(device_action('connect','sdk',package,'port',network_path=network,peer='192.0.2.10')['connected'])
                self.assertTrue(device_action('disconnect','sdk',package,'port')['home'])
                manifest['id']='foreign'
                with self.assertRaises(ValueError):device_action('install','sdk',package,'port')
            self.assertEqual(events,['open','close','open','close'])

    def test_a_named_pipe_is_rejected_without_waiting_for_a_writer(self):
        import os,subprocess,sys
        with tempfile.TemporaryDirectory() as tmp:
            fifo=Path(tmp)/'network';os.mkfifo(fifo,0o600)
            code="from arcade_agent_desk.transport import load_network; import sys\ntry: load_network(sys.argv[1])\nexcept ValueError: raise SystemExit(0)\nraise SystemExit(1)"
            result=subprocess.run([sys.executable,'-c',code,str(fifo)],timeout=.5,capture_output=True)
            self.assertEqual(result.returncode,0)
