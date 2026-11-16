"""Private pairing and deterministic builds against a pinned public SDK."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SDK_COMMIT='3bb9548846505eac303927b9064c6a8d0eb44f79'
OWNER='arcade-agent-desk-build-v1'


def private_path(path):
    path=Path(path).absolute()
    if path.is_symlink():raise ValueError('symbolic link is not a private file')
    return path.parent.resolve()/path.name


def create_key(path):
    path=private_path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        stream.write(json.dumps({'key_hex':secrets.token_hex(16)})+'\n')


def load_key(path):
    try:
        path=private_path(path)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size>256 or info.st_mode&0o077:
                raise ValueError()
            config=json.loads(stream.read(257))
        if type(config) is not dict or set(config)!={'key_hex'} or type(config['key_hex']) is not str:
            raise ValueError()
        key=bytes.fromhex(config['key_hex'])
        if len(key)!=16 or len(config['key_hex'])!=32:raise ValueError()
        return key
    except (OSError,ValueError,TypeError):raise ValueError('private pairing file unavailable or invalid') from None


def pinned_sdk(path):
    path=Path(path).absolute()
    try:
        if path.resolve()!=path:raise ValueError()
        actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
        changes=subprocess.check_output(['git','-C',str(path),'status','--porcelain','--untracked-files=no'],text=True)
        if actual!=SDK_COMMIT or changes.strip():raise ValueError()
    except (OSError,ValueError,subprocess.CalledProcessError):raise ValueError('clean pinned Scratch Arcade OS SDK required') from None
    sys.path.insert(0,str(path/'prototypes/lab-os'))
    sdk=importlib.import_module('labos.project')
    if sdk.ROOT!=path:raise ValueError('another SDK is already loaded')
    return sdk


def build_app(sdk_root,keyfile,output):
    sdk=pinned_sdk(sdk_root);key=load_key(keyfile)
    output=private_path(output)
    marker=output/'.agent-desk-owner'
    if output.exists():
        if (not marker.is_file() or marker.read_text()!=OWNER or
            any(path.is_symlink() for path in output.rglob('*'))):
            raise ValueError('output is not owned by Agent Desk')
    else:
        output.mkdir(parents=True,mode=0o700);marker.write_text(OWNER)
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        stage=Path(temporary)
        for name in ('app.c','app.json'):(stage/name).write_bytes((ROOT/'app'/name).read_bytes())
        values=','.join(str(value) for value in key)
        (stage/'desk_key.h').write_text('static const uint8_t desk_key[16]={'+values+'};\n')
        result=sdk.build_project(stage)
        package=Path(result['package']).read_bytes()
        for name in ('app.labapp','app.wasm','manifest.json'):
            target=output/name
            fd=os.open(stage/(name+'.private'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write((stage/'build'/name).read_bytes())
            os.replace(stage/(name+'.private'),target)
    config=json.loads((ROOT/'app/app.json').read_text())
    return dict(package=str(output/'app.labapp'),sha256=hashlib.sha256(package).hexdigest(),
                package_bytes=len(package),capabilities=config['capabilities'],
                sdk_commit=SDK_COMMIT,device_tested=False)
