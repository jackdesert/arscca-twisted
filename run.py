# Adapted from
# https://pawelmhm.github.io/python/websockets/2016/01/02/playing-with-websockets.html

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol

from twisted.internet import reactor
from twisted.python import log
from twisted.web.resource import Resource
from twisted.web.server import Site

from twisted.web.client import getPage

from watcher import Watcher

import json
import pdb
import sys

connections = set()


class Dispatcher:

    UPSTREAM = 'http://localhost:6543'

    connections = set()

    @classmethod
    def add_connection(cls, connection):
        cls.connections.add(connection)

    @classmethod
    def file_updated(cls):
        print('file_updated *******************************')
        cls._tell_upstream_to_update_redis()

    @classmethod
    def _tell_upstream_to_update_redis(cls):
        print('tell_upstream_to_update_redis *******************************')

        # Payload from url will say which drivers changed
        url = cls._upstream_url('live/update_redis')

        d = getPage(url)
        d.addCallback(cls._send_delta_drivers_to_all_clients)
        d.addErrback(cls._error)

    @classmethod
    def _send_delta_drivers_to_all_clients(cls, data_json):
        print('send_delta_drivers_to_all_clients *******************************')
        data = json.loads(data_json)
        message = dict(source='server',
                       action='update_drivers',
                       data=data)

        cls._send_message_to_all_clients(message)

    @classmethod
    def _send_message_to_all_clients(cls, message):
        count = len(cls.connections)
        print(f'_send_message_to_all_clients ({count} clients)  *******************************')

        if isinstance(message, dict):
            message = json.dumps(message)
        message_bytes = bytes(message, encoding='utf-8')

        for c in cls.connections:
            c.sendMessage(message_bytes)

    @classmethod
    def _upstream_url(cls, path):
        url = f'{cls.UPSTREAM}/{path}'
        url_bytes = bytes(url, encoding='utf-8')
        return url_bytes

    @classmethod
    def _error(cls, exc):
        print(f'ERROR: {exc} *****************************')
        pdb.set_trace()
        1


######


def send_driver_diff(revision):
    global connections
    message = f'New Drivers for revision {revision}'
    message_bytes = bytes(message, encoding='utf-8')
    for c in connections:
        c.sendMessage(message_bytes)


class SomeServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        Dispatcher.add_connection(self)
        print("some request connected {}".format(request))


    def onMessage(self, payload, isBinary):
        self.sendMessage(b"message received")



if __name__ == "__main__":
    log.startLogging(sys.stdout)

    root = Resource()

    factory = WebSocketServerFactory("ws://127.0.0.1:8080")
    factory.protocol = SomeServerProtocol
    resource = WebSocketResource(factory)
    # websockets resource on "/ws" path
    root.putChild(b"ws", resource)

    watcher = Watcher(Dispatcher.file_updated)
    watcher.watch()

    site = Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()
