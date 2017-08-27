import json
import logging
import uuid
import websockets

from taiga_events import signing
from taiga_events.meta import commandhandler
from taiga_events.meta.commandhandler import (
    handles_command, requires_authentication, validate
)


class ClientSession(commandhandler.CommandHandlerMeta):
    def __init__(self, websocket, client_id):
        self.websocket = websocket
        self.client_id = client_id
        self.session_id = None
        self.token = None

    def isAuthenticated(self):
        return self.session_id and self.token

    @handles_command
    async def ping(self, data):
        try:
            await self.websocket.send(json.dumps({'cmd': 'pong'}))
        except:
            pass

    @handles_command('auth')
    @validate(['data','token'],['data','sessionId'])
    async def authenticate(self, data):
        auth = data.get('data')
        token = auth.get('token')
        session_id = auth.get('sessionId') # the json-key realy is sessionId
        try:
            signing.verifyToken(token)
            self.token = token
            self.session_id = session_id
            logging.info("session:{}:authenticate: success".format(
                self.client_id
            ))
        except signing.TokenInvalidError:
            logging.error("session:{}:authenticate: failed".format(
                self.client_id
            ))

    @handles_command
    @requires_authentication
    @validate('routing_key')
    async def subscribe(self, data):
        routing_key = data.get('routing_key')
#        await self.events.subscribe(self.id, routing_key)
        logging.info("session:{}:subscribe: {}".format(
            self.client_id, routing_key
        ))

    @handles_command
    @requires_authentication
    @validate('routing_key')
    async def unsubscribe(self, message):
        routing_key = message.get('routing_key')
#        await self.events.unsubscribe(self.id, routing_key)
        logging.info("session:{}:unsubscribe: {}".format(
            self.client_id, routing_key
        ))


class Server(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sessions = {}

    async def serve(self):
        await websockets.serve(self.handleClient, self.host, self.port)
        logging.info("server: listening on ws://{}:{}".format(
            self.host, self.port
        ))

    async def handleClient(self, websocket, path):
        client_id = uuid.uuid4()
        session = ClientSession(websocket, client_id)
        self.sessions[client_id] = session
        logging.info("server:{}: client connected".format(client_id))
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                command = data.pop('cmd', '__undefined__')
                await session.handleCommand(command, data)
            except websockets.ConnectionClosed:
                logging.info("server:{}: disconnected".format(client_id))
                break
            except json.JSONDecodeError:
                logging.error("server:{}: invalid json".format(client_id))
            except commandhandler.UnknownCommandError:
                logging.error("server:{}: unknown command '{}'".format(
                    client_id, command
                ))
            except commandhandler.UnauthenticatedError:
                logging.error("server:{}:{}: unauthenticated".format(
                    client_id, command
                ))
            except commandhandler.ValidationError:
                logging.error("server:{}:{}: invalid arguments".format(
                    client_id, command
                ))
