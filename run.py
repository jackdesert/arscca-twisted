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

from watcher import Watcher
from util import Util

import json
import pdb
import sys
import treq




class Dispatcher:
    # Callback Chain Naming Convention
    # _100 calls _101 as a callback

    class UpstreamError(Exception):
        '''Used to indicate a network call failed'''

    UPSTREAM = 'http://localhost:6543'

    N_OVERLAP = 10

    _CLIENTS = set()
    _RECENT_DELTAS = deque()

    @classmethod
    def add_client(cls, client):
        cls._CLIENTS.add(client)

    @classmethod
    def remove_client(cls, client):
        cls._CLIENTS.remove(client)

    @classmethod
    def send_recent_deltas_to_client(cls, client):
        print(f'send_recent_deltas_to_client. deltas: {len(cls._RECENT_DELTAS)}, clients: {len(cls._CLIENTS)} *******************************')
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

        d = treq.get(url, timeout=10)
        d.addCallback(cls._201_verify_status_code_and_read_response, url)
        d.addErrback(cls._error)

    @classmethod
    def _201_verify_status_code_and_read_response(cls, response, url):
        print('_201_verify_status_code_and_read_response *******************************')

        # treq is strict about deferreds.
        # That is, we have access to the status code here,
        # but to get the respones body, we must use a callback.
        code = response.code
        if code == 200:
            d = response.text()
            d.addCallback(cls._202_store_delta_and_send_to_all_clients)
            d.addErrback(cls._error)
        else:
            exc = cls.UpstreamError(f'Status code {code} accessing {url.decode()}')
            Util.post_to_slack(exc)

    @classmethod
    def _202_store_delta_and_send_to_all_clients(cls, delta_json):
        print('_202_store_delta_and_send_to_all_clients *******************************')
        cls._store_delta(delta_json)
        cls._send_message_to_clients(delta_json)

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
        Util.post_to_slack(exc)


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
        Dispatcher.send_recent_deltas_to_client(self)

    def onClose(self, wasClean, code, reason):
        print(f'Removing Client. wasClean: {wasClean}, code: {code}, reason: {reason}')
        # If client loses network, this appears not to fire.
        # Is it a problem if there are many (say two hundred) open connections
        # and a bunch of them have lost network?
        Dispatcher.remove_client(self)

    def onMessage(self, payload, isBinary):
        # Actual application will not use this,
        # but it is fun to watch
        message = f'Message received: {payload}'
        message_bytes = bytes(message, encoding='utf-8')
        self.sendMessage(message_bytes)

if __name__ == "__main__":
    log.startLogging(sys.stdout)

    root = Resource()

    factory = WebSocketServerFactory("ws://127.0.0.1:6544")
    factory.protocol = SomeServerProtocol
    resource = WebSocketResource(factory)
    # websockets resource on "/ws" path
    root.putChild(b"ws", resource)

    watcher = Watcher(Dispatcher.file_updated)
    watcher.watch()

    site = Site(root)
    reactor.listenTCP(6544, site)
    reactor.run()
