# Adapted from
# https://pawelmhm.github.io/python/websockets/2016/01/02/playing-with-websockets.html

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol

from collections import deque

from twisted.internet import reactor
from twisted.python import log
from twisted.web.resource import Resource
from twisted.web.server import Site

from twisted.web.client import getPage

from watcher import Watcher

import json
import pdb
import sys




class Dispatcher:
    # A note on method naming conventions.
    # _100 calls _101 as a callback
    # _200 calls _201 as a callback

    UPSTREAM = 'http://localhost:6543'

    N_OVERLAP = 10

    _CLIENTS = set()
    _RECENT_DELTAS = deque()

    @classmethod
    def add_client(cls, client):
        cls._CLIENTS.add(client)

    @classmethod
    def send_recent_deltas_to_client(cls, client):
        print(f'send_recent_deltas_to_client {len(cls._RECENT_DELTAS)} *******************************')
        for delta in cls._RECENT_DELTAS:
            cls._send_message_to_client(delta, client)

    @classmethod
    def _store_delta(cls, data_json):
        # Maintain deque of recent deltas that is up to N_OVERLAP in length
        deltas = cls._RECENT_DELTAS
        deltas.append(data_json)
        if len(deltas) > cls.N_OVERLAP:
            deltas.popleft()

    @classmethod
    def file_updated(cls):
        print('file_updated *******************************')
        cls._200_tell_upstream_to_update_redis()

    @classmethod
    def _200_tell_upstream_to_update_redis(cls):
        print('_200_tell_upstream_to_update_redis *******************************')

        # Payload from url will say which drivers changed
        url = cls._upstream_url('live/update_redis')

        d = getPage(url)
        d.addCallback(cls._201_store_delta_drivers_and_send_to_all_clients)
        d.addErrback(cls._error)

    @classmethod
    def _201_store_delta_drivers_and_send_to_all_clients(cls, data_json):
        print('_201_store_delta_drivers_and_send_to_all_clients *******************************')
        # What if pyramid-server returns an error???
        cls._store_delta(data_json)

        cls._send_message_to_clients(data_json)


    @classmethod
    def _send_message_to_client(cls, message, client):
        cls._send_message_to_clients(message, [client])

    @classmethod
    def _send_message_to_clients(cls, message, clients=[]):

        if isinstance(message, dict):
            message = json.dumps(message)

        if isinstance(message, str):
            # Convert to bytes
            message = bytes(message, encoding='utf-8')

        clients = clients or cls._CLIENTS
        print(f'_send_message_to_clients ({len(clients)} clients)  *******************************')
        for c in clients:
            c.sendMessage(message) # message is bytes

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



class SomeServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        # You cannot yet send messages to this protocol
        # Send any greetings in onOpen
        print(f'New Connection about to happen: {request}')
        Dispatcher.add_client(self)

    def onOpen(self):
        # docs for WebSocketServerProtocol indicate to send messages
        # in connectionMade callback, but inside that callback
        # sending messages results in an error ( self.state undefined )
        # Sending from onOpen appears to work

        print('CONNECTION OPEN')
        self.sendMessage(b'Connected to twisted-server')
        Dispatcher.send_recent_deltas_to_client(self)



    def onMessage(self, payload, isBinary):
        # Actual application will not use this,
        # but it is fun to watch
        message = f'Message received: {payload}'
        message_bytes = bytes(message, encoding='utf-8')
        self.sendMessage(message_bytes)

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
