#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import json
import random
import logging
from collections import OrderedDict

from tornado import web
from docker import Client

logger = logging.getLogger(__name__)

SWARM_VERSION = '0.0.1'
SWARM_VERSION_GIT = 'swam'


class ApiView(web.RequestHandler):

    def prepare(self):
        # Unify arguments loading (json, form-urlencoded) to self.arguments
        content_type = self.request.headers.get("Content-Type")
        if content_type is not None:
            self.arguments = {}
            if content_type.startswith('application/x-www-form-urlencoded'):
                for arg in self.request.arguments:
                    value = self.get_arguments(arg)
                    if len(value) == 1:
                        value = value[0]
                    self.arguments[arg] = value
            elif content_type.startswith('application/json'):
                self.arguments = json.loads(self.request.body)

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
        # Refresh nodes before each API call
        self._swarm.list()


class VersionView(SwarmView):

    def get(self):
        logger.info('GET /version')
        version = OrderedDict()
        version['Version'] = 'swarm/%s' % SWARM_VERSION
        version['GitCommit'] = SWARM_VERSION_GIT
        self.write(version)


class InfoView(SwarmView):

    def get(self):
        logger.info('GET /info')
        info = OrderedDict()
        info['Containers'] = 0
        info['DriverStatus'] = [
            [
                'Nodes',
                unicode(len(self._swarm.nodes))
            ],
        ]
        info['NEventsListener'] = 0  # TODO
        info['Debug'] = False
        for node in self._swarm.nodes:
            node_client = Client(base_url='tcp://%s' % node)
            node_info = node_client.info()
            info['Containers'] += node_info['Containers']
            info['DriverStatus'].append(
                [node_info['Name'], 'http://%s' % node])
        self.write(info)


class SwarmServer(web.Application):

    def __init__(self, swarm, *args, **kwargs):
        urls = [
            (r'/version', VersionView, {'swarm': swarm}),
            (r'/info', InfoView, {'swarm': swarm}),
        ]
        super(SwarmServer, self).__init__(urls, *args, **kwargs)
