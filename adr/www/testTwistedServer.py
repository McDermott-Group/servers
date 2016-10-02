import sys
import json
from twisted.web.static import File
from twisted.python import log
from twisted.web.server import Site
from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol

from autobahn.twisted.resource import WebSocketResource

from datetime import datetime


class MyServerProtocol(WebSocketServerProtocol):
    def onOpen(self):
        self.factory.register(self)
        print('new connection')
        from time import sleep
        sleep(4)
        print('sending message')
        message = json.dumps( {
                    'compressorOn':True,
                    'instruments':{
                        'Ruox Temperature Monitor':{'server':True,'connected':False},
                        'Compressor':{'server':True,'connected':True}
                    },
                    'pressure':769,
                    'backEMF':0.101,
                    'PSVoltage':1.7,
                    'PSCurrent':8.7,
                    'log':[ {'datetime':(datetime.now()-datetime(1970,1,1)).total_seconds()+10*i,'message':'hellow world','alert':False} for i in range(9)]
                } )
        self.sendMessage(message)
        """
        from random import random
        from datetime import datetime
        for _ in range(1000):
            sleep(2)
            print('adding temps')
            message = json.dumps( {
                'temps': {
                    'timeStamps':[(datetime.now()-datetime(1970,1,1)).total_seconds()],
                    't60K': [20.+random()],
                    't03K': [15.+random()],
                    'tGGG': [10.+random()],
                    'tFAA': [5.+random()]
                }
            })
            self.sendMessage(message)
        """

    def connectionLost(self, reason):
        self.factory.unregister(self)
        print('connection lost')

    def onMessage(self, payload, isBinary):
        print(json.loads(payload))

class MyFactory(WebSocketServerFactory):
    def __init__(self, *args, **kwargs):
        super(MyFactory, self).__init__(*args, **kwargs)
        self.clients = {}

    def register(self, client):
        self.clients[client.peer] = client

    def unregister(self, client):
        self.clients.pop(client.peer)


if __name__ == "__main__":
    log.startLogging(sys.stdout)

    # static file server seving index.html as root
    root = File(".")

    factory = MyFactory(u"ws://127.0.0.1:9876/")
    factory.protocol = MyServerProtocol
    resource = WebSocketResource(factory)
    # websockets resource on "/ws" path
    root.putChild(u"ws", resource)

    site = Site(root)
    reactor.listenTCP(9876, site)
    reactor.run()
