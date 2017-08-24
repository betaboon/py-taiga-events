import aioamqp
import logging


class Events(object):
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

    async def start(self):
        try:
            transport, protocol = await aioamqp.connect(
                host=self.host,
                port=self.port,
                login=self.username,
                password=self.password,
                virtualhost=self.virtualhost
            )
            self.transport = transport
            self.protocol = protocol
            logging.info("events: connected")
        except aioamqp.AmqpClosedConnection:
            logging.error("events: failed to connect")
            return

    async def getClientChannel(self, client_id):
        if not client_id in self.channels:
            self.channels[client_id] = await self.protocol.channel()
        return self.channels[client_id]

    async def closeClientChannel(self, client_id):
        if client_id in self.channels:
            channel = await self.getClientChannel(client_id)
            channel.close()
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

    async def addClient(self, client_id, callback):
        await self.getClientConsumer(client_id, callback)

    async def removeClient(self, client_id):
        await self.closeClientChannel(client_id)
