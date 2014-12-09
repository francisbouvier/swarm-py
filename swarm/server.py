#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import json
import random
import logging

from tornado import web
from docker import Client

logger = logging.getLogger(__name__)

SWARM_VERSION = '0.0.1'
SWARM_VERSION_GIT = 'swarm'


class ApiView(web.RequestHandler):

    def prepare(self):
        # Unify arguments loading (json, form-urlencoded) to self.arguments
        self.arguments = {}
        if self.request.arguments:
            for arg in self.request.arguments:
                value = self.get_arguments(arg)
                if len(value) == 1:
                    value = value[0]
                self.arguments[arg] = value
        else:
            try:
                self.arguments = json.loads(self.request.body)
            except ValueError:
                pass

    def write(self, data):
        self.set_header('Content-Type', 'application/json')
        super(ApiView, self).write(data)


class SwarmView(ApiView):

    def __init__(self, *args, **kwargs):
        self._swarm = kwargs.pop('swarm')
        super(SwarmView, self).__init__(*args, **kwargs)

    def _select(self):
        """Dummy random select function"""
        return random.choice(self.swarm.nodes)

    def prepare(self):
        super(SwarmView, self).prepare()
        logger.info('%s %s' % (self.request.method, self.request.uri))
        # Refresh nodes before each API call
        self._swarm.list()


class VersionView(SwarmView):

    def get(self, **kwargs):
        version = {
            'Version': 'swarm/%s' % SWARM_VERSION,
            'GitCommit': SWARM_VERSION_GIT,
        }
        self.write(version)


class InfoView(SwarmView):

    def get(self, **kwargs):
        info = {
            'Containers': 0,
            'DriverStatus': [
                [
                    'Nodes',
                    unicode(len(self._swarm.nodes))
                ],
            ],
            'NEventsListener': 0,  # TODO
            'Debug': False,
        }
        for node in self._swarm.nodes:
            node_client = Client(base_url='tcp://%s' % node)
            node_info = node_client.info()
            info['Containers'] += node_info['Containers']
            info['DriverStatus'].append(
                [node_info['Name'], 'http://%s' % node])
        self.write(info)


class ContainersView(SwarmView):

    def get(self, **kwargs):
        containers = []
        params = {
            'all': int(self.arguments.get('all', 0)),
        }
        for node in self._swarm.nodes:
            node_client = Client(base_url='tcp://%s' % node)
            node_info = node_client.info()
            node_containers = node_client.containers(**params)
            for container in node_containers:
                # Prepend Node Id in the name
                names = []
                for name in container['Names']:
                    name = '/%s%s' % (node_info['Name'], name)
                    names.append(name)
                container['Names'] = names
                # Replace IP '0.0.0.0' by Node IP
                for port in container['Ports']:
                    if port['IP'] == '0.0.0.0':
                        port['IP'] = node.split(':')[0]
                containers.append(container)
        self.write(json.dumps(containers))


class SwarmServer(web.Application):

    def __init__(self, swarm, *args, **kwargs):
        v = r'/(?P<version>v\d.\d+/){0,1}'
        urls = [
            (v + 'version', VersionView, {'swarm': swarm}),
            (v + 'info', InfoView, {'swarm': swarm}),
            (v + 'containers/json', ContainersView, {'swarm': swarm}),
        ]
        super(SwarmServer, self).__init__(urls, *args, **kwargs)
