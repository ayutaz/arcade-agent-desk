"""RAM-only radio setup and finite input for the exact owned Agent Desk app."""
import ipaddress
import re
import time


def _home(status):
    return status['mode']==0 and not status['held'] and not status['remaining_ms'] and not status['active_id']


def _catalog(client,app_sha):
    if type(app_sha) is not str or not re.fullmatch('[0-9a-f]{64}',app_sha):raise ValueError('owned package hash')
    rows=client.list_apps()
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('catalog')
    app=next((r for r in rows if r['id']=='agent-desk'),None)
    if app is None or app['sha256']!=app_sha:raise ValueError('installed Agent Desk does not match the selected package')
    return rows


def _same(client,rows):
    if sorted(client.list_apps(),key=lambda r:r['id'])!=sorted(rows,key=lambda r:r['id']):raise RuntimeError('catalog changed; stop')


def _wait(get,predicate,seconds,clock,sleep):
    end=clock()+seconds
    for _ in range(3000):
        if clock()>=end:break
        value=get()
        if predicate(value):return value
        sleep(.01)
    raise RuntimeError('device deadline; stop without retrying the operation')


def _pulse(client,held,clock,sleep):
    before=client.control_status()
    if (before['held'] or before['remaining_ms'] or
        not (_home(before) or (before['mode']==1 and before['active_id']=='agent-desk'))):raise RuntimeError('device input ownership changed')
    ack=client.input_pulse(held,duration_ms=80);generation=ack['generation']
    def released(status):
        if status['generation']!=generation:raise RuntimeError('input generation changed')
        return not status['held'] and not status['remaining_ms'] and status['applied']!=before['applied']
    return _wait(client.control_status,released,3,clock,sleep)


def link_owned(client,ssid,password,peer,peer_port,*,app_sha,clock=time.monotonic,sleep=time.sleep):
    try:
        ip=ipaddress.IPv4Address(peer)
        if ip.is_multicast or ip.is_unspecified or ip.is_loopback or ip.is_reserved or int(ip)==0xffffffff:raise ValueError()
        if type(peer_port) is not int or not 1<=peer_port<=65535:raise ValueError()
        if type(ssid) is not str or type(password) is not str:raise ValueError()
        raw=ssid.encode('utf-8');secret=password.encode('ascii')
        if not 1<=len(raw)<=32 or not 8<=len(secret)<=63 or any(c<32 or c==127 for c in raw) or any(c<32 or c>126 for c in secret):raise ValueError()
    except (ValueError,UnicodeError):raise ValueError('network settings unavailable or invalid') from None
    if not _home(client.control_status()):raise ValueError('HOME with released keys required')
    rows=_catalog(client,app_sha)
    if client.network_status()['state']!=0:raise ValueError('existing radio connection is not owned by this call')
    requested=started=launched=False
    try:
        requested=True;client.network_start(ssid,password);started=True
        def associated(status):
            if status['state'] not in (0,1,2):raise RuntimeError('wireless association failed')
            return status['state']==2
        _wait(client.network_status,associated,25,clock,sleep)
        client.network_route(str(ip),peer_port,local_port=0)
        target=next(i for i,row in enumerate(rows) if row['id']=='agent-desk')
        for _ in range(17):
            _same(client,rows);status=client.control_status()
            if not _home(status):raise RuntimeError('HOME ownership changed')
            if status['selected']==target:break
            _pulse(client,4,clock,sleep)
        else:raise RuntimeError('selection did not converge')
        status=_pulse(client,16,clock,sleep)
        if status['mode']!=1 or status['active_id']!='agent-desk':raise RuntimeError('owned app did not launch')
        launched=True
        _wait(client.network_channel_status,lambda s:s['state']==1,3,clock,sleep)
        return dict(connected=True,active_id='agent-desk',catalog_count=len(rows),firmware_updated=False)
    except BaseException:
        if (requested and not started) or getattr(client,'failed',False):
            raise RuntimeError('link outcome uncertain; inspect device without retrying') from None
        if started:
            try:
                status=client.control_status()
                if launched and status['mode']==1 and status['active_id']=='agent-desk':
                    _pulse(client,192,clock,sleep);status=_wait(client.control_status,_home,3,clock,sleep)
                if not _home(status):raise RuntimeError('ownership changed')
                _same(client,rows)
                client.network_stop()
                _wait(client.network_status,lambda s:s['state']==0,3,clock,sleep)
                _wait(client.network_channel_status,lambda s:s['state']==0,3,clock,sleep)
            except BaseException:raise RuntimeError('link failed and cleanup is unconfirmed; inspect device') from None
        raise


def unlink_owned(client,*,app_sha,clock=time.monotonic,sleep=time.sleep):
    status=client.control_status()
    if status['held'] or status['remaining_ms']:raise ValueError('released keys required')
    if status['mode']==1 and status['active_id']=='agent-desk':
        _pulse(client,192,clock,sleep);status=_wait(client.control_status,_home,3,clock,sleep)
    if not _home(status):raise ValueError('only HOME or the owned Agent Desk app can be disconnected')
    rows=_catalog(client,app_sha)
    client.network_stop()
    _wait(client.network_status,lambda s:s['state']==0,3,clock,sleep)
    _wait(client.network_channel_status,lambda s:s['state']==0,3,clock,sleep)
    _same(client,rows)
    return dict(home=True,radio_stopped=True,catalog_count=len(rows))
