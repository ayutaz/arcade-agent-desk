"""Run an explicit argv locally and send only numeric task state to the handheld."""
import argparse
import json
import math
from pathlib import Path
import stat
import sys
import time
from .bridge import Bridge
from .build import build_app, create_key, load_key
from .runner import run_command
from .jobs import run_jobs,validate_jobs


def main(argv=None,*,out=None):
    out=out or sys.stdout
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    pair=sub.add_parser('pair',help='create a local 0600 pairing key once')
    pair.add_argument('--key',required=True)
    build=sub.add_parser('build',help='build the paired app using a clean pinned OS checkout')
    build.add_argument('--sdk',required=True);build.add_argument('--key',required=True)
    build.add_argument('--output',default='build/paired')
    run=sub.add_parser('run',help='run a command without a shell and relay its real exit status')
    run.add_argument('--key',required=True);run.add_argument('--bind',default='127.0.0.1')
    run.add_argument('--port',type=int,default=50123);run.add_argument('--task',type=int,choices=range(1,5),default=1)
    run.add_argument('--timeout',type=float,default=3600);run.add_argument('--linger',type=float,default=3)
    run.add_argument('command',nargs=argparse.REMAINDER)
    watch=sub.add_parser('watch',help='run one to four explicit jobs through a single state bridge')
    watch.add_argument('--key',required=True);watch.add_argument('--jobs',required=True,type=Path)
    watch.add_argument('--bind',default='127.0.0.1');watch.add_argument('--port',type=int,default=50123)
    watch.add_argument('--linger',type=float,default=3)
    args=parser.parse_args(argv)
    try:
        if args.action=='pair':
            create_key(args.key);print('Local pairing file created; keep it private.',file=out);return 0
        if args.action=='build':
            print(json.dumps(build_app(args.sdk,args.key,args.output)),file=out);return 0
        if not math.isfinite(args.linger) or not 0<=args.linger<=60:
            raise ValueError('linger must be between 0 and 60 seconds')
        if args.action=='watch':
            info=args.jobs.stat()
            if args.jobs.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size>16384:raise ValueError('job file')
            raw=args.jobs.read_bytes()
            if len(raw)!=info.st_size:raise ValueError('job file changed')
            config=json.loads(raw)
            if type(config) is not dict or set(config)!={'jobs'}:raise ValueError('job file schema')
            jobs=validate_jobs(config['jobs'])
            with Bridge(load_key(args.key),bind=(args.bind,args.port)) as bridge:
                def event(task,row):bridge.update(task,row);bridge.pump(.001)
                codes=run_jobs(jobs,on_event=event)
                end=time.monotonic()+args.linger
                while time.monotonic()<end:bridge.pump(min(.02,max(0,end-time.monotonic())))
                print(json.dumps(dict(task_exit_codes=codes,device_connected=bridge.peer is not None)),file=out)
            return 1 if any(codes.values()) else 0
        command=args.command[1:] if args.command[:1]==['--'] else args.command
        with Bridge(load_key(args.key),bind=(args.bind,args.port)) as bridge:
            def event(row):
                bridge.update(args.task,row);bridge.pump(.01)
            code=run_command(command,on_event=event,timeout=args.timeout)
            end=time.monotonic()+args.linger
            while time.monotonic()<end:bridge.pump(min(.02,end-time.monotonic()) if end>time.monotonic() else 0)
            print(json.dumps(dict(exit_code=code,device_connected=bridge.peer is not None)),file=out)
            return code
    except (OSError,ValueError):
        print('Unable to continue: check the private pairing file, options, SDK and local port.',file=out)
        return 2


if __name__=='__main__':raise SystemExit(main())
