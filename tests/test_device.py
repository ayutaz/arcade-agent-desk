import unittest
from arcade_agent_desk.device import link_owned,unlink_owned

SHA='a'*64
class Device:
    def __init__(self):
        self.rows=[dict(id='old-app',title='Old',version='1.0.0',sha256='b'*64),dict(id='agent-desk',title='Agent Desk',version='1.0.0',sha256=SHA)]
        self.s=dict(mode=0,held=0,remaining_ms=0,active_id='',selected=0,generation=0,applied=0)
        self.radio=0;self.starts=self.stops=0;self.pulses=[];self.fail_radio=False;self.routes=0
    def control_status(self):return dict(self.s)
    def list_apps(self):
        if self.s['mode']!=0:raise RuntimeError('catalog BUSY while guest is active')
        return [dict(row) for row in self.rows]
    def network_status(self):return dict(state=3 if self.fail_radio and self.radio else self.radio,ipv4=1 if self.radio==2 else 0)
    def network_start(self,*_):self.starts+=1;self.radio=2
    def network_stop(self):self.stops+=1;self.radio=0
    def network_route(self,*args,**kwargs):self.routes+=1
    def network_channel_status(self):
        active=self.radio==2 and self.s['mode']==1 and self.s['active_id']=='agent-desk'
        return dict(state=1 if active else 0,port=1234 if active else 0)
    def input_pulse(self,held,*,duration_ms):
        self.pulses.append(held);self.s['generation']+=1;self.s['applied']+=1
        if held==4:self.s['selected']=(self.s['selected']+1)%len(self.rows)
        if held==16:self.s.update(mode=1,active_id=self.rows[self.s['selected']]['id'])
        if held==192:self.s.update(mode=0,active_id='')
        return dict(self.s)

class DeviceTests(unittest.TestCase):
    def test_link_launch_and_disconnect_preserve_catalog_without_reboot_or_install(self):
        client=Device();before=client.list_apps()
        result=link_owned(client,'example-ssid','example-password','192.0.2.10',50123,app_sha=SHA)
        self.assertTrue(result['connected']);self.assertEqual(client.s['active_id'],'agent-desk')
        self.assertEqual(client.pulses,[4,16]);self.assertEqual(client.rows,before)
        result=unlink_owned(client,app_sha=SHA)
        self.assertTrue(result['home']);self.assertEqual(client.radio,0);self.assertEqual(client.pulses[-1],192)
        self.assertEqual(client.list_apps(),before)
    def test_wrong_hash_foreign_active_keys_existing_radio_and_invalid_input_never_start_wifi(self):
        for mode in ('hash','active','held','radio','peer','ssid','password'):
            client=Device();sha=SHA;peer='192.0.2.10';ssid='example-ssid';password='example-password'
            if mode=='hash':sha='c'*64
            if mode=='active':client.s.update(mode=1,active_id='old-app')
            if mode=='held':client.s['held']=16
            if mode=='radio':client.radio=2
            if mode=='peer':peer='invalid'
            if mode=='ssid':ssid=''
            if mode=='password':password='short'
            with self.assertRaises(ValueError):link_owned(client,ssid,password,peer,50123,app_sha=sha)
            self.assertEqual(client.starts,0);self.assertEqual(client.stops,0);self.assertEqual(client.pulses,[])
    def test_failed_association_stops_only_the_connection_started_by_this_call(self):
        client=Device();client.fail_radio=True
        with self.assertRaises(RuntimeError):link_owned(client,'example-ssid','example-password','192.0.2.10',50123,app_sha=SHA)
        self.assertEqual((client.starts,client.stops,client.routes),(1,1,0));self.assertEqual(client.pulses,[])
    def test_disconnect_never_exits_an_unrelated_app(self):
        client=Device();client.s.update(mode=1,active_id='old-app')
        with self.assertRaises(ValueError):unlink_owned(client,app_sha=SHA)
        self.assertEqual(client.pulses,[]);self.assertEqual(client.stops,0)

    def test_failed_radio_cleanup_is_not_reported_as_a_confirmed_stop(self):
        client=Device();client.fail_radio=True;clock=[0.0]
        def failed_stop():client.stops+=1
        client.network_stop=failed_stop
        def sleep(seconds):clock[0]+=seconds
        with self.assertRaisesRegex(RuntimeError,'cleanup is unconfirmed'):
            link_owned(client,'example-ssid','example-password','192.0.2.10',50123,app_sha=SHA,clock=lambda:clock[0],sleep=sleep)
        self.assertEqual(client.stops,1)

    def test_udp_socket_is_waited_for_after_the_guest_acquires_its_lease(self):
        client=Device();clock=[0.0]
        client.network_channel_status=lambda:dict(state=1 if client.radio==2 and client.s['mode']==1 else 0,port=1234 if client.s['mode']==1 else 0)
        def sleep(seconds):clock[0]+=seconds
        result=link_owned(client,'example-ssid','example-password','192.0.2.10',50123,app_sha=SHA,clock=lambda:clock[0],sleep=sleep)
        self.assertTrue(result['connected']);self.assertEqual(client.pulses,[4,16])

    def test_catalog_is_read_only_at_home_and_disconnect_closes_owned_app_before_checking_hash(self):
        client=Device();original=client.list_apps
        def only_home():
            if client.s['mode']!=0:raise RuntimeError('catalog BUSY while guest is active')
            return original()
        client.list_apps=only_home
        self.assertTrue(link_owned(client,'example-ssid','example-password','192.0.2.10',50123,app_sha=SHA)['connected'])
        self.assertTrue(unlink_owned(client,app_sha=SHA)['home'])

    def test_disconnect_waits_for_async_cleanup_to_reach_home(self):
        client=Device();client.s.update(mode=1,active_id='agent-desk');original_pulse=client.input_pulse;reads=[0]
        def pulse(held,**kwargs):
            result=original_pulse(held,**kwargs)
            if held==192:client.s['mode']=2;client.s['active_id']='agent-desk'
            return result
        def status():
            if client.s['mode']==2:
                reads[0]+=1
                if reads[0]>=3:client.s.update(mode=0,active_id='')
            return dict(client.s)
        client.input_pulse=pulse;client.control_status=status
        self.assertTrue(unlink_owned(client,app_sha=SHA)['home'])
