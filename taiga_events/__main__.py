import asyncio
import logging

from taiga_events import signing, websocket
from . import config


def main():
    logging.basicConfig(level=logging.DEBUG)

    signing.setConfig(
        salt=config.signing.get('salt'),
        secret=config.signing.get('secret')
    )

    server = websocket.Server(
        host=config.websocket.get('host'),
        port=config.websocket.get('port')
    )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.serve())
    loop.run_forever()

if __name__ == "__main__":
    main()
