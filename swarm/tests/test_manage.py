#! /usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals

import unittest

import json
import requests


class SwarmManageTest(unittest.TestCase):

    go = '2375'
    python = '2376'

    def get_url(self, version):
        return 'http://localhost:%s/v1.15/' % getattr(self, version)

    def test_info(self):
        g = requests.get(self.get_url('go') + 'info')
        # Hack : strange encoding in Swarm Go
        g_text = g.text.replace('\\u0008', '')
        g_json = json.loads(g_text)
        # Hack : Swarm Go does not seem to sort nodes
        nodes = g_json['DriverStatus'][1:]
        nodes.sort(key=lambda x: x[1])
        g_json['DriverStatus'][1:] = nodes

        p = requests.get(self.get_url('python') + 'info')
        self.assertEqual(p.json(), g_json)

    def test_version(self):
        g = requests.get(self.get_url('go') + 'version')
        # Hack : swarm-py does not have 'GoVersion'
        g_json = g.json()
        del g_json['GoVersion']
        p = requests.get(self.get_url('python') + 'version')
        self.assertEqual(p.json(), g_json)

    def test_containers(self, params=''):
        g = requests.get(self.get_url('go') + 'containers/json' + params)
        # Hack : swarm-py doesn't handle 'SizeRw' and 'SizeRootFs'
        # (docker client version ?)
        g_json = g.json()
        for container in g_json:
            del container['SizeRw']
            del container['SizeRootFs']
        p = requests.get(self.get_url('python') + 'containers/json' + params)
        self.assertEqual(p.json(), g_json)

    def test_containers_all(self):
        self.test_containers(params='?all=1')

    def test_container(self):
        pk = '9be8b99fc891c6e653da3f05f0e71e1cb38cce9353f331c3981bbe8bda8ba729'
        extra_url = 'containers/%s/json' % pk
        g = requests.get(self.get_url('go') + extra_url)
        p = requests.get(self.get_url('go') + extra_url)
        self.assertEqual(p.json(), g.json())
