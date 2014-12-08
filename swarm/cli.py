#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import argparse
import requests
from tornado import ioloop

from swarm.server import SwarmServer

DISCOVERY_URL = 'https://discovery-stage.hub.docker.com/v1'


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
