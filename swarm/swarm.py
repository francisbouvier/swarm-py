#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import json
import random
import argparse
from tornado import ioloop, web

import requests
from docker import Client

DISCOVERY_URL = 'https://discovery-stage.hub.docker.com/v1'


class ApiView(web.RequestHandler):

    debug = False

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

    def _select(self):
        """Dummy random select function"""
        return random.choice(self.swarm.nodes)

    def prepare(self):
        super(SwarmView, self).prepare()
        self._swarm = Swarm(self.token)


class InfoView(SwarmView):

    def get(self):
        info = {
            'Containers': 0,
            'DriverStatus': [
                [
                    'Nodes',
                    unicode(len(self._swarm.nodes))
                ],
                [],
            ],
            'NEventsListener': 0,  # TODO
            'Debug': False,
        }
        for node in self._swarm.nodes:
            node_client = Client(base_url='tcp://%s' % node)
            node_info = node_client.info()
            info['Containers'] += node_info['Containers']
            info['DriverStatus'][1].append(node_info['Name'])
            info['DriverStatus'][1].append('http://%s' % node)
        self.write(info)


URLS = [
    (r'/info', InfoView),
]


class Swarm(object):

    def __init__(self, token=None):
        self.token = token
        self.nodes = []

    def create(self):
        result = requests.post(DISCOVERY_URL + '/clusters')
        self.token = result.text
        return self.token

    def list(self):
        result = requests.get(DISCOVERY_URL + '/clusters/' + self.token)
        self.nodes = result.json()
        return self.nodes

    def join(self, ip, port):
        data = '%s:%s' % (ip, port)
        requests.post(DISCOVERY_URL + '/clusters/' + self.token, data=data)
        self.list()
        return self.nodes

    def manage(self, ip='127.0.0.1', port='4244'):
        app = web.Application(URLS)
        app.listen(port=int(port), address=ip)
        ioloop.IOLoop.instance().start()

    def delete(self):
        requests.delete(DISCOVERY_URL + '/clusters/' + self.token)


def main():

    # Command
    parser = argparse.ArgumentParser(
        description='Swarm (python)')
    subparsers = parser.add_subparsers(
        title='sub-commands', dest='subparser_name', help='sub-command help')

    # Create
    subparsers.add_parser('create', help='Create')

    # List
    swarm_list = subparsers.add_parser('list', help='List')
    swarm_list.add_argument(
        '-t', '--token', help='Token', required=True)

    # Join
    swarm_join = subparsers.add_parser('join', help='Join')
    swarm_join.add_argument(
        '-t', '--token', help='Token', required=True)
    swarm_join.add_argument(
        '-a', '--addr', help='Address', required=True)

    # Manage
    swarm_manage = subparsers.add_parser('manage', help='Manage')
    swarm_manage.add_argument(
        '-t', '--token', help='Token', required=True)
    swarm_manage.add_argument(
        '-a', '--addr', help='Address', required=True)

    # Delete
    swarm_delete = subparsers.add_parser('delete', help='delete')
    swarm_delete.add_argument(
        '-t', '--token', help='Token', required=True)

    # Launch
    args = parser.parse_args()
    swarm = Swarm()

    if args.subparser_name == 'create':
        print(swarm.create())

    elif args.subparser_name == 'list':
        swarm.token = args.token
        print(swarm.list())

    elif args.subparser_name == 'join':
        swarm.token = args.token
        ip, port = args.addr.split(':')
        print(swarm.join(ip, port))

    elif args.subparser_name == 'manage':
        swarm.token = args.token
        ip, port = args.addr.split(':')
        swarm.manage(ip, port)

    elif args.subparser_name == 'delete':
        swarm.token = args.token
        swarm.delete()


if __name__ == "__main__":
    main()
