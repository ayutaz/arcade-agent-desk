"""Explicit serial actions through the pinned OS; credentials remain local/RAM-only."""
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
from .build import pinned_sdk
from .deploy import install_owned
from .device import link_owned,unlink_owned


def _read(path,maximum,minimum=1,*,private=False):
    path=Path(path)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not minimum<=info.st_size<=maximum or (private and info.st_mode&0o077):
            raise ValueError('regular bounded private file required')
        raw=stream.read(maximum+1)
    if len(raw)!=info.st_size:raise ValueError('file changed while reading')
    return raw


def load_network(path):
    try:
        config=json.loads(_read(path,4096,private=True))
        if type(config) is not dict or type(config.get('ssid')) is not str or type(config.get('password')) is not str:raise ValueError()
        return config['ssid'],config['password']
    except (OSError,ValueError,TypeError):raise ValueError('network settings unavailable or invalid') from None


def adapter(sdk_root):
    pinned_sdk(sdk_root);decode=importlib.import_module('labos.package').decode
    module=importlib.import_module('labos.transfer')
    @contextmanager
    def connect(port):
        with module.serial_connection(port) as stream:
            client=module.Client(stream,timeout=4)
            try:client.connect();yield client
            finally:client.close()
    return decode,connect


def device_action(action,sdk_root,package_path,port,*,previous_sha=None,network_path=None,peer=None,peer_port=50123):
    if action not in ('install','connect','disconnect'):raise ValueError('device action')
    package=_read(package_path,16384,264)
    decode,connect=adapter(sdk_root);manifest,_=decode(package)
    if manifest['id']!='agent-desk' or manifest['capabilities']!=['draw','speaker','network','storage']:
        raise ValueError('paired Agent Desk package required')
    digest=hashlib.sha256(package).hexdigest()
    settings=load_network(network_path) if action=='connect' else None
    with connect(port) as client:
        if action=='install':return install_owned(client,package,decode,previous_sha=previous_sha)
        if action=='connect':return link_owned(client,*settings,peer,peer_port,app_sha=digest)
        return unlink_owned(client,app_sha=digest)
