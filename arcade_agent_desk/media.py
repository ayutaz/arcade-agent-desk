"""Replay public synthetic notices in the actual WASM app, without a device."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from .build import build_app
from .protocol import Notice,State,encode_notice


class _Storage:
    def call(self,op,slot,value):return (1,0 if op==1 else value)


class _Audio:
    def call(self,op,a,b):return 0 if op==4 else 1


class _Network:
    def __init__(self):self.queue=[]
    def call(self,op,data,count):
        if op in (1,3):return 1
        if not self.queue:return 0
        packet=self.queue.pop(0);data[:len(packet)]=packet;return len(packet)


def render_demo(sdk_root,output):
    output=Path(output).absolute()
    if output.resolve()!=output or output.exists():raise ValueError('fresh real media output required')
    key=bytes(range(16))  # Public demo fixture only; never a production pairing key.
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp).resolve();keyfile=base/'fixture.json'
        keyfile.write_text(json.dumps(dict(key_hex=key.hex())));keyfile.chmod(0o600)
        built=build_app(sdk_root,keyfile,base/'app')
        decode=importlib.import_module('labos.package').decode
        Session=importlib.import_module('labos.sdk').Session
        render=importlib.import_module('labos.display').render
        manifest,blob=decode((base/'app/app.labapp').read_bytes())
        network=_Network();session=Session(blob,manifest,network=network,state=_Storage(),audio=_Audio())
        images={};frames=[]
        try:
            for seq,state in enumerate((State.WORK,State.DONE,State.FAIL,State.WAIT,State.CANCEL),1):
                network.queue.append(encode_notice(Notice(1,seq,1,state,50 if state==State.WORK else 100,seq*100),key))
                session.frame(0,seq*20)
                if session.debug('debug_value')!=state:raise ValueError('WASM replay state mismatch')
                images[state.name]=render(SimpleNamespace(mode='running',commands=session.commands))
                frames.append(images[state.name])
            session.frame(0,5200)
            if session.debug('debug_value')!=State.LOST:raise ValueError('WASM replay did not expire')
            images['LOST']=render(SimpleNamespace(mode='running',commands=session.commands));frames.append(images['LOST'])
            if not session.frame(192,5220):raise ValueError('WASM replay did not exit')
        finally:session.close()
    output.mkdir(parents=True)
    for state,image in images.items():image.save(output/(state.lower()+'.png'))
    frames[0].save(output/'replay.gif',save_all=True,append_images=frames[1:],duration=700,loop=0,disposal=2)
    result=dict(source='actual WASM with synthetic notices',device_capture=False,real_jobs=False,
                states=list(images),package_sha256=built['sha256'])
    (output/'media.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(json.dumps(render_demo(args.sdk,args.output)))
