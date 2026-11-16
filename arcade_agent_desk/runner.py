"""Report only task states; do not capture command text, output or credentials."""
from dataclasses import dataclass
import math
import os
import signal
import subprocess
import time
from .protocol import State


@dataclass(frozen=True)
class Event:
    state: State
    elapsed_ms: int


def run_command(argv,*,on_event,timeout=3600,heartbeat=.5):
    if (type(argv) is not list or not argv or any(type(arg) is not str or not arg or '\0' in arg for arg in argv)
        or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=86400
        or not .01<=heartbeat<=5):
        raise ValueError('command/timeout bounds')
    started=time.monotonic()
    def emit(state):on_event(Event(state,int((time.monotonic()-started)*1000)))
    emit(State.WORK)
    try: process=subprocess.Popen(argv,start_new_session=True)
    except OSError:
        emit(State.FAIL);return 127
    def terminate():
        if process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=.25)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait(timeout=1)
    try:
        while True:
            left=timeout-(time.monotonic()-started)
            if left<=0:
                terminate();emit(State.FAIL);return 124
            try:code=process.wait(timeout=min(left,heartbeat));break
            except subprocess.TimeoutExpired:emit(State.WORK)
        emit(State.DONE if code==0 else State.FAIL)
        return code if code>=0 else 128-code
    except KeyboardInterrupt:
        terminate();emit(State.CANCEL);return 130
    finally:terminate()
