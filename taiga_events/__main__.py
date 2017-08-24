import asyncio
import logging

from . import Events, Server, Signer
from . import config


def main():
    logging.basicConfig(level=logging.INFO)

    server = Server(
        host=config.websocket.get('host'),
        port=config.websocket.get('port'),
        signer = Signer(
            config.signing.get('salt'),
            config.signing.get('secret')
        ),
        events = Events(
            config.amqp.get('host'),
            config.amqp.get('port'),
            config.amqp.get('virtualhost'),
            config.amqp.get('username'),
            config.amqp.get('password')
        )
    )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    loop.run_forever()
    logging.info("Stopping...")

if __name__ == "__main__":
    main()
