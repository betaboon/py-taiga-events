import json
import logging
import websockets

from .client import Client


class Server(object):
    def __init__(self, host, port, signer, events):
        self.host = host
        self.port = port
        self.signer = signer
        self.events = events

    async def start(self):
        await websockets.serve(self.client_handler, self.host, self.port)
        logging.info("server: listening on ws://{}:{}".format(
            self.host, self.port
        ))
        await self.events.start()

    async def client_handler(self, websocket, path):
        async with Client(
            websocket, self.signer, self.events
        ) as client:
            logging.info("client:{}: connected".format(client.id))
            while True:
                try:
                    message = await websocket.recv()
                    await client.websocket_handler(json.loads(message))
                except ValueError:
                    #TODO: use more specific exceptions
                    logging.error("client:{}: ValueError")
                except websockets.ConnectionClosed:
                    logging.info("client:{}: disconnected".format(client.id))
                    break
