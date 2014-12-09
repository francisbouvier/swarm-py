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
