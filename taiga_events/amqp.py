from abc import ABCMeta, abstractmethod
import aioamqp
import json
import logging

from .meta import Singleton


class EventHandlerMeta(metaclass=ABCMeta):
    @abstractmethod
    async def handleEvent(self, event):
        pass

    async def handleRawEvent(self, channel, body, envelope, properties):
        try:
            event = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            logging.error("event:handler: invalid json")
        else:
            event['routing_key'] = envelope.routing_key
            await self.handleEvent(event)

    async def startConsumingEvents(self, client_id):
        await EventsConsumer().register(client_id, self.handleRawEvent)

    async def stopConsumingEvents(self, client_id):
        await EventsConsumer().unregister(client_id)

    async def subscribeEvents(self, client_id, routing_key):
        await EventsConsumer().subscribe(client_id, routing_key)

    async def unsubscribeEvents(self, client_id, routing_key):
        await EventsConsumer().unsubscribe(client_id, routing_key)


class EventsConsumer(metaclass=Singleton):
    def __init__(self, host, port, virtualhost, username, password):
        self.host = host
        self.port = port
        self.virtualhost = virtualhost
        self.username = username
        self.password = password
        self.exchange_name='events'
        self.transport = None
        self.protocol = None
        self.channels = {}
        self.queues = {}
        self.consumers = {}

    def isConnected(self):
        return self.protocol is not None

    async def consume(self):
        try:
            transport, protocol = await aioamqp.connect(
                host=self.host,
                port=self.port,
                login=self.username,
                password=self.password,
                virtualhost=self.virtualhost
            )
            logging.info("amqp:events: connected")
            self.transport = transport
            self.protocol = protocol
        except aioamqp.AmqpClosedConnection:
            logging.error("amqp:events: disconnected")
            return
        except ConnectionRefusedError:
            logging.error("amqp:events: failed to connect")

    async def getClientChannel(self, client_id):
        if not client_id in self.channels:
            self.channels[client_id] = await self.protocol.channel()
        return self.channels[client_id]

    async def closeClientChannel(self, client_id):
        if client_id in self.channels:
            channel = await self.getClientChannel(client_id)
            await channel.close()
            del self.channels[client_id]

    async def getClientQueue(self, client_id):
        if not client_id in self.queues:
            channel = await self.getClientChannel(client_id)
            await channel.exchange(
                exchange_name=self.exchange_name,
                type_name='topic',
                durable=False,
                auto_delete=True
            )
            queue_result = await channel.queue(
                queue_name='',
                durable=True,
                auto_delete=True,
                exclusive=True
            )
            self.queues[client_id] = queue_result['queue']
        return self.queues[client_id]

    async def getClientConsumer(self, client_id, callback):
        if not client_id in self.consumers:
            channel = await self.getClientChannel(client_id)
            queue_name = await self.getClientQueue(client_id)
            result = await channel.basic_consume(
                callback=callback,
                queue_name=queue_name,
                no_ack=True
            )
            self.consumers[client_id] = result['consumer_tag']
        return self.consumers[client_id]

    async def subscribe(self, client_id, routing_key):
        channel = await self.getClientChannel(client_id)
        queue_name = await self.getClientQueue(client_id)
        result = await channel.queue_bind(
            exchange_name=self.exchange_name,
            queue_name=queue_name,
            routing_key=routing_key
        )
        if not result:
            logging.error(
                "amqp:events:{}:subscribe: {}; failed".format(
                    client_id, routing_key
            ))
        return result

    async def unsubscribe(self, client_id, routing_key):
        channel = await self.getClientChannel(client_id)
        queue_name = await self.getClientQueue(client_id)
        result = await channel.queue_unbind(
            exchange_name=self.exchange_name,
            queue_name=queue_name,
            routing_key=routing_key
        )
        if not result:
            logging.error(
                "amqp:events:{}:unsubscribe: {}; failed".format(
                    client_id, routing_key
            ))
        return result

    async def register(self, client_id, callback):
        await self.getClientConsumer(client_id, callback)

    async def unregister(self, client_id):
        await self.closeClientChannel(client_id)
