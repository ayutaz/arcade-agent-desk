import hashlib
import unittest
from arcade_agent_desk.deploy import install_owned

PACKAGE=b'validated fixture'
HASH=hashlib.sha256(PACKAGE).hexdigest()
MANIFEST=dict(id='agent-desk',version='1.0.0',title='Agent Desk')

class Client:
    def __init__(self):
        self.rows=[dict(id='old-game',version='1.0.0',title='Existing',sha256='a'*64)]
        self.mode=0;self.held=0;self.installs=0;self.corrupt=False
    def control_status(self):return dict(mode=self.mode,held=self.held,remaining_ms=0,active_id='')
    def list_apps(self):return [dict(row) for row in self.rows]
    def install(self,package):
        self.installs+=1
        self.rows=[row for row in self.rows if row['id']!='agent-desk']
        self.rows.append(dict(MANIFEST,sha256=HASH))
        if self.corrupt:self.rows[0]['sha256']='b'*64

class DeployTests(unittest.TestCase):
    def test_new_app_only_and_exact_hash_update(self):
        client=Client();baseline=client.list_apps()
        result=install_owned(client,PACKAGE,lambda _: (MANIFEST,b''))
        self.assertEqual(result['sha256'],HASH);self.assertEqual(client.rows[0],baseline[0])
        with self.assertRaises(ValueError):install_owned(client,PACKAGE,lambda _: (MANIFEST,b''))
        install_owned(client,PACKAGE,lambda _: (MANIFEST,b''),previous_sha=HASH)
        self.assertEqual(client.installs,2)

    def test_foreign_package_active_keys_wrong_hash_full_catalog_rejected_before_write(self):
        for failure in ('id','mode','held','hash','full'):
            client=Client();manifest=dict(MANIFEST)
            if failure=='id':manifest['id']='old-game'
            if failure=='mode':client.mode=1
            if failure=='held':client.held=1
            if failure=='hash':client.rows.append(dict(MANIFEST,sha256='c'*64))
            if failure=='full':client.rows*=16
            with self.assertRaises(ValueError):install_owned(client,PACKAGE,lambda _: (manifest,b''),previous_sha='a'*64)
            self.assertEqual(client.installs,0)

    def test_other_app_change_is_reported_without_deleting_anything(self):
        client=Client();client.corrupt=True
        with self.assertRaises(RuntimeError):install_owned(client,PACKAGE,lambda _: (MANIFEST,b''))
        self.assertEqual(client.installs,1);self.assertEqual(len(client.rows),2)

if __name__=='__main__':unittest.main()
