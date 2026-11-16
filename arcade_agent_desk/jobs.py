"""Run up to four explicit local jobs; deliver numeric events on one writer thread."""
from concurrent.futures import ThreadPoolExecutor
import math
import queue
import threading
from .runner import run_command


def validate_jobs(jobs):
    if type(jobs) is not list or not 1<=len(jobs)<=4:raise ValueError('one to four jobs')
    seen=set();result=[]
    for row in jobs:
        if type(row) is not dict or set(row)!={'task','command','timeout'}:raise ValueError('job schema')
        task=row['task'];command=row['command'];timeout=row['timeout']
        if type(task) is not int or not 1<=task<=4 or task in seen:raise ValueError('unique task id')
        if (type(command) is not list or not command or len(command)>128 or
            any(type(arg) is not str or not arg or '\0' in arg or len(arg)>4096 for arg in command) or
            type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=3600):
            raise ValueError('job command/deadline bounds')
        seen.add(task);result.append(dict(task=task,command=list(command),timeout=timeout))
    return result


def run_jobs(jobs,*,on_event,stop=None):
    jobs=validate_jobs(jobs)
    if not callable(on_event):raise ValueError('event sink')
    stop=threading.Event() if stop is None else stop
    if not callable(getattr(stop,'is_set',None)) or not callable(getattr(stop,'set',None)):raise ValueError('stop event')
    events=queue.Queue();results={}
    def worker(row):
        return run_command(row['command'],timeout=row['timeout'],heartbeat=.05,cancel=stop,
                           on_event=lambda event:events.put((row['task'],event)))
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures={pool.submit(worker,row):row['task'] for row in jobs}
        try:
            while futures or not events.empty():
                try:
                    try:message=events.get(timeout=.01)
                    except queue.Empty:message=None
                    if message is not None:on_event(*message)
                    for future,task in list(futures.items()):
                        if future.done():results[task]=future.result();del futures[future]
                except KeyboardInterrupt:stop.set()
        except BaseException:
            stop.set();raise
    return dict(sorted(results.items()))
