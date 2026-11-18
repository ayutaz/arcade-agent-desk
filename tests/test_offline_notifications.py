"""通知先の切断が実作業を取り消さず、認証/再送の条件も保つ契約。"""
import errno
import socket
import sys
import unittest
from unittest.mock import Mock

from arcade_agent_desk.bridge import Bridge
from arcade_agent_desk.protocol import State, decode_notice, encode_hello
from arcade_agent_desk.runner import Event, run_command

KEY = bytes(range(16))


class OfflineNotificationTests(unittest.TestCase):
    def test_unreachable_receiver_does_not_cancel_a_real_local_job(self):
        with Bridge(KEY, bind=('127.0.0.1', 0)) as bridge, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as device:
            device.bind(('127.0.0.1', 0)); device.settimeout(.1)
            device.sendto(encode_hello(7, KEY), bridge.address); bridge.pump(.01)
            original = bridge.socket
            bridge.socket = Mock(wraps=original)
            bridge.socket.sendto.side_effect = OSError(errno.EHOSTUNREACH, 'fixture unreachable')
            bridge.last_send -= 1  # initial heartbeat must exercise the failed delivery
            def report(event):
                bridge.update(1, event)
                bridge.pump(0)
            code = run_command([sys.executable, '-c', 'import time; time.sleep(.06)'],
                               timeout=2, heartbeat=.01, on_event=report)
            self.assertEqual(code, 0)
            self.assertEqual(bridge.rows[1].state, State.DONE)
            self.assertGreaterEqual(bridge.socket.sendto.call_count, 1)
            self.assertLessEqual(bridge.socket.sendto.call_count, 2)

    def test_receive_error_does_not_reset_authentication_or_lose_pending_status(self):
        now = [0.]
        with Bridge(KEY, bind=('127.0.0.1', 0), clock=lambda: now[0]) as bridge, \
             socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as first, \
             socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as second:
            for peer in (first, second): peer.bind(('127.0.0.1', 0)); peer.settimeout(.1)
            bridge.update(1, Event(State.WORK, 0))
            first.sendto(encode_hello(7, KEY), bridge.address); bridge.pump(); first.recvfrom(64)
            original = bridge.socket; bridge.socket = Mock(wraps=original)
            bridge.socket.recvfrom.side_effect = OSError(errno.ECONNREFUSED, 'fixture offline')
            now[0] = .1
            self.assertEqual(bridge.pump(0), 0)
            self.assertEqual(bridge.generation, 7)
            self.assertEqual(bridge.peer, first.getsockname())
            bridge.socket = original
            second.sendto(encode_hello(8, KEY), bridge.address); bridge.pump(.02)
            self.assertEqual(bridge.peer, first.getsockname())  # five-second lease still applies
            now[0] = 6.
            second.sendto(encode_hello(7, KEY), bridge.address); bridge.pump(.02)
            self.assertEqual(bridge.peer, first.getsockname())
            second.sendto(encode_hello(8, KEY), bridge.address); bridge.pump()
            self.assertEqual(bridge.peer, second.getsockname())
            self.assertEqual(decode_notice(second.recvfrom(64)[0], KEY).state, State.WORK)

    def test_unexpected_socket_errors_remain_fatal(self):
        with Bridge(KEY, bind=('127.0.0.1', 0)) as bridge:
            original = bridge.socket; bridge.socket = Mock(wraps=original)
            bridge.socket.recvfrom.side_effect = OSError(errno.EBADF, 'fixture broken descriptor')
            with self.assertRaises(OSError): bridge.pump(0)


if __name__ == '__main__': unittest.main()
