import asyncio
import logging

from taiga_events import amqp, signing, websocket
from . import config


def main():
    logging.basicConfig(level=logging.INFO)

    signing.setConfig(
        salt=config.signing.get('salt'),
        secret=config.signing.get('secret')
    )

    events = amqp.EventConsumer(
        host=config.amqp.get('host'),
        port=config.amqp.get('port'),
        virtualhost=config.amqp.get('virtualhost'),
        username=config.amqp.get('username'),
        password=config.amqp.get('password'),
    )

    server = websocket.Server(
        host=config.websocket.get('host'),
        port=config.websocket.get('port')
    )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.serve())
    loop.run_until_complete(events.consume())
    loop.run_forever()

if __name__ == "__main__":
    main()
