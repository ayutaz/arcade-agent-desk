"""ADS1: a 40-byte authenticated notification, plus launch-generation hello."""
from dataclasses import dataclass, replace
from enum import IntEnum
import hmac
import struct
import time

MASK = (1 << 64) - 1
BODY = struct.Struct('<4sIIII4BII')


def siphash(key, message):
    """SipHash-2-4; the published reference vectors are tested independently."""
    if type(key) is not bytes or len(key) != 16:
        raise ValueError('16-byte pairing key required')
    k0, k1 = struct.unpack('<QQ', key)
    v = [0x736f6d6570736575 ^ k0, 0x646f72616e646f6d ^ k1,
         0x6c7967656e657261 ^ k0, 0x7465646279746573 ^ k1]
    def rotate(value, bits): return ((value << bits) | (value >> (64-bits))) & MASK
    def round_():
        v[0] = (v[0]+v[1]) & MASK; v[1] = rotate(v[1],13)^v[0]; v[0]=rotate(v[0],32)
        v[2] = (v[2]+v[3]) & MASK; v[3] = rotate(v[3],16)^v[2]
        v[0] = (v[0]+v[3]) & MASK; v[3] = rotate(v[3],21)^v[0]
        v[2] = (v[2]+v[1]) & MASK; v[1] = rotate(v[1],17)^v[2]; v[2]=rotate(v[2],32)
    offset=0
    while offset+8 <= len(message):
        block=int.from_bytes(message[offset:offset+8],'little'); offset+=8
        v[3]^=block; round_(); round_(); v[0]^=block
    block=(len(message)&255)<<56 | int.from_bytes(message[offset:],'little')
    v[3]^=block; round_(); round_(); v[0]^=block; v[2]^=255
    for _ in range(4): round_()
    return v[0]^v[1]^v[2]^v[3]


class State(IntEnum):
    WORK=1
    DONE=2
    FAIL=3
    WAIT=4
    CANCEL=5
    LOST=6  # Local display state, never accepted from the wire.


@dataclass(frozen=True)
class Notice:
    generation: int
    sequence: int
    task: int
    state: State
    progress: int = 255
    elapsed_ms: int = 0
    ttl_ms: int = 5000


def validate(notice):
    if type(notice) is not Notice: raise ValueError('notice required')
    bounds = ((notice.generation,1,0x7fffffff),(notice.sequence,1,0xffffffff),
              (notice.task,1,4),(notice.elapsed_ms,0,0xffffffff),(notice.ttl_ms,1000,30000))
    if any(type(value) is not int or not lo<=value<=hi for value,lo,hi in bounds):
        raise ValueError('notice bounds')
    if type(notice.state) not in (int,State) or not 1<=notice.state<=5:
        raise ValueError('notice state')
    if type(notice.progress) is not int or not (0<=notice.progress<=100 or notice.progress==255):
        raise ValueError('progress')
    return notice


def signed(body,key): return body+struct.pack('<Q',siphash(key,body))


def verified(packet, key, size):
    if type(packet) is not bytes or len(packet)!=size: raise ValueError('packet framing')
    if not hmac.compare_digest(packet[-8:],struct.pack('<Q',siphash(key,packet[:-8]))):
        raise ValueError('packet authentication')
    return packet[:-8]


def encode_notice(notice,key):
    validate(notice)
    return signed(BODY.pack(b'ADS1',notice.generation,notice.sequence,notice.task,
                           notice.elapsed_ms,notice.state,notice.progress,0,0,notice.ttl_ms,0),key)


def decode_notice(packet,key):
    magic,generation,seq,task,elapsed,state,progress,r0,r1,ttl,r2=BODY.unpack(verified(packet,key,40))
    if magic!=b'ADS1' or r0 or r1 or r2: raise ValueError('packet version/reserved')
    return validate(Notice(generation,seq,task,state,progress,elapsed,ttl))


def encode_hello(generation,key):
    if type(generation) is not int or not 1<=generation<=0x7fffffff:
        raise ValueError('launch generation')
    return signed(struct.pack('<4sI',b'ADH1',generation),key)


def decode_hello(packet,key):
    magic,generation=struct.unpack('<4sI',verified(packet,key,16))
    if magic!=b'ADH1':raise ValueError('hello framing')
    encode_hello(generation,key)
    return generation


class Tracker:
    def __init__(self,generation,*,clock=time.monotonic):
        encode_hello(generation,bytes(16))
        self.generation=generation;self.clock=clock;self.sequence=0
        self.rows={};self.selected=1

    def accept(self,packet,key):
        try: notice=decode_notice(packet,key)
        except ValueError:return False
        distance=(notice.sequence-self.sequence)&0xffffffff
        if notice.generation!=self.generation or (self.sequence and not 0<distance<0x80000000):
            return False
        self.sequence=notice.sequence
        self.rows[notice.task]=(notice,self.clock())
        if len(self.rows)==1:self.selected=notice.task
        return True

    def view(self,task=None):
        task=self.selected if task is None else task
        if task not in self.rows:return dict(task=task,state=State.LOST,progress=255,elapsed_ms=0)
        notice,received=self.rows[task]
        state=State.LOST if (self.clock()-received)*1000>=notice.ttl_ms else notice.state
        return dict(task=task,state=state,progress=notice.progress,elapsed_ms=notice.elapsed_ms)

    def next_task(self):
        tasks=sorted(self.rows)
        if tasks:self.selected=tasks[(tasks.index(self.selected)+1)%len(tasks)]
        return self.selected
