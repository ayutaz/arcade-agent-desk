import dataclasses
import struct
import unittest

from arcade_agent_desk.protocol import (
    Notice, State, Tracker, decode_hello, decode_notice, encode_hello,
    encode_notice, siphash,
)

KEY = bytes(range(16))


class ProtocolTests(unittest.TestCase):
    def test_siphash_reference_vectors(self):
        self.assertEqual(siphash(KEY, b''), 0x726fdb47dd0e0e31)
        self.assertEqual(siphash(KEY, bytes(range(15))), 0xa129ca6149be45e5)

    def test_authenticated_bounded_packets_roundtrip(self):
        notice = Notice(7, 1, 2, State.WORK, 40, 1234, 5000)
        packet = encode_notice(notice, KEY)
        self.assertEqual(len(packet), 40)
        self.assertEqual(decode_notice(packet, KEY), notice)
        self.assertEqual(decode_hello(encode_hello(7, KEY), KEY), 7)
        self.assertEqual(len(encode_hello(7, KEY)), 16)

    def test_corruption_wrong_key_bounds_and_reserved_fields_rejected(self):
        original = encode_notice(Notice(1, 1, 1, State.WORK), KEY)
        for index in range(len(original)):
            packet = bytearray(original); packet[index] ^= 1
            with self.assertRaises(ValueError): decode_notice(bytes(packet), KEY)
        for packet in (original[:-1], original + b'x'):
            with self.assertRaises(ValueError): decode_notice(packet, KEY)
        with self.assertRaises(ValueError): decode_notice(original, b'0' * 16)
        for change in ({'generation': 0}, {'sequence': 0}, {'task': 5},
                       {'progress': 101}, {'ttl_ms': 999}, {'state': 6},
                       {'elapsed_ms': -1}, {'sequence': True}):
            with self.assertRaises(ValueError):
                encode_notice(dataclasses.replace(Notice(1, 1, 1, State.WORK), **change), KEY)
        for key in (b'', b'0' * 15, b'0' * 17):
            with self.assertRaises(ValueError): encode_hello(1, key)
        reserved = bytearray(original[:32]); reserved[22] = 1
        packet = bytes(reserved) + struct.pack('<Q', siphash(KEY, reserved))
        with self.assertRaises(ValueError): decode_notice(packet, KEY)

    def test_generation_replay_sequence_wrap_expiry_and_selection(self):
        now = [0.0]
        tracker = Tracker(7, clock=lambda: now[0])
        def send(seq, task=1, state=State.WORK, generation=7):
            return tracker.accept(encode_notice(Notice(generation, seq, task, state), KEY), KEY)
        self.assertFalse(send(1, generation=6))
        self.assertTrue(send(0xffffffff))
        self.assertTrue(send(1, 2, State.DONE))
        self.assertFalse(send(0xffffffff))
        now[0] = 4
        self.assertFalse(send(1, 2, State.DONE))
        now[0] = 5.01
        self.assertEqual(tracker.view(2)['state'], State.LOST)
        self.assertTrue(send(2, 2, State.FAIL))
        self.assertEqual(tracker.view(2)['state'], State.FAIL)
        self.assertEqual(tracker.next_task(), 2)
        self.assertEqual(tracker.next_task(), 1)


if __name__ == '__main__': unittest.main()
