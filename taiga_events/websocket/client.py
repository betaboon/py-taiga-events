import json
import logging
import uuid


class Client(object):
    def __init__(self, websocket, signer, events):
        self.websocket = websocket
        self.signer = signer
        self.events = events
        self.id = uuid.uuid4()
        self.session_id = None
        self.token = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *err):
        await self.stop_event_handler()

    async def start_event_handler(self):
        await self.events.addClient(self.id, self.event_handler)

    async def stop_event_handler(self):
        await self.events.removeClient(self.id)

    async def event_handler(self, channel, body, envelope, properties):
        event = json.loads(body.decode("utf-8"))
        if event.get('session_id') == self.session_id:
            return
        event['routing_key'] = envelope.routing_key
        try:
            await self.websocket.send(json.dumps(event))
            logging.debug("client:{}:event: {}".format(
                self.id, event
            ))
        except:
            logging.error("client:{}:event: failed to send".format(
                self.id
            ))

    async def websocket_handler(self, message):
        try:
            cmd = message.get('cmd')
            if 'ping' == cmd:
                await self.ping(message)
            if 'auth' == cmd:
                await self.authenticate(message)
            if 'subscribe' == cmd:
                await self.subscribe(message)
            if 'unsubscribe' == cmd:
                await self.unsubscribe(message)
        except KeyError:
            logging.error("client:{}: message malformed".format(
                self.id
            ))

    def authentication_required(func):
        async def wrapper(*args):
            client = args[0]
            if client.session_id and client.token:
                return await func(*args)
            else:
                logging.warn(
                    "client:{}:{}: unauthenticated".format(
                    client.id, func.__name__
                ))
        return wrapper

    async def ping(self, message):
        try:
            logging.debug("client:{}:ping".format(self.id))
            await self.websocket.send(json.dumps({'cmd': 'pong'}))
            logging.debug("client:{}:pong".format(self.id))
        except:
            logging.error("client:{}:pong: failed".format(
                self.id
            ))

    async def authenticate(self, message):
        data = message.get('data')
        token = data.get('token')
        session_id = data.get('sessionId') # the json-key realy is sessionId
        if self.signer.verifyToken(token):
            self.token = token
            self.session_id = session_id
            logging.debug(
                "client:{}:authenticate: success".format(
                    self.id
            ))
            await self.start_event_handler()
        else:
            logging.error(
                "client:{}:authenticate: failed".format(
                self.id
            ))

    @authentication_required
    async def subscribe(self, message):
        routing_key = message.get('routing_key')
        await self.events.subscribe(self.id, routing_key)
        logging.debug("client:{}:subscribe: {}".format(
            self.id, routing_key
        ))

    @authentication_required
    async def unsubscribe(self, message):
        routing_key = message.get('routing_key')
        await self.events.unsubscribe(self.id, routing_key)
        logging.debug("client:{}:unsubscribe: {}".format(
            self.id, routing_key
        ))
