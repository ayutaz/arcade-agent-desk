"""A single-writer UDP bridge. No command/output text crosses this boundary."""
import ipaddress
import errno
import math
import socket
import time
from .protocol import Notice, State, decode_hello, encode_hello, encode_notice

OFFLINE_ERRORS = frozenset(getattr(errno, name) for name in
    ('EHOSTUNREACH', 'ENETUNREACH', 'EHOSTDOWN', 'ENETDOWN', 'ECONNREFUSED') if hasattr(errno, name))


class Bridge:
    def __init__(self,key,*,bind=('127.0.0.1',50123),clock=time.monotonic):
        encode_hello(1,key)
        if (type(bind) is not tuple or len(bind)!=2 or type(bind[1]) is not int
            or not 0<=bind[1]<=65535):raise ValueError('bridge address')
        address=str(ipaddress.IPv4Address(bind[0]))
        self.key=key;self.clock=clock;self.generation=0;self.sequence=0
        self.rows={};self.peer=None;self.dirty=False;self.last_send=0;self.last_hello=0
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:self.socket.bind((address,bind[1]))
        except BaseException:self.socket.close();raise
        self.address=self.socket.getsockname()

    def __enter__(self):return self
    def __exit__(self,*args):self.socket.close()

    def update(self,task,event,progress=255):
        notice=Notice(1,1,task,event.state,progress,event.elapsed_ms)
        encode_notice(notice,self.key)
        self.rows[task]=notice;self.dirty=True

    def pump(self,timeout=.02):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<=timeout<=1:
            raise ValueError('poll deadline')
        self.socket.settimeout(timeout)
        accepted=False
        for _ in range(32):
            try:packet,source=self.socket.recvfrom(65)
            except (socket.timeout,BlockingIOError):break
            except OSError as error:
                if error.errno not in OFFLINE_ERRORS:raise
                break
            try:generation=decode_hello(packet,self.key)
            except ValueError:continue
            if (self.peer is not None and source!=self.peer and
                (self.clock()-self.last_hello<=5 or generation<=self.generation)):continue
            if generation<self.generation:continue
            self.peer=source;self.last_hello=self.clock();accepted=True
            if generation!=self.generation:self.generation=generation;self.sequence=0
        count=0
        if self.peer is not None and (accepted or (self.dirty and self.clock()-self.last_send>=.25) or self.clock()-self.last_send>=.5):
            for task,notice in sorted(self.rows.items()):
                self.sequence=self.sequence%0xffffffff+1
                from dataclasses import replace
                packet=encode_notice(replace(notice,generation=self.generation,sequence=self.sequence),self.key)
                try:self.socket.sendto(packet,self.peer)
                except OSError as error:
                    if error.errno not in OFFLINE_ERRORS:raise
                    break
                count+=1
            self.last_send=self.clock();self.dirty=False
        return count
