#!/usr/bin/python3

import socket
import asyncio
import ipaddress
import sys
import logging

def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(screen_handler)
    return logger

LOGGER = setup_custom_logger("proxy")

ACCEPTED_NETWORK = ipaddress.IPv4Network("142.39.0.0/16")

class ProxyClientProtocol(asyncio.Protocol):
    def __init__(self, transport):
        self.transport = transport

    def data_received(self, data):
        try:
            self.transport.write(data)
        except:
            self.transport.close()

class ProxyServerProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.loop = loop

    def connection_made(self, transport):
        self.step = 0
        self.transport = transport
        self.peer = ipaddress.IPv4Address(self.transport.get_extra_info('peername')[0])
        LOGGER.info("Connection from: " + str(self.peer))
        if self.peer not in ACCEPTED_NETWORK:
            LOGGER.info("Peer is not in accepted networks")
            self.transport.close()
    
    def connection_lost(self, exc):
        LOGGER.info("Connection with " + str(self.peer) + " closed")
        #self.proxy.shutdown(socket.SHUT_RDWR)
        #self.proxy.close()
        #self.coro.close()

    def data_received(self, data):
        if self.step == 0:
            header = data.decode().split("\r\n")
            connect_found = False
            for line in header:
                name_value = line.split(" ")
                if len(name_value) >= 2 and name_value[0] == "CONNECT":
                    host_port = name_value[1].split(":")
                    if len(host_port) == 2:
                        if (host_port[0] != "localhost" and host_port[0] != "127.0.0.1") or host_port[1] != "22":
                            LOGGER.info("Connection attempt on invalid host:port (" + host_port[0] + ":" + host_port[1] + ")")
                            self.transport.close()
                        self.step = 1
                        self.transport.write(("HTTP/1.1 200 Connection established\r\nProxy-agent: Spoluck\r\n\r\n").encode())
                        self.proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.proxy.connect((host_port[0], int(host_port[1])))
                        self.coro = self.loop.create_connection(lambda: ProxyClientProtocol(self.transport), sock=self.proxy)
                        asyncio.ensure_future(self.coro)
                        connect_found = True
                        LOGGER.info("Proxy established")
                        break
#            if not connect_found:
#                LOGGER.info("Connection failed")
#                self.transport.close()
        elif self.step == 1:
            try:
                self.proxy.send(data)
            except:
                self.transport.close()

loop = asyncio.get_event_loop()

coro = loop.create_server(lambda: ProxyServerProtocol(loop), "0.0.0.0", 5005)

server = loop.run_until_complete(coro)

print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()

