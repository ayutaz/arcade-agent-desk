import socket
import unittest

from arcade_agent_desk.bridge import Bridge
from arcade_agent_desk.protocol import Notice, State, decode_notice, encode_hello
from arcade_agent_desk.runner import Event

KEY=bytes(range(16))


class BridgeTests(unittest.TestCase):
    def test_reconnect_requires_expired_peer_and_new_generation(self):
        clock=[0.0]
        with Bridge(KEY,bind=('127.0.0.1',0),clock=lambda:clock[0]) as bridge, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as first, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as second:
            for peer in (first,second):peer.bind(('127.0.0.1',0));peer.settimeout(.05)
            bridge.update(1,Event(State.WORK,1))
            first.sendto(encode_hello(7,KEY),bridge.address);bridge.pump();first.recvfrom(64)
            clock[0]=6
            second.sendto(encode_hello(7,KEY),bridge.address);bridge.pump()
            self.assertEqual(bridge.peer,first.getsockname())
            second.sendto(encode_hello(8,KEY),bridge.address);bridge.pump()
            self.assertEqual(bridge.peer,second.getsockname())
            self.assertEqual(decode_notice(second.recvfrom(64)[0],KEY).generation,8)

    def test_real_udp_hello_authenticated_state_and_generation_change(self):
        with Bridge(KEY,bind=('127.0.0.1',0)) as bridge, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as device:
            device.bind(('127.0.0.1',0));device.settimeout(.3)
            bridge.update(2,Event(State.WORK,123))
            device.sendto(encode_hello(7,KEY),bridge.address)
            self.assertEqual(bridge.pump(),1)
            packet,_=device.recvfrom(64);notice=decode_notice(packet,KEY)
            self.assertEqual((notice.generation,notice.task,notice.state,notice.elapsed_ms),(7,2,State.WORK,123))
            device.sendto(encode_hello(7,KEY),bridge.address);bridge.pump()
            repeated=decode_notice(device.recvfrom(64)[0],KEY)
            self.assertGreater(repeated.sequence,notice.sequence)
            device.sendto(encode_hello(8,KEY),bridge.address);bridge.pump()
            fresh=decode_notice(device.recvfrom(64)[0],KEY)
            self.assertEqual((fresh.generation,fresh.sequence),(8,1))

    def test_wrong_key_foreign_peer_and_old_generation_do_not_change_route(self):
        with Bridge(KEY,bind=('127.0.0.1',0)) as bridge, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as device, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as foreign:
            for peer in (device,foreign):peer.bind(('127.0.0.1',0));peer.settimeout(.05)
            bridge.update(1,Event(State.DONE,10))
            foreign.sendto(encode_hello(9,b'0'*16),bridge.address);self.assertEqual(bridge.pump(),0)
            device.sendto(encode_hello(7,KEY),bridge.address);bridge.pump();device.recvfrom(64)
            foreign.sendto(encode_hello(8,KEY),bridge.address);self.assertEqual(bridge.pump(),0)
            device.sendto(encode_hello(6,KEY),bridge.address);self.assertEqual(bridge.pump(),0)
            self.assertEqual(bridge.generation,7)

    def test_task_bounds_and_socket_close(self):
        bridge=Bridge(KEY,bind=('127.0.0.1',0))
        with bridge:
            with self.assertRaises(ValueError):bridge.update(5,Event(State.DONE,1))
        self.assertEqual(bridge.socket.fileno(),-1)


if __name__=='__main__':unittest.main()
