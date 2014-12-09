#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import json
import random
import logging

from tornado import web

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
        self.cluster = kwargs.pop('cluster')
        super(SwarmView, self).__init__(*args, **kwargs)

    def _select(self):
        """Dummy random select function"""
        return random.choice(self.cluster.hosts)

    def prepare(self):
        super(SwarmView, self).prepare()
        logger.info('%s %s' % (self.request.method, self.request.uri))
        # Refresh hosts before each API call
        # TODO: check to implement a refresh async version with heartbeat
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
                    unicode(len(self.cluster.hosts))
                ],
            ],
            'NEventsListener': 0,  # TODO
            'Debug': False,
        }
        # TODO: use an event system to triger changes
        self.cluster.refresh_nodes()
        for host in self.cluster.hosts:
            node = self.cluster.nodes[host]
            info['Containers'] += node.info['Containers']
            info['DriverStatus'].append(
                [node.info['Name'], 'http://%s' % host])
        self.write(info)


class ContainersView(SwarmView):

    def get(self, **kwargs):
        containers = []
        params = {
            'all': int(self.arguments.get('all', 0)),
        }
        # TODO: use an event system to triger changes
        self.cluster.refresh_containers()
        for host in self.cluster.hosts:
            for container in self.cluster.nodes[host].containers:
                if params['all'] == 0:
                    if container.is_up:
                        containers.append(container.info)
                else:
                    containers.append(container.info)
        self.write(json.dumps(containers))


class SwarmServer(web.Application):

    def __init__(self, swarm, *args, **kwargs):
        v = r'/(?P<version>v\d.\d+/){0,1}'
        extra = {'swarm': swarm, 'cluster': swarm.cluster}
        urls = [
            (v + 'version', VersionView, extra),
            (v + 'info', InfoView, extra),
            (v + 'containers/json', ContainersView, extra),
        ]
        super(SwarmServer, self).__init__(urls, *args, **kwargs)
