#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import logging
from docker import Client

logger = logging.getLogger(__name__)


class Cluster(object):

    def __init__(self, token):
        self.token = token
        self.hosts = []
        self.nodes = {}
        self.clients = {}

    def refresh_clients(self):
        for host in self.hosts:
            if host not in self.clients:
                self.clients[host] = Client(base_url='tcp://%s' % host)

    def refresh_nodes(self):
        self.refresh_clients()
        for host in self.hosts:
            if host not in self.nodes:
                self.nodes[host] = Node(
                    host=host, info=self.clients[host].info())

    def refresh_containers(self):
        self.refresh_nodes()
        for host in self.hosts:
            node = self.nodes[host]
            node.containers = []
            params = {'all': 1}
            for container in self.clients[host].containers(**params):
                # Prepend Node Id in the name
                names = []
                for name in container['Names']:
                    name = '/%s%s' % (node.info['Name'], name)
                    names.append(name)
                container['Names'] = names
                # Replace IP '0.0.0.0' by Node IP
                for port in container['Ports']:
                    if port['IP'] == '0.0.0.0':
                        port['IP'] = host.split(':')[0]
                node.containers.append(
                    Container(id=container['Id'], cluster=self,
                              host=host, info=container))

    def find_container(self, container_id):
        for host in self.hosts:
            for container in self.nodes[host].containers:
                if container.id == container_id:
                    return container
        return None


class Node(object):

    def __init__(self, host, info):
        self.host = host
        self.info = info
        self.containers = []


class Container(object):

    def __init__(self, id, cluster, host, info):
        self.id = id
        self.cluster = cluster
        self.host = host
        self.info = info
        self.extra = {}

    @property
    def is_up(self):
        return self.info['Status'].startswith('Up')

    @property
    def inspect(self):
        if not self.extra:
            self.inspect_container()
        return self.extra

    def inspect_container(self):
        self.extra = self.cluster.clients[self.host].inspect_container(self.id)
