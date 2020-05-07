#!/usr/bin/env python3

import json
import os
import os.path as path
import paho.mqtt.client as mqtt
import re
import subprocess
import time


MQTT_HOST = 'mqtt.bitlair.nl'
AP_DIR    = path.join(path.dirname(__file__), 'access_points.d')


def read_ap(filepath):
    regexp_mac = re.compile('^(:?[0-9a-f]{2}:){5}[0-9a-f]{2}$')
    associations = json.loads(subprocess.check_output([ filepath ]).decode('utf8'))
    assert type(associations) is list, 'The value returned by the AP driver is not a list'

    def valid(assoc):
        return type(assoc['mac']) is str \
            and regexp_mac.match(assoc['mac']) \
            and type(assoc['ssid']) is str and len(assoc['ssid']) > 1
    return [ assoc for assoc in associations if valid(assoc)]

class Activity(object):

    def __init__(self, driver_directory):
        self.associations = {}
        if driver_directory == "":
            return
        for ap_driver in os.listdir(driver_directory):
            filepath = path.join(driver_directory, ap_driver)
            if os.access(filepath, os.X_OK):
                self.associations.update({ assoc['mac']: assoc for assoc in read_ap(filepath) })

    def ssids(self):
        return { assoc['ssid'] for assoc in self.associations.values() }

    def macs(self):
        return self.associations.keys()

    def diff(self, prev_activity):
        macs_joined = self.macs() - prev_activity.macs()
        macs_parted = prev_activity.macs() - self.macs()
        return {
            'joined': [ self.associations[mac] for mac in macs_joined ],
            'parted': [ prev_activity.associations[mac] for mac in macs_parted ],
        }


def hook_print(activity, prev_activity, diff):
    print('')
    print('total online: %s' % len(activity.associations))
    if len(diff['joined']) > 0:
        print('joined: %s' % ', '.join([ '%s on %s' % (assoc['mac'], assoc['ssid']) for assoc in diff['joined'] ]))
    if len(diff['parted']) > 0:
        print('parted: %s' % ', '.join([ '%s on %s' % (assoc['mac'], assoc['ssid']) for assoc in diff['parted'] ]))

def hook_mqtt(activity, prev_activity, diff):
    normalize_ssid = lambda s: s.lower().replace(' ', '-')
    mqttc.publish('bitlair/wifi/all/online', len(activity.associations), retain=True)
    for ssid in activity.ssids() | prev_activity.ssids():
        online_count = sum(assoc['ssid'] == ssid for assoc in activity.associations.values())
        mqttc.publish('bitlair/wifi/%s/online' % normalize_ssid(ssid), str(online_count), retain=True)
    for assoc in diff['joined']:
        signal = assoc['signal'] if 'signal' in assoc else '-'
        payload = 'join %s %s' % (assoc['mac'], signal)
        mqttc.publish('bitlair/wifi/%s' % normalize_ssid(assoc['ssid']), payload)
    for assoc in diff['parted']:
        mqttc.publish('bitlair/wifi/%s' % normalize_ssid(assoc['ssid']), 'part %s' % assoc['mac'])


if __name__ == '__main__':
    mqttc = mqtt.Client()
    mqttc.connect(MQTT_HOST)
    mqttc.loop_start()

    prev_activity = Activity('')
    while True:
        try:
            activity = Activity(AP_DIR)
        except Exception as err:
            print(err)
            time.sleep(1)
            continue

        diff = activity.diff(prev_activity)
        hooks = [
#            hook_print,
            hook_mqtt,
        ]
        for hook in hooks:
            hook(activity, prev_activity, diff)

        prev_activity = activity
        time.sleep(30)
