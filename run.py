"""
This file represents the controller/view of this twisted project

Adapted from
https://pawelmhm.github.io/python/websockets/2016/01/02/playing-with-websockets.html
"""

from collections import deque
import json
import treq

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from twisted.internet import reactor
from twisted.python import log
from twisted.python.logfile import DailyLogFile
from twisted.web.resource import Resource
from twisted.web.server import Site

from watcher import Watcher
from util import Util


class Dispatcher:
    """
    Callback Chain Naming Convention
    _100 calls _101 as a callback
    """

    class UpstreamError(Exception):
        '''Used to indicate a network call failed'''

    UPSTREAM = 'http://arscca-pyramid:6543'

    # If there are no CPU burst credits on the AWS box,
    # arscca-pyramid running on a t2.nano takes 15 seconds to parse
    # one event with 66 drivers.
    # Ideally, we run the demo with a period great enough that we
    # do not deplete the CPU burst credits. But if we have depleted
    # them, it makes sense to offer a timeout greater than the time
    # required to complete the request at the base CPU rate.
    # (nano has a 5% base rate)
    UPSTREAM_TIMEOUT_SECONDS = 30

    N_OVERLAP = 10

    _CLIENTS = set()
    _RECENT_DELTAS = deque()

    @classmethod
    def add_client(cls, client):
        """
        Add a client to the pool
        """
        cls._CLIENTS.add(client)

    @classmethod
    def remove_client(cls, client):
        """
        Remove a client from the pool
        """
        cls._CLIENTS.remove(client)

    @classmethod
    def send_recent_deltas_to_client(cls, client):
        """
        Sends recent deltas to a single client
        """
        num_deltas = len(cls._RECENT_DELTAS)
        num_clients = len(cls._CLIENTS)
        print(
            f'send_recent_deltas_to_client. deltas: {num_deltas}, clients: {num_clients} *******'
        )
        for delta in cls._RECENT_DELTAS:
            cls._send_message_to_single_client(delta, client)

    @classmethod
    def _store_delta(cls, data_json):
        """
        Maintain deque of recent deltas that is up to N_OVERLAP in length
        """
        deltas = cls._RECENT_DELTAS
        deltas.append(data_json)
        if len(deltas) > cls.N_OVERLAP:
            deltas.popleft()

    @classmethod
    def file_updated(cls):
        """
        The Watcher calls this method when it sees that a file has been updated
        """
        print('file_updated *******************************')
        cls._200_tell_upstream_to_update_redis()

    @classmethod
    def _200_tell_upstream_to_update_redis(cls):
        """
        Note the number in the method. That shows you the order
        Upstream in this case is arscca-pyramid.
        """
        print('_200_tell_upstream_to_update_redis *******************************')

        # Payload from url will say which drivers changed
        url = cls._upstream_url('live/update_redis')

        d = treq.get(url, timeout=cls.UPSTREAM_TIMEOUT_SECONDS)
        d.addCallback(cls._201_verify_status_code_and_read_response, url)
        d.addErrback(cls._error)

    @classmethod
    def _201_verify_status_code_and_read_response(cls, response, url):
        """
        Note the number in the method. That shows you the order
        """

        print(
            '_201_verify_status_code_and_read_response *******************************'
        )

        # treq is strict about deferreds.
        # That is, we have access to the status code here,
        # but to get the response body, we must use a callback.
        code = response.code
        if code == 200:
            d = response.text()
            d.addCallback(cls._202_store_delta_and_send_to_all_clients)
            d.addErrback(cls._error)
        elif code == 429:
            print(
                '429 Error: Pyramid was unable to keep up, so this request was dropped'
            )
        else:
            exc = cls.UpstreamError(f'Status code {code} accessing {url.decode()}')
            Util.post_to_slack(exc)

    @classmethod
    def _202_store_delta_and_send_to_all_clients(cls, delta_json):
        """
        Note the number in the method. That shows you the order
        """
        print(
            '_202_store_delta_and_send_to_all_clients *******************************'
        )
        cls._store_delta(delta_json)
        cls._send_message_to_clients(delta_json)

    @classmethod
    def _send_message_to_single_client(cls, message, client):
        cls._send_message_to_clients(message, [client])

    @classmethod
    def _send_message_to_clients(cls, message, clients=None):

        if isinstance(message, dict):
            message = json.dumps(message)

        if isinstance(message, str):
            # Convert to bytes
            message = bytes(message, encoding='utf-8')

        clients = clients or cls._CLIENTS
        print(
            f'_send_message_to_clients ({len(clients)} clients)  *******************************'
        )
        for c in clients:
            c.sendMessage(message)  # message is bytes

    @classmethod
    def _upstream_url(cls, path):
        url = f'{cls.UPSTREAM}/{path}'
        url_bytes = bytes(url, encoding='utf-8')
        return url_bytes

    @classmethod
    def _error(cls, exc):
        print(f'ERROR: {exc} *****************************')
        Util.post_to_slack(exc)


# pylint: disable=too-many-ancestors
class SomeServerProtocol(WebSocketServerProtocol):
    """
    Websocket callbacks
    """

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


class StatusPage(Resource):
    """
    This status is page is here so we can monitor that the service is up

    see https://twistedmatrix.com/documents/current/web/howto/using-twistedweb.html
    """

    isLeaf = True

    # pylint: disable=unused-argument,no-self-use
    def render_GET(self, request):
        """
        Return a simple html document
        """
        return b'<html><body><h1>Serving</h1></body></html>'


if __name__ == '__main__':
    log.startLogging(DailyLogFile.fromFullPath('/tmp/arscca-twisted.log'))

    root = Resource()

    factory = WebSocketServerFactory('ws://127.0.0.1:6544')
    factory.protocol = SomeServerProtocol
    resource = WebSocketResource(factory)

    # websockets resource on '/ws' path
    root.putChild(b'ws', resource)

    # status page on '/' path
    status_page = StatusPage()
    root.putChild(b'', status_page)

    watcher = Watcher(Dispatcher.file_updated)
    watcher.watch()

    site = Site(root)
    # Not sure why pylint thinks these next two methods don't exist
    # pylint: disable=no-member
    reactor.listenTCP(6544, site)
    # pylint: disable=no-member
    reactor.run()
