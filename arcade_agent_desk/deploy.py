"""Install only Agent Desk, preserving the complete unrelated app catalog."""
import hashlib
import re


def install_owned(client,package,decode,*,previous_sha=None):
    manifest,_=decode(package)
    if manifest['id']!='agent-desk' or len(package)>16384:
        raise ValueError('Agent Desk package required')
    if previous_sha is not None and (type(previous_sha) is not str or not re.fullmatch('[0-9a-f]{64}',previous_sha)):
        raise ValueError('previous package hash required')
    status=client.control_status()
    if status['mode']!=0 or status['held'] or status['remaining_ms'] or status['active_id']:
        raise ValueError('HOME with released keys required')
    before=client.list_apps()
    if len({row['id'] for row in before})!=len(before):raise ValueError('invalid catalog')
    existing=next((row for row in before if row['id']=='agent-desk'),None)
    if existing is not None and existing['sha256']!=previous_sha:
        raise ValueError('exact previous Agent Desk hash required')
    if existing is None and len(before)>=16:raise ValueError('catalog is full')
    others=[row for row in before if row['id']!='agent-desk']
    client.install(package)
    after=client.list_apps()
    actual=next((row for row in after if row['id']=='agent-desk'),None)
    expected=dict(id='agent-desk',title=manifest['title'],version=manifest['version'],
                  sha256=hashlib.sha256(package).hexdigest())
    if (actual!=expected or len(after)!=len(others)+1 or
        sorted((row for row in after if row['id']!='agent-desk'),key=lambda row:row['id'])!=sorted(others,key=lambda row:row['id'])):
        raise RuntimeError('catalog invariant failed; stop and inspect, do not retry or remove apps')
    return actual
