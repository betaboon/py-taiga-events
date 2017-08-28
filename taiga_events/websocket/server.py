import json
import logging
import uuid
import websockets

from taiga_events import signing
from taiga_events.meta import commandhandler
from taiga_events.meta.commandhandler import (
    command,
    require_authentication, validate_arguments, consume_arguments
)


class ClientSession(commandhandler.CommandHandlerMeta):
    def __init__(self, websocket, client_id):
        self.websocket = websocket
        self.client_id = client_id
        self.session_id = None
        self.token = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stopConsumingEvents()

    # required for @require_authentication
    def isAuthenticated(self):
        return self.session_id and self.token

    @command
    @consume_arguments
    async def ping(self):
        try:
            await self.websocket.send(json.dumps({'cmd': 'pong'}))
        except:
            pass

    @command('auth')
    @validate_arguments({'data': ['token', 'sessionId']})
    @consume_arguments
    async def authenticate(self, data):
        token = data.get('token')
        session_id = data.get('sessionId') # the json-key realy is sessionId
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

    @command
    @require_authentication
    @consume_arguments
    async def subscribe(self, routing_key):
#        await self.events.subscribe(self.id, routing_key)
        logging.info("session:{}:subscribe: {}".format(
            self.client_id, routing_key
        ))

    @command
    @require_authentication
    @consume_arguments
    async def unsubscribe(self, routing_key):
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

    async def handleClientSession(self, session):
        while True:
            try:
                message = await session.websocket.recv()
                data = json.loads(message)
                command = data.pop('cmd', '__undefined__')
                await session.handleCommand(command, data)
            except websockets.ConnectionClosed:
                break
            except json.JSONDecodeError:
                logging.error("server:{}: invalid json".format(
                    session.client_id
                ))
            except commandhandler.UnauthenticatedError:
                logging.error("server:{}:{}: unauthenticated".format(
                    session.client_id, command
                ))
            except commandhandler.InvalidCommandError:
                logging.error("server:{}: invalid command '{}'".format(
                    session.client_id, command
                ))
            except commandhandler.MissingArgumentError as e:
                logging.error("server:{}:{}: missing argument '{}'".format(
                    session.client_id, command, e
                ))
            except commandhandler.InvalidArgumentError as e:
                logging.error("server:{}:{}: invalid argument '{}'".format(
                    session.client_id, command, e
                ))


    async def handleClient(self, websocket, path):
        client_id = uuid.uuid4()
        async with ClientSession(websocket, client_id) as session:
            logging.info("server:{}: client connected".format(client_id))
            self.sessions[client_id] = session
            await self.handleClientSession(session)
            logging.info("server:{}: client disconnected".format(client_id))
