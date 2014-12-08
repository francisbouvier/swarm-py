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


class SwarmServer(web.Application):

    def __init__(self, swarm, *args, **kwargs):
        urls = [
            (r'/info', InfoView, {'swarm': swarm}),
        ]
        super(SwarmServer, self).__init__(urls, *args, **kwargs)


class Swarm(object):

    def __init__(self, token=None):
        self.token = token
        self.nodes = []

    def create(self, url):
        result = requests.post(url + '/clusters')
        self.token = result.text
        return self.token

    def list(self, url):
        result = requests.get(url + '/clusters/' + self.token)
        self.nodes = result.json()
        if self.nodes:
            return '\n'.join(self.nodes)

    def join(self, url, ip, port):
        data = '%s:%s' % (ip, port)
        result = requests.post(url + '/clusters/' + self.token, data=data)
        if result.status_code == 200:
            return self.list(url)
        else:
            return result.text

    def manage(self, ip='127.0.0.1', port='4244'):
        app = SwarmServer(swarm=self, debug=True)
        app.listen(port=int(port), address=ip)
        ioloop.IOLoop.instance().start()

    def delete(self, url):
        requests.delete(url + '/clusters/' + self.token)


def main():

    # Command
    parser = argparse.ArgumentParser(
        description='Swarm (python)')
    subparsers = parser.add_subparsers(
        title='sub-commands', dest='subparser_name', help='sub-command help')

    # Create
    swarm_create = subparsers.add_parser('create', help='Create')
    swarm_create.add_argument(
        '-u', '--url', help='Discovery API url',
        default=DISCOVERY_URL, required=False
    )

    # List
    swarm_list = subparsers.add_parser('list', help='List')
    swarm_list.add_argument(
        '-t', '--token', help='Token', required=True)
    swarm_list.add_argument(
        '-u', '--url', help='Discovery API url',
        default=DISCOVERY_URL, required=False
    )

    # Join
    swarm_join = subparsers.add_parser('join', help='Join')
    swarm_join.add_argument(
        '-t', '--token', help='Token', required=True)
    swarm_join.add_argument(
        '-a', '--addr', help='Address', required=True)
    swarm_join.add_argument(
        '-u', '--url', help='Discovery API url',
        default=DISCOVERY_URL, required=False
    )

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
    swarm_delete.add_argument(
        '-u', '--url', help='Discovery API url',
        default=DISCOVERY_URL, required=False
    )

    # Launch
    args = parser.parse_args()
    swarm = Swarm()

    if args.subparser_name == 'create':
        print(swarm.create(args.url))

    elif args.subparser_name == 'list':
        swarm.token = args.token
        cluster_list = swarm.list(args.url)
        if cluster_list is not None:
            print(cluster_list)

    elif args.subparser_name == 'join':
        swarm.token = args.token
        ip, port = args.addr.split(':')
        print(swarm.join(args.url, ip, port))

    elif args.subparser_name == 'manage':
        swarm.token = args.token
        ip, port = args.addr.split(':')
        swarm.manage(ip, port)

    elif args.subparser_name == 'delete':
        swarm.token = args.token
        swarm.delete(args.url)


if __name__ == "__main__":
    main()
