from abc import ABCMeta, abstractmethod
import aioamqp
import json
import logging
import uuid

from .util import Singleton


class EventConsumer(metaclass=Singleton):
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
        self.queue_names = {}
        self.consumer_tags = {}

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

    async def getChannel(self, consumer_tag):
        if not consumer_tag in self.channels:
            self.channels[consumer_tag] = await self.protocol.channel()
        return self.channels[consumer_tag]

    async def closeChannel(self, consumer_tag):
        if consumer_tag in self.channels:
            channel = await self.getChannel(consumer_tag)
            await channel.close()
            del self.channels[consumer_tag]

    async def getQueue(self, consumer_tag):
        if not consumer_tag in self.queue_names:
            channel = await self.getChannel(consumer_tag)
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
            self.queue_names[consumer_tag] = queue_result['queue']
        return self.queue_names[consumer_tag]

    async def getConsumer(self, consumer_tag, callback):
        if not consumer_tag in self.consumer_tags:
            channel = await self.getChannel(consumer_tag)
            queue_name = await self.getQueue(consumer_tag)
            result = await channel.basic_consume(
                callback=callback,
                queue_name=queue_name,
                consumer_tag=consumer_tag,
                no_ack=True
            )
            # these should be equal and therefore redundant
            self.consumer_tags[consumer_tag] = result['consumer_tag']
        return self.consumer_tags[consumer_tag]

    async def subscribe(self, consumer_tag, routing_key):
        channel = await self.getChannel(consumer_tag)
        queue_name = await self.getQueue(consumer_tag)
        result = await channel.queue_bind(
            exchange_name=self.exchange_name,
            queue_name=queue_name,
            routing_key=routing_key
        )
        if not result:
            logging.error(
                "amqp:events:{}:subscribe: {}; failed".format(
                    consumer_tag, routing_key
            ))
        return result

    async def unsubscribe(self, consumer_tag, routing_key):
        channel = await self.getChannel(consumer_tag)
        queue_name = await self.getQueue(consumer_tag)
        result = await channel.queue_unbind(
            exchange_name=self.exchange_name,
            queue_name=queue_name,
            routing_key=routing_key
        )
        if not result:
            logging.error(
                "amqp:events:{}:unsubscribe: {}; failed".format(
                    consumer_tag, routing_key
            ))
        return result

    async def register(self, consumer_tag, callback):
        await self.getConsumer(consumer_tag, callback)

    async def unregister(self, consumer_tag):
        await self.closeChannel(consumer_tag)


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

    def hasConsumerTag(self):
        return hasattr(self, 'consumer_tag') and self.consumer_tag

    async def startConsumingEvents(self):
        if not self.hasConsumerTag():
            self.consumer_tag = str(uuid.uuid4())
            await EventConsumer().register(
                self.consumer_tag, self.handleRawEvent
            )

    async def stopConsumingEvents(self):
        if self.hasConsumerTag():
            await EventConsumer().unregister(self.consumer_tag)
            self.consumer_tag = None

    async def subscribeEvents(self, routing_key):
        if self.hasConsumerTag():
            await EventConsumer().subscribe(
                self.consumer_tag, routing_key
            )
        # TODO: what if not yet consuming?

    async def unsubscribeEvents(self, routing_key):
        if self.hasConsumerTag():
            await EventConsumer().unsubscribe(
                self.consumer_tag, routing_key
            )
