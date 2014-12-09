#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import logging
import argparse

import requests
from tornado import ioloop
from colorlog import ColoredFormatter

from swarm.server import SwarmServer
from swarm.models import Cluster

logger = logging.getLogger('swarm')

DISCOVERY_URL = 'https://discovery-stage.hub.docker.com/v1'


class Swarm(object):

    def __init__(self, url=DISCOVERY_URL, token=None):
        self.url = url
        self.cluster = None

    def create(self):
        result = requests.post(self.url + '/clusters')
        return result.text

    def list(self):
        result = requests.get(self.url + '/clusters/' + self.cluster.token)
        self.cluster.hosts = result.json()
        if self.cluster.hosts:
            return '\n'.join(self.cluster.hosts)

    def join(self, ip, port):
        data = '%s:%s' % (ip, port)
        result = requests.post(
            self.url + '/clusters/' + self.cluster.token, data=data)
        if result.status_code == 200:
            return self.list()
        else:
            return result.text

    def manage(self, ip='127.0.0.1', port='4244'):
        app = SwarmServer(swarm=self, debug=True)
        app.listen(port=int(port), address=ip)
        ioloop.IOLoop.instance().start()

    def delete(self):
        requests.delete(self.url + '/clusters/' + self.cluster.token)


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
    swarm_manage.add_argument(
        '-u', '--url', help='Discovery API url',
        default=DISCOVERY_URL, required=False
    )

    # Delete
    swarm_delete = subparsers.add_parser('delete', help='delete')
    swarm_delete.add_argument(
        '-t', '--token', help='Token', required=True)
    swarm_delete.add_argument(
        '-u', '--url', help='Discovery API url',
        default=DISCOVERY_URL, required=False
    )

    args = parser.parse_args()

    # Logging
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = ColoredFormatter(
        '%(log_color)s%(levelname)-s%(reset)s %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Launch
    swarm = Swarm(url=args.url)

    if args.subparser_name == 'create':
        print(swarm.create())

    elif args.subparser_name == 'list':
        swarm.cluster = Cluster(args.token)
        cluster_list = swarm.list()
        if cluster_list is not None:
            print(cluster_list)

    elif args.subparser_name == 'join':
        swarm.cluster = Cluster(args.token)
        ip, port = args.addr.split(':')
        print(swarm.join(ip, port))

    elif args.subparser_name == 'manage':
        swarm.cluster = Cluster(args.token)
        ip, port = args.addr.split(':')
        swarm.manage(ip, port)

    elif args.subparser_name == 'delete':
        swarm.cluster = Cluster(args.token)
        swarm.delete()


if __name__ == "__main__":
    main()
