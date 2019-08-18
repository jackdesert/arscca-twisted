# Adapted from
# https://pawelmhm.github.io/python/websockets/2016/01/02/playing-with-websockets.html

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol

from twisted.internet import reactor
from twisted.python import log
from twisted.web.resource import Resource
from twisted.web.server import Site

from watcher import Watcher

import sys
import pdb

connections = set()

def send_driver_diff():
    global connections
    for c in connections:
        c.sendMessage(b'New Drivers!!')


class SomeServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        connections.add(self)
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

    watcher = Watcher(send_driver_diff)
    watcher.watch()

    site = Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()
