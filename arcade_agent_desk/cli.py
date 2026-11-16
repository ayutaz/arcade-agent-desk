"""Run an explicit argv locally and send only numeric task state to the handheld."""
import argparse
import json
import math
import sys
import time
from .bridge import Bridge
from .build import build_app, create_key, load_key
from .runner import run_command


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
    args=parser.parse_args(argv)
    try:
        if args.action=='pair':
            create_key(args.key);print('Local pairing file created; keep it private.',file=out);return 0
        if args.action=='build':
            print(json.dumps(build_app(args.sdk,args.key,args.output)),file=out);return 0
        command=args.command[1:] if args.command[:1]==['--'] else args.command
        if not math.isfinite(args.linger) or not 0<=args.linger<=60:
            raise ValueError('linger must be between 0 and 60 seconds')
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
